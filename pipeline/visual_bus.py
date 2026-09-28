"""VISUAL BUS builder: video only, absolutely no audio.
1) prep: every source clip -> 1920x1080 24 fps, audio stripped (-an) and verified
2) cycle: clips of one shot are chained with long crossfades and closed into a seamless loop
3) compose: timeline of shots, slow sub-pixel push-in per shot, long crossfades between shots,
   brightness automation (darker toward sleep), fade-out. Output has NO audio stream.
usage: python3 visual_bus.py timeline.json out.mp4
timeline.json = {"duration": s, "fps": 24, "xfade_shot": 6, "xfade_clip": 2.5,
  "shots": [{"name": "A", "clips": ["dir/A1/raw.mp4", ...], "start": 0, "end": 702.5, "zoom": [1.0, 1.06]}, ...],
  "brightness": [[t, factor], ...], "fade_out": 15}
"""
import sys, os, json, subprocess, numpy as np, cv2

W, H = 1920, 1080

def sh(cmd):
    subprocess.run(cmd, shell=True, check=True)

def streams(fn):
    return subprocess.run(f"ffprobe -v error -show_entries stream=codec_type -of csv=p=0 '{fn}'", shell=True,
                          capture_output=True, text=True).stdout.split()

def dur(fn):
    return float(subprocess.run(f"ffprobe -v error -show_entries format=duration -of csv=p=0 '{fn}'", shell=True,
                                capture_output=True, text=True).stdout)

def clean_range(src):
    """generated clips can contain a hard jump (model segment boundary); keep the longest jump-free run"""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vf', 'scale=160:90,format=gray', '-f', 'rawvideo', '-'],
                         capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 90, 160).astype(np.float32)
    f = f - f.mean((1, 2), keepdims=True)   # ignore global flicker (lamp / fire light), detect structural jumps only
    d = np.abs(np.diff(f, axis=0)).mean((1, 2))
    thr = max(1.6, 4 * float(np.median(d)))
    cuts = [0] + [i + 1 for i in np.where(d > thr)[0]] + [len(f)]
    a, b = max(zip(cuts[:-1], cuts[1:]), key=lambda r: r[1] - r[0])
    a = a + 2 if a > 0 else a            # skip the first frames right after a jump
    src_fps = 24.0
    return a / src_fps, b / src_fps, len(cuts) - 2

def prep(src, dst, fps):
    if not os.path.exists(dst):
        ss, to, njumps = clean_range(src)
        print(f'  prep {os.path.basename(os.path.dirname(src))}: jumps={njumps} keep {ss:.2f}-{to:.2f}s', flush=True)
        sh(f"ffmpeg -y -v error -i '{src}' -an -vf 'trim={ss:.3f}:{to:.3f},setpts=PTS-STARTPTS,scale={W}:{H}:flags=lanczos,"
           f"unsharp=5:5:0.35,fps={fps},format=yuv420p' -c:v libx264 -preset fast -crf 14 '{dst}'")
    assert streams(dst) == ['video'], f'{dst} must be video-only, got {streams(dst)}'
    return dst

def cycle(clips, dst, X, fps):
    """chain clips with X-second crossfades, then close the loop seamlessly"""
    if os.path.exists(dst):
        return dst
    tmp = dst + '.chain.mp4'
    if len(clips) == 1:
        sh(f"cp '{clips[0]}' '{tmp}'")
    else:
        ins = ' '.join(f"-i '{c}'" for c in clips)
        ds = [dur(c) for c in clips]
        fc = []; prev = '[0:v]'; off = 0.0
        for k in range(1, len(clips)):
            off += ds[k - 1] - X
            fc.append(f"{prev}[{k}:v]xfade=transition=fade:duration={X}:offset={off:.3f}[x{k}]")
            prev = f'[x{k}]'
        sh(f"ffmpeg -y -v error {ins} -filter_complex \"{';'.join(fc)}\" -map '{prev}' -an -c:v libx264 -preset fast -crf 14 '{tmp}'")
    L = dur(tmp)
    # loop closure: body = [X, L-X), then crossfade(tail=[L-X, L) -> head=[0, X))
    sh(f"ffmpeg -y -v error -i '{tmp}' -filter_complex "
       f"\"[0:v]split=3[a][b][c];[a]trim={X}:{L - X:.3f},setpts=PTS-STARTPTS[body];"
       f"[b]trim={L - X:.3f}:{L:.3f},setpts=PTS-STARTPTS[tail];[c]trim=0:{X},setpts=PTS-STARTPTS[head];"
       f"[tail][head]xfade=transition=fade:duration={X}:offset=0[join];[body][join]concat=n=2:v=1:a=0[o]\" "
       f"-map '[o]' -an -r {fps} -c:v libx264 -preset fast -crf 14 '{dst}'")
    assert streams(dst) == ['video']
    return dst

class Reader:
    """endless raw-frame reader of a looping video"""
    def __init__(self, fn):
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-stream_loop', '-1', '-i', fn, '-an', '-f', 'rawvideo',
                                   '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)
    def read(self):
        b = self.p.stdout.read(W * H * 3)
        return np.frombuffer(b, np.uint8).reshape(H, W, 3)
    def close(self):
        self.p.kill()

