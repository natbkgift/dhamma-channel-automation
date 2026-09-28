"""Move shot boundaries of an existing visual timeline to a re-rendered narration.
Boundaries were placed on narration chunk starts; map old times -> new times piecewise-linearly through chunk starts.
usage: python3 remap_timeline.py old_timeline.json old_meta.json new_meta.json out_timeline.json"""
import sys, json, numpy as np
tl = json.load(open(sys.argv[1])); om = json.load(open(sys.argv[2])); nm = json.load(open(sys.argv[3]))
o = np.array([0.0] + [c[0] for c in om['chunks']] + [om['duration']]); n = np.array([0.0] + [c[0] for c in nm['chunks']] + [nm['duration']])
assert len(o) == len(n), 'chunk count changed'
D = tl['duration']
def f(t):
    if t >= o[-1]: return t - o[-1] + n[-1]      # after narration: shift by the narration length difference
    return float(np.interp(t, o, n))
for s in tl['shots']:
    s['start'] = round(f(s['start']), 2) if s['start'] > 0 else 0
    s['end'] = round(f(s['end']), 2) if s['end'] < D else D
b = tl['brightness']; tl['brightness'] = [[round(f(t), 2) if 0 < t < D else t, v] for t, v in b]
json.dump(tl, open(sys.argv[4], 'w'), indent=1)
for s in tl['shots']: print(s['name'], s['start'], s['end'])
print('brightness', tl['brightness'])
