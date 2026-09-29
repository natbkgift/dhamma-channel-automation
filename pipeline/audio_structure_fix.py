"""Audio Structure Policy (Nat, 29 Sep 2026) applied to an already-approved render, local only (API cost 0).
- intro: cut the ~6 s lead so narration starts ~1.0-1.5 s in; music audible from 0:00 with a soft fade-in
- outro: after the last spoken word, pause ~2 s, then a raised-cosine ramp (~15 s) into a music-only level
  (default -25 LUFS stereo); the speech-band EQ carve of the narration bed is blended out during the ramp
- everything between the first and last word is the approved mix, sample for sample (keeps de-click fixes)
- video: same approved visual bus, trimmed by the same amount, 1 s fade-in from black, re-muxed
usage: python3 audio_structure_fix.py <approved_dir> <out_dir> [--trim 5.0] [--outro_lufs -25] [--pause 2.0] [--ramp 15]
"""
import os, sys, json, argparse, subprocess
import numpy as np, soundfile as sf, pyloudnorm as pyln

SR = 48000
ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--trim', type=float, default=5.0)
ap.add_argument('--fade_in', type=float, default=1.0)
ap.add_argument('--pause', type=float, default=2.0)
ap.add_argument('--ramp', type=float, default=15.0)
ap.add_argument('--outro_lufs', type=float, default=-25.0)
ap.add_argument('--video', type=int, default=1)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
meta = json.load(open(f'{a.src}/meta.json')); mu = json.load(open(f'{a.src}/music_used.json'))

# last spoken word from the narration stem
v, vsr = sf.read(f'{a.src}/voice.wav', dtype='float32')
w = int(0.05 * vsr); n = len(v) // w
db = 20 * np.log10(np.sqrt((v[:n * w].reshape(n, w) ** 2).mean(1)) + 1e-9)
act = np.where(db > -45)[0]
first_word, last_word = act[0] * 0.05, (act[-1] + 1) * 0.05
voice_end = meta['duration']

mix, sr = sf.read(f'{a.src}/mix.wav', dtype='float32'); assert sr == SR
T0 = a.trim
Tn = last_word + a.pause                      # start of the music-only rise (original timeline)
Tr = Tn + a.ramp
# level the original bed followed (music_bed.py design): talk until voice_end+4, linear to outro over 40 s
g_talk, g_out = mu['talk_lufs'], mu['outro_lufs']
t = np.arange(len(mix)) / SR
seg = t >= Tn
ts = t[seg]
L_orig = np.where(ts < voice_end + 4, g_talk, g_talk + (g_out - g_talk) * np.clip((ts - voice_end - 4) / 40, 0, 1))
r = 0.5 - 0.5 * np.cos(np.pi * np.clip((ts - Tn) / a.ramp, 0, 1))      # 0 -> 1 raised cosine

x = mix[seg].copy()
# undo the speech-band carve (inverse of music_bed.carve, the 70 Hz high-pass is kept)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af',
                      'lowshelf=f=160:g=4,equalizer=f=1800:t=q:w=1.2:g=4,equalizer=f=3500:t=q:w=1.5:g=2',
                      '-f', 'f32le', '-'], input=x.astype(np.float32).tobytes(), capture_output=True, check=True).stdout
xd = np.frombuffer(raw, np.float32).reshape(-1, 2)[:len(x)]
blend = x * (1 - r[:, None]) + xd * r[:, None]

def apply(corr):
    gain_db = r * ((a.outro_lufs + corr) - L_orig)
    return blend * (10 ** (gain_db / 20))[:, None].astype(np.float32)

meter = pyln.Meter(SR)
end_fade = 25.0
steady = (ts >= Tr + 2) & (ts <= t[-1] - end_fade - 2)      # music-only, after the ramp, before the end fade
corr = 0.0
for _ in range(3):   # measure and correct once or twice (the de-carve changes loudness)
    y = apply(corr)
    L = meter.integrated_loudness(y[steady]) if steady.sum() > SR * 10 else a.outro_lufs
    corr += a.outro_lufs - L
    if abs(a.outro_lufs - L) < 0.2: break
y = apply(corr)
new = mix.copy(); new[seg] = y
new = new[int(T0 * SR):]
fi = int(a.fade_in * SR)
new[:fi] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fi)))[:, None].astype(np.float32)
# true-peak headroom <= -1.5 dBTP (4x oversampled estimate); scale only the music-only tail if it is the offender
def tp(z, blk=SR * 30):
    import scipy.signal as ss
    m = 0.0
    for i in range(0, len(z), blk):
        m = max(m, float(np.abs(ss.resample_poly(z[max(0, i - 64):i + blk + 64], 4, 1, axis=0)).max()))
    return 20 * np.log10(m + 1e-12)
cut = int((Tn - T0) * SR)
tp_head, tp_tail = tp(new[:cut]), tp(new[cut:])
if tp_tail > -2.0:
    new[cut:] *= 10 ** ((-2.1 - tp_tail) / 20); tp_tail = -2.1
g_all = min(0.0, -2.0 - tp_head)             # whole-programme trim for headroom after AAC (final must be <= -1.5 dBTP)
if g_all < 0: new *= 10 ** (g_all / 20)
sf.write(f'{a.out}/mix.wav', new, SR, subtype='PCM_24')
rep = {'source': a.src, 'trim_s': T0, 'first_word_new_s': round(first_word - T0, 2), 'last_word_new_s': round(last_word - T0, 2),
       'rise_start_new_s': round(Tn - T0, 2), 'rise_end_new_s': round(Tr - T0, 2), 'outro_lufs_target': a.outro_lufs,
       'outro_gain_corr_db': round(corr, 2), 'narration_bed_lufs': g_talk, 'tp_narration_part': round(tp_head, 2),
       'tp_outro_part': round(tp_tail, 2), 'global_trim_db': round(g_all, 2), 'duration_s': round(len(new) / SR, 2)}
print(json.dumps(rep))
json.dump(rep, open(f'{a.out}/audio_structure.json', 'w'), indent=1)
if a.video:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{T0}', '-i', f'{a.src}/visual.mp4', '-i', f'{a.out}/mix.wav',
                    '-map', '0:v', '-map', '1:a', '-vf', f'fade=t=in:st=0:d={a.fade_in}', '-c:v', 'libx264', '-preset', 'faster',
                    '-crf', '20', '-pix_fmt', 'yuv420p', '-g', '240', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                    '-shortest', '-movflags', '+faststart', f'{a.out}/final.mp4'], check=True)
    print('final', f'{a.out}/final.mp4')
