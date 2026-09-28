"""Automated audio QC for DhammaLab renders (calibrated on EXP-01 v2 defects, 28 Sep 2026).
Usage:
  python3 qc_scan.py --file mix.wav [--voice voice.wav]            # scan one audio/video file
  python3 qc_scan.py --final final.mp4 --mix mix.wav [--voice v.wav] # also verify the final render
Checks
  burst  : 10 ms frames >=5 dB above the local (+-3 s) 90th percentile, spectral centroid >3.5 kHz, >-30 dBFS
           (caught all 59 C2PA noise bursts in v2; 0-2 hits on clean speech = strong sibilants, reported as 'warn')
  click  : sample-to-sample jump >=0.02 and >=6x the local 5 ms RMS inside regions where the narration bus is
           silent (music-only / silence), i.e. pops that cannot be consonants
  clip   : |x| >= 0.999
  final  : exactly 1 video + 1 audio stream; decoded final audio matches mix.wav (corr >= 0.98) so no audio from
           visual assets / effects / transitions can have entered the programme
Exit 1 on any error-level finding.
"""
import sys, json, subprocess, argparse
import numpy as np

SR = 48000

def decode(fn, sr=SR):
    # average channels explicitly (ffmpeg's default -ac 1 downmix is +3 dB and fakes clipping)
    ch = int(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=channels',
                             '-of', 'csv=p=0', fn], capture_output=True, text=True).stdout.strip() or 1)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', fn, '-vn', '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).mean(1)

def bursts(x):
    W = SR // 100; n = len(x) // W; fr = x[:n * W].reshape(n, W)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    ref = np.array([np.percentile(db[max(0, i - 300):i + 300], 90) for i in range(0, n, 10)])
    ref = np.repeat(ref, 10)[:n]
    S = np.abs(np.fft.rfft(fr * np.hanning(W), axis=1)); f = np.fft.rfftfreq(W, 1 / SR)
    cen = (S * f).sum(1) / (S.sum(1) + 1e-9)
    hit = np.where((db - ref >= 5) & (cen > 3500) & (db > -30))[0]
    ev = []; last = -100
    for i in hit:
        if i - last > 5:
            ev.append({'type': 'burst', 't': round(i / 100, 2), 'db': round(float(db[i]), 1),
                       'over_local': round(float(db[i] - ref[i]), 1), 'centroid': int(cen[i])})
        last = i
    return ev

def clicks(x, voice=None):
    w = int(SR * 0.005); n = len(x) // w
    rms = np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(1))
    if voice is not None:
        m = min(len(voice), n * w) // w
        vr = np.sqrt((voice[:m * w].reshape(m, w) ** 2).mean(1))
        quiet = np.zeros(n, bool); quiet[:m] = vr < 10 ** (-50 / 20)
        from scipy.ndimage import binary_erosion
        quiet = binary_erosion(quiet, iterations=20)  # 100 ms away from any speech
        if len(voice) < len(x): quiet[m:] = True
    else:
        quiet = rms < 10 ** (-40 / 20)
    d = np.abs(np.diff(x[:n * w]))
    rr = np.repeat(rms, w)[:-1]; qq = np.repeat(quiet, w)[:-1]
    hit = np.where(qq & (d >= 0.02) & (d >= 6 * rr))[0]
    ev = []; last = -SR
    for i in hit:
        if i - last > SR // 20:
            ev.append({'type': 'click', 't': round(i / SR, 3), 'jump': round(float(d[i]), 3)})
        last = i
    return ev

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file'); ap.add_argument('--final'); ap.add_argument('--mix'); ap.add_argument('--voice')
    ap.add_argument('--json')
    a = ap.parse_args()
    rep = {'errors': [], 'warnings': []}
    target = a.file or a.mix
    x = decode(target)
    v = decode(a.voice) if a.voice else None
    b = bursts(x)
    # isolated strong sibilants on clean speech: at most a couple, all < -8 dBFS -> warning; otherwise error
    if len(b) <= 2 and all(e['db'] < -8 for e in b):
        rep['warnings'] += b
    else:
        rep['errors'] += b
    rep['errors'] += clicks(x, v)
    nclip = int((np.abs(x) >= 0.999).sum())
    if nclip: rep['errors'].append({'type': 'clip', 'samples': nclip})
    if a.final:
        st = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', a.final],
                            capture_output=True, text=True).stdout.split()
        if st.count('video') != 1 or st.count('audio') != 1:
            rep['errors'].append({'type': 'streams', 'found': st})
        fa = decode(a.final)
        L = min(len(fa), len(x)); step = SR * 30; cs = []
        for s in range(0, L - SR * 5, step):
            p, q = fa[s:s + SR * 5], x[s:s + SR * 5]
            if np.std(q) > 1e-4:
                cs.append(float(np.corrcoef(p, q)[0, 1]))
        rep['final_mix_corr_min'] = round(min(cs), 4)
        if min(cs) < 0.98:
            rep['errors'].append({'type': 'final_audio_mismatch', 'corr_min': round(min(cs), 4)})
        fb = bursts(fa)
        if len(fb) > len(b):
            rep['errors'].append({'type': 'final_has_extra_bursts', 'n': len(fb) - len(b), 'at': [e['t'] for e in fb][:10]})
    print(json.dumps({k: (v if not isinstance(v, list) else v[:30]) for k, v in rep.items()}, ensure_ascii=False, indent=1))
    print('ERRORS', len(rep['errors']), 'WARNINGS', len(rep['warnings']))
    if a.json: json.dump(rep, open(a.json, 'w'), ensure_ascii=False, indent=1)
    sys.exit(1 if rep['errors'] else 0)

if __name__ == '__main__':
    main()
