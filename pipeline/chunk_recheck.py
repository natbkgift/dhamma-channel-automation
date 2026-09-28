"""Re-transcribe chunks from an assembled narration with two models (flash + transcribe) to arbitrate diffs.
usage: python3 chunk_recheck.py script.txt outdir chunk_no|all [...]"""
import sys, os, json, io, difflib, subprocess, concurrent.futures as cf
import soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_audio as B
from voice_takes import norm, transcribe, TERMS
script, outdir = sys.argv[1], sys.argv[2]
ch = B.chunk(B.parse(script))
m = json.load(open(os.path.join(outdir, 'meta.json'))); st = [c[0] for c in m['chunks']] + [m['duration']]
x, sr = sf.read(os.path.join(outdir, 'voice.wav'), dtype='float32')
nums = list(range(1, len(ch) + 1)) if sys.argv[3] == 'all' else [int(v) for v in sys.argv[3:]]
def job(n):
    seg = x[max(0, int((st[n - 1] - 0.2) * sr)):int(st[n] * sr)]
    fn = f'/tmp/claude-0/rc_{n}.wav'; sf.write(fn, seg, sr)
    ref = norm(ch[n - 1]['text']); out = {'chunk': n}
    for model in ('gemini-3.8-flash', None):
        hyp = transcribe(fn, model)
        if not hyp or len(norm(hyp)) < 0.5 * len(ref): out[model or 'transcribe'] = 'n/a'; continue
        h = norm(hyp); sm = difflib.SequenceMatcher(None, ref, h, autojunk=False)
        out[model or 'transcribe'] = [(ref[max(0, i1 - 6):i2 + 6], h[max(0, j1 - 6):j2 + 6]) for op, i1, i2, j1, j2 in sm.get_opcodes()
                                      if op != 'equal' and max(i2 - i1, j2 - j1) >= 2]
    out['terms_missing'] = [w for w in TERMS if w in ref and (out.get('gemini-3.8-flash') == 'n/a')]
    return out
with cf.ThreadPoolExecutor(4) as ex:
    res = list(ex.map(job, nums))
for r in res: print(json.dumps(r, ensure_ascii=False))
json.dump(res, open(os.path.join(outdir, 'chunk_recheck.json'), 'w'), ensure_ascii=False, indent=1)