def zoom(img, s, cx=0.5, cy=0.5):
    if abs(s - 1) < 1e-4:
        return img
    M = np.array([[s, 0, (1 - s) * W * cx], [0, s, (1 - s) * H * cy]], np.float32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def main():
    tl = json.load(open(sys.argv[1])); out = sys.argv[2]
    fps = tl.get('fps', 24); D = tl['duration']; XS = tl.get('xfade_shot', 6); XC = tl.get('xfade_clip', 2.5)
    work = os.path.splitext(out)[0] + '_work'; os.makedirs(work, exist_ok=True)
    shots = tl['shots']
    for s in shots:
        pc = [prep(c, f"{work}/{s['name']}_{i}.mp4", fps) for i, c in enumerate(s['clips'])]
        s['cycle'] = cycle(pc, f"{work}/{s['name']}_cycle.mp4", XC, fps)
        print('cycle', s['name'], round(dur(s['cycle']), 2), 's', flush=True)
    bt = np.array(tl['brightness'], float)
    enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(fps),
                            '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'faster', '-crf', '22', '-pix_fmt', 'yuv420p',
                            '-g', str(fps * 10), '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    readers = {}
    N = int(round(D * fps))
    logo = tl.get('logo')   # Branding Policy: static channel logo top-left, soft fade-in, opacity follows scene dimming
    if logo:
        from PIL import Image
        lg = Image.open(logo['file']).convert('RGBA')
        if 'width' in logo: lg = lg.resize((logo['width'], round(lg.height * logo['width'] / lg.width)), Image.LANCZOS)
        lg = np.asarray(lg).astype(np.float32)
        lg_rgb = lg[:, :, 2::-1].copy(); lg_a = lg[:, :, 3:4] / 255.0     # BGR + alpha
        lx, ly = logo.get('x', 56), logo.get('y', 44); lh, lw = lg.shape[:2]
        f0, f1 = logo.get('fade_in', [1.5, 3.5]); op = logo.get('opacity', 0.8); follow = logo.get('dim_follow', 0.45)
    for n in range(N):
        t = n / fps
        active = [s for s in shots if s['start'] - XS / 2 <= t < s['end'] + XS / 2]
        layers = []
        for s in active:
            if s['name'] not in readers:
                readers[s['name']] = Reader(s['cycle'])
            fr = readers[s['name']].read()
            z0, z1 = s.get('zoom', [1.0, 1.05])
            u = min(max((t - s['start']) / max(1, s['end'] - s['start']), 0), 1)
            u = 0.5 - 0.5 * np.cos(np.pi * u)  # ease in/out
            img = zoom(fr, z0 + (z1 - z0) * u, *s.get('center', [0.5, 0.5]))
            # crossfade weight around shot boundaries (equal-power not needed for video; linear in light)
            w = 1.0
            if t < s['start'] + XS / 2 and s['start'] > 0:
                w = (t - (s['start'] - XS / 2)) / XS
            if t >= s['end'] - XS / 2 and s['end'] < D:
                w = min(w, ((s['end'] + XS / 2) - t) / XS)
            layers.append((max(0.0, min(1.0, w)), img))
        for s in shots:  # free readers of finished shots
            if s['name'] in readers and t >= s['end'] + XS / 2:
                readers.pop(s['name']).close()
        tot = sum(w for w, _ in layers) or 1.0
        b = float(np.interp(t, bt[:, 0], bt[:, 1]))
        fo = tl.get('fade_out', 15)
        if t > D - fo:
            b *= max(0.0, (D - t) / fo)
        fi = tl.get('fade_in', 2)
        if t < fi:
            b *= t / fi
        if len(layers) == 1:
            frame = cv2.convertScaleAbs(layers[0][1], alpha=b)
        else:
            (w1, i1), (w2, i2) = layers[0], layers[1]
            frame = cv2.addWeighted(i1, b * w1 / tot, i2, b * w2 / tot, 0)
        if logo:
            k = op * min(1.0, max(0.0, (t - f0) / (f1 - f0)))
            k *= 1.0 - follow * (1.0 - min(1.0, float(np.interp(t, bt[:, 0], bt[:, 1]))))
            if t > D - fo: k *= max(0.0, (D - t) / fo)
            if k > 0:
                roi = frame[ly:ly + lh, lx:lx + lw].astype(np.float32)
                a_ = lg_a * k
                frame = frame.copy() if not frame.flags.writeable else frame
                frame[ly:ly + lh, lx:lx + lw] = (roi * (1 - a_) + lg_rgb * a_).astype(np.uint8)
        enc.stdin.write(frame.tobytes())
        if n % (fps * 60) == 0:
            print(f'{t/60:.0f} min', flush=True)
    enc.stdin.close(); enc.wait()
    for r in readers.values(): r.close()
    assert streams(out) == ['video'], 'visual bus must not contain audio'
    print('visual bus ok', out, round(dur(out), 2))

if __name__ == '__main__':
    import freeze; freeze.check()
    main()
