"""Chunk-to-chunk continuity of the narrator (catches a take that 'jumps out' from the one before it).
Uses the selected takes' metrics from voice_takes.json.
usage: python3 continuity.py outdir [--st 2.0] [--sim 0.6]"""
import sys, os, json, numpy as np
d = sys.argv[1]
st_thr = float(sys.argv[sys.argv.index('--st') + 1]) if '--st' in sys.argv else 2.0
sim_thr = float(sys.argv[sys.argv.index('--sim') + 1]) if '--sim' in sys.argv else 0.6
L = json.load(open(os.path.join(d, 'voice_takes.json'))); ov = json.load(open(os.path.join(d, 'overrides.json')))
sel = [L[f'{n}:{ov[str(n)]}'] for n in range(1, len(ov) + 1)]
flags = []
print('chunk  f0   d_st   sim_prev  dur')
for i, r in enumerate(sel):
    if i == 0: print(f'{i+1:>3} {r["f0"]:6.1f}'); continue
    p = sel[i - 1]
    dst = 12 * np.log2(r['f0'] / p['f0']); sim = float(np.array(r['emb']) @ np.array(p['emb']))
    short = min(r['dur'], p['dur']) < 8
    bad = abs(dst) > st_thr or (not short and sim < sim_thr)
    if bad: flags.append(i + 1)
    print(f'{i+1:>3} {r["f0"]:6.1f} {dst:+5.2f}   {sim:.3f}   {r["dur"]:5.1f} {"FLAG" if bad else ""}')
f0 = np.array([r['f0'] for r in sel])
print('f0 range %.1f-%.1f Hz (%.2f st), flags %s' % (f0.min(), f0.max(), 12 * np.log2(f0.max() / f0.min()), flags))
json.dump({'flags': flags, 'f0': f0.tolist()}, open(os.path.join(d, 'continuity.json'), 'w'))
