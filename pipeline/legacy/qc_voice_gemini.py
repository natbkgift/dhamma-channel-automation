"""LEGACY / ROLLBACK ONLY - spends Make operations. Never called by normal production.
Requires an open make_guard rollback session and DHAMMALAB_MAKE_ROLLBACK=1."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
"""Voice text QC with Gemini transcription (accuracy only - never a 'pleasantness' score).
Splits the narration bus at pauses >= 2.5 s, transcribes each segment, aligns the whole transcript with the script
and lists passages that were added, dropped or changed (>= 6 Thai chars).
usage: python3 qc_voice_gemini.py script.txt voice.wav out.json"""
import sys, re, io, json, base64, difflib, subprocess, concurrent.futures as cf
import numpy as np, soundfile as sf, requests

from make_guard import make_endpoint
hook, key = make_endpoint('transcribe')

sys.path.insert(0, '/home/claude/lab/pipeline')
from voice_takes import norm   # digits -> Thai number words, accepted spelling variants

script = open(sys.argv[1], encoding='utf-8').read()
ref_lines = [l.strip() for l in script.split('\n') if l.strip() and not l.startswith('## ') and not re.fullmatch(r'\[พัก [\d.]+\]', l.strip())]
ref = norm(''.join(ref_lines))
x, sr = sf.read(sys.argv[2], dtype='float32')
w = int(sr * 0.05); n = len(x) // w
db = 20 * np.log10(np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(1)) + 1e-9)
act = db > -45
segs = []; i = 0
while i < n:
    if not act[i]: i += 1; continue
    j = i; sil = 0
    while j < n and (sil < 50):  # stop after 2.5 s of silence
        sil = sil + 1 if not act[j] else 0; j += 1
    segs.append((i * w, (j - sil) * w)); i = j
# merge very short segments into neighbours, cap at ~90 s
merged = []
for a, b in segs:
    if merged and (b - merged[-1][0]) / sr < 90 and (a - merged[-1][1]) / sr < 6 and (b - a) / sr < 8:
        merged[-1] = (merged[-1][0], b)
    else:
        merged.append((a, b))
print('segments', len(merged), flush=True)

def tx(k):
    a, b = merged[k]
    seg = x[max(0, a - int(0.2 * sr)):b + int(0.3 * sr)]
    wav = io.BytesIO(); sf.write(wav, seg, sr, format='WAV')
    mp3 = subprocess.run(['ffmpeg', '-v', 'error', '-i', '-', '-ac', '1', '-b:a', '48k', '-f', 'mp3', '-'],
                         input=wav.getvalue(), capture_output=True).stdout
    for attempt in range(3):
        r = requests.post(hook, json={'key': key, 'mode': 'transcribe', 'fname': f'seg{k}.mp3',
                                      'audio_b64': base64.b64encode(mp3).decode()}, timeout=300)
        if r.status_code == 200:
            t = r.text
            try:
                j = json.loads(t)
                t = ''.join(pp.get('audioTranscription', {}).get('text', '') or pp.get('text', '') for pp in j['content']['parts'])
            except Exception:
                pass
            return k, t
    return k, None

with cf.ThreadPoolExecutor(4) as ex:
    res = dict(ex.map(tx, range(len(merged))))
failed = [k for k, v in res.items() if v is None]
hyp = ''; tmap = []
for k in range(len(merged)):
    t = norm(res[k] or '')
    for c in range(len(t)):
        tmap.append(merged[k][0] / sr)
    hyp += t
sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
issues = []
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == 'equal': continue
    r_, h_ = ref[i1:i2], hyp[j1:j2]
    if max(len(r_), len(h_)) >= 6:
        issues.append({'t_seg_start': round(tmap[min(j1, len(tmap) - 1)], 1) if tmap else None, 'op': op,
                       'script': r_, 'heard': h_})
out = {'similarity': round(sm.ratio(), 4), 'segments': len(merged), 'failed_segments': failed,
       'ref_chars': len(ref), 'hyp_chars': len(hyp), 'long_diffs': issues,
       'transcripts': {k: res[k] for k in range(len(merged))}}
json.dump(out, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
print('similarity', out['similarity'], 'failed', failed, 'long diffs', len(issues))
for d in issues: print(d)
