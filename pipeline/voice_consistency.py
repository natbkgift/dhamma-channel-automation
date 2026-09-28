"""Within-video narrator consistency: phrase-level pitch register + ECAPA timbre.
Splits narration at pauses >= 0.25 s into phrases; for phrases >= 1.5 s computes median F0 (semitones vs video median)
and ECAPA similarity to the video narrator centroid. Flags phrases that sound like a different speaker
(register shift > 3 st or timbre sim < thr).
usage: python3 voice_consistency.py voice.wav [out.json] [--ref ref.wav]"""
import sys, json, numpy as np, librosa
sys.path.insert(0, '/home/claude/lab/pipeline')
from spk import emb, load
def phrases(x, sr, min_gap=0.25, min_len=1.5):
    iv = librosa.effects.split(x, top_db=35, frame_length=1024, hop_length=256)
    segs = []
    for a, b in iv:
        if segs and (a - segs[-1][1]) / sr < min_gap: segs[-1][1] = b
        else: segs.append([a, b])
    return [(a, b) for a, b in segs if (b - a) / sr >= min_len]
def f0med(y, sr):
    y16 = librosa.resample(y, orig_sr=sr, target_sr=16000)
    f, v, _ = librosa.pyin(y16, fmin=55, fmax=320, sr=16000, frame_length=1024, hop_length=256)
    f = f[v & ~np.isnan(f)]
    return float(np.median(f)) if len(f) > 5 else np.nan
def analyse(x, sr, ref=None, st_thr=3.0, sim_thr=0.55):
    P = phrases(x, sr)
    rows = []
    for a, b in P:
        y = x[a:b]
        rows.append({'t': round(a / sr, 2), 'dur': round((b - a) / sr, 2), 'f0': f0med(y, sr), 'e': emb(y, sr)})
    f0s = np.array([r['f0'] for r in rows]); med = np.nanmedian(f0s)
    E = np.array([r['e'] for r in rows]); cen = E.mean(0); cen /= np.linalg.norm(cen)
    flags = []
    for r in rows:
        r['st'] = round(12 * np.log2(r['f0'] / med), 2) if r['f0'] == r['f0'] else None
        r['sim'] = round(float(r['e'] @ cen), 3)
        if ref is not None: r['sim_ref'] = round(float(r['e'] @ ref), 3)
        bad = (r['st'] is not None and abs(r['st']) > st_thr) or r['sim'] < sim_thr
        r['flag'] = bool(bad)
        del r['e']
    sims = np.array([r['sim'] for r in rows])
    return {'f0_median': round(float(med), 1), 'phrases': len(rows), 'sim_mean': round(float(sims.mean()), 3),
            'sim_p05': round(float(np.percentile(sims, 5)), 3), 'n_flag': int(sum(r['flag'] for r in rows)),
            'rows': rows}
if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ref = None
    if '--ref' in sys.argv: ref = emb(*load(sys.argv[sys.argv.index('--ref') + 1]))
    x, sr = load(args[0])
    res = analyse(x, sr, ref)
    print(json.dumps({k: v for k, v in res.items() if k != 'rows'}))
    for r in res['rows']:
        if r['flag']: print('FLAG', r)
    if len(args) > 1: json.dump(res, open(args[1], 'w'), indent=1)
