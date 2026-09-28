"""Automated QC for long-form meditation / sleep music (EXP-M). usage: python3 music_qc.py track.(wav|mp3) [--json out.json]
Checks (per directive 29 Sep 2026): click, pop/glitch, clipping, sudden peaks, unexpected silence, abrupt tonal change,
audible edit point (spectral discontinuity), excessive bass, excessive percussion, plus loudness range.
Also prints the timestamps for the human-ear spot check: start, 25%, 50%, 75%, end."""
import sys, json, subprocess, numpy as np, librosa

SR = 22050

def decode(fn, sr=SR, ch=1):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', fn, '-ac', str(ch), '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)

def fmt(t): return f'{int(t // 60)}:{int(t % 60):02d}'

def qc(fn):
    y = decode(fn); dur = len(y) / SR
    yf = decode(fn, 48000)
    out = {'file': fn, 'duration_s': round(dur, 1), 'errors': [], 'warnings': []}
    E, W = out['errors'], out['warnings']
    # clipping
    clip = int((np.abs(yf) >= 0.999).sum())
    if clip: E.append({'type': 'clipping', 'samples': clip})
    # clicks: sample jump far above the local 5 ms RMS
    d = np.abs(np.diff(yf)); w = 240
    n = len(yf) // w; rms = np.sqrt((yf[:n * w].reshape(n, w) ** 2).mean(1)) + 1e-6
    loc = np.repeat(rms, w); loc = np.pad(loc, (0, max(0, len(d) - len(loc))), mode='edge')[:len(d)]
    idx = np.where((d > 0.05) & (d > 10 * loc))[0]
    for i in idx[:10]: E.append({'type': 'click', 't': fmt(i / 48000), 'jump': round(float(d[i]), 3)})
    # short-term level 1 s: sudden peaks, silence, loudness range
    s = SR; m = len(y) // s
    db = 20 * np.log10(np.sqrt((y[:m * s].reshape(m, s) ** 2).mean(1)) + 1e-9)
    med = float(np.median(db))
    for i in range(3, m):
        if db[i] - np.median(db[max(0, i - 10):i]) > 8: E.append({'type': 'sudden_peak', 't': fmt(i), 'rise_db': round(float(db[i] - np.median(db[max(0, i - 10):i])), 1)})
    sil = np.where(db < med - 25)[0]
    runs = np.split(sil, np.where(np.diff(sil) != 1)[0] + 1) if len(sil) else []
    for r in runs:
        if len(r) >= 2 and 5 < r[0] < m - 10: E.append({'type': 'unexpected_silence', 't': fmt(r[0]), 'len_s': len(r)})
    out['level_range_db'] = round(float(np.percentile(db, 95) - np.percentile(db, 5)), 1)
    if out['level_range_db'] > 10: W.append({'type': 'wide_level_range', 'db': out['level_range_db']})
    # spectral balance: bass share, percussive share
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=1024)) ** 2
    fr = librosa.fft_frequencies(sr=SR, n_fft=2048); tot = S.sum(0) + 1e-12
    out['bass_share'] = round(float((S[fr < 120].sum(0) / tot).mean()), 3)
    H, P = librosa.decompose.hpss(S); out['percussive_share'] = round(float(P.sum() / (H.sum() + P.sum())), 3)
    if out['bass_share'] > 0.35: E.append({'type': 'excessive_bass', 'share': out['bass_share']})
    if out['percussive_share'] > 0.25: E.append({'type': 'excessive_percussion', 'share': out['percussive_share']})
    # abrupt tonal change / edit point: chroma + spectral-centroid jump between adjacent 5 s windows
    chroma = librosa.feature.chroma_stft(S=S, sr=SR, hop_length=1024)
    cent = librosa.feature.spectral_centroid(S=np.sqrt(S), sr=SR)[0]
    fps = SR / 1024; win = int(5 * fps); k = chroma.shape[1] // win
    if k > 2:
        C = np.array([chroma[:, i * win:(i + 1) * win].mean(1) for i in range(k)]); C /= (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)
        Z = np.array([cent[i * win:(i + 1) * win].mean() for i in range(k)])
        sims = (C[1:] * C[:-1]).sum(1); dz = np.abs(np.diff(Z)) / (Z[:-1] + 1e-9)
        for i in np.where((sims < 0.80) | (dz > 0.35))[0][:10]:
            hard = (sims[i] < 0.60 and dz[i] > 0.25) or dz[i] > 0.5
            (E if hard else W).append({'type': 'abrupt_tonal_change' if hard else 'tonal_drift_check_by_ear', 't': fmt((i + 1) * 5), 'chroma_sim': round(float(sims[i]), 2), 'centroid_jump': round(float(dz[i]), 2)})
        out['tonal_similarity_min'] = round(float(sims.min()), 2)
    # obvious loop: a 20 s window repeating almost exactly later on
    if dur > 120:
        mf = librosa.feature.mfcc(S=librosa.power_to_db(S), n_mfcc=13); seg = int(20 * fps); step = int(10 * fps)
        V = [mf[:, i:i + seg].flatten() for i in range(0, mf.shape[1] - seg, step)]
        V = np.array([v / (np.linalg.norm(v) + 1e-9) for v in V]); sim = V @ V.T
        np.fill_diagonal(sim, 0); iu = np.triu_indices(len(V), 3)
        out['max_self_similarity'] = round(float(sim[iu].max()), 3) if len(iu[0]) else 0
        if out['max_self_similarity'] > 0.995: W.append({'type': 'possible_audible_loop', 'sim': out['max_self_similarity']})
    out['spot_check'] = {p: fmt(dur * f) for p, f in [('start', 0), ('25%', .25), ('50%', .5), ('75%', .75), ('end', max(0, 1 - 30 / max(dur, 1)))]}
    out['pass'] = not E
    return out

if __name__ == '__main__':
    r = qc(sys.argv[1]); s = json.dumps(r, ensure_ascii=False, indent=1)
    if '--json' in sys.argv: open(sys.argv[sys.argv.index('--json') + 1], 'w').write(s)
    print(s)
