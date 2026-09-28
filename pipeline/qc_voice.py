"""Voice QC: transcribe the narration bus and align it with the script to find added (hallucinated),
missing or mispronounced passages. Whisper is used ONLY for text accuracy, never to judge how pleasant a voice is.
usage: python3 qc_voice.py script.txt voice.wav out.json"""
import sys, re, json, difflib
from faster_whisper import WhisperModel

def norm(s):
    return re.sub(r'[\s\.…,ๆ\-–—"“”\'!?:;()\[\]0-9]+', '', s)

script = open(sys.argv[1], encoding='utf-8').read()
ref_lines = [l.strip() for l in script.split('\n') if l.strip() and not l.startswith('## ') and not re.fullmatch(r'\[พัก [\d.]+\]', l.strip())]
ref = norm(''.join(ref_lines))
m = WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=2)
segs, _ = m.transcribe(sys.argv[2], language='th', beam_size=1, vad_filter=True, condition_on_previous_text=False)
segs = list(segs)
hyp_parts = [(s.start, s.end, s.text) for s in segs]
hyp = ''; pos = []  # char index -> time
for st, en, tx in hyp_parts:
    t = norm(tx)
    for k in range(len(t)):
        pos.append(st + (en - st) * k / max(1, len(t)))
    hyp += t
sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
ratio = sm.ratio()
issues = []
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == 'equal':
        continue
    r, h = ref[i1:i2], hyp[j1:j2]
    t = round(pos[min(j1, len(pos) - 1)], 1) if pos else None
    # ASR on Thai makes many 1-3 char substitutions; only long differences are worth a human look
    if max(len(r), len(h)) >= 8:
        issues.append({'t': t, 'op': op, 'script': r, 'heard': h})
out = {'similarity': round(ratio, 4), 'ref_chars': len(ref), 'hyp_chars': len(hyp), 'long_diffs': issues}
json.dump(out, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
print('similarity', round(ratio, 4), 'long diffs', len(issues))
for d in issues[:40]:
    print(d)
