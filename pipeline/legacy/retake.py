"""LEGACY / ROLLBACK ONLY - spends Make operations. Never called by normal production.
Requires an open make_guard rollback session and DHAMMALAB_MAKE_ROLLBACK=1."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
"""Find a word-exact TTS take for flagged chunks, verified by Gemini transcription.
usage: python3 retake.py script.txt outdir voice chunk_no [chunk_no ...]
writes outdir/overrides.json {chunk_no: salt}"""
import sys, os, io, json, re, base64, difflib, subprocess, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_audio as B
import soundfile as sf

from make_guard import make_endpoint
hook, key = make_endpoint('transcribe')
DIG = ['ศูนย์', 'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า']
UNITS = ['', 'สิบ', 'ร้อย', 'พัน', 'หมื่น', 'แสน', 'ล้าน']
def thai_num(n):
    if n == 0: return DIG[0]
    s = str(n); out = ''
    for i, ch in enumerate(s):
        d = int(ch); pos = len(s) - i - 1
        if d == 0: continue
        if pos == 1 and d == 1: out += 'สิบ'
        elif pos == 1 and d == 2: out += 'ยี่สิบ'
        elif pos == 0 and d == 1 and len(s) > 1: out += 'เอ็ด'
        else: out += DIG[d] + UNITS[pos]
    return out
def norm(s):
    s = re.sub(r'\d[\d,]*', lambda m: thai_num(int(m.group().replace(',', ''))), s)
    return re.sub(r'[\s\.…,ๆ\-–—"“”\'!?:;()\[\]a-zA-Z{}]+', '', s)

def transcribe(fn):
    mp3 = subprocess.run(['ffmpeg', '-v', 'error', '-i', fn, '-ac', '1', '-b:a', '48k', '-f', 'mp3', '-'], capture_output=True).stdout
    r = requests.post(hook, json={'key': key, 'mode': 'transcribe', 'fname': 'take.mp3', 'audio_b64': base64.b64encode(mp3).decode()}, timeout=300)
    t = r.text
    try:
        j = json.loads(t); t = ''.join(pp.get('audioTranscription', {}).get('text', '') or pp.get('text', '') for pp in j['content']['parts'])
    except Exception:
        pass
    return t

script, outdir, voice = sys.argv[1], sys.argv[2], sys.argv[3]
profile = 'talk'
args = sys.argv[4:]
if args and args[0].startswith('--profile='):
    profile = args[0].split('=', 1)[1]; args = args[1:]
targets = [int(v) for v in args]
ch = B.chunk(B.parse(script)); cache = os.path.join(outdir, 'cache')
styles = []; slow = False
for c in ch:
    if c['chapter']: slow = any(k in c['chapter'] for k in B.SLOW_CHAPTERS)
    styles.append(B.STYLE_SLOW if slow else (B.PROFILES.get(profile) or B.STYLE))
ov_fn = os.path.join(outdir, 'overrides.json')
ov = json.load(open(ov_fn)) if os.path.exists(ov_fn) else {}
log = []
for n in targets:
    c = ch[n - 1]; ref = norm(c['text']); best = None
    qa_fn = os.path.join(outdir, 'qa.json'); cur = ''
    if os.path.exists(qa_fn):
        for q in json.load(open(qa_fn)):
            if q['chunk'] == n: cur = q['salt']
    salts = [cur] + [x for x in ['', 'b', 'r1a', 'r1b', 'r2a', 'r2b', 'r3a', 'r3b', 'r4a', 'r4b'] if x != cur]
    for salt in salts:
        fn = B.tts_gemini(c['text'], voice, 'gemini-3.8-flash-tts', cache, styles[n - 1], salt=salt)
        hyp = norm(transcribe(fn))
        sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
        diffs = [(ref[i1:i2], hyp[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal']
        big = [d for d in diffs if max(len(d[0]), len(d[1])) >= 2]
        score = sm.ratio()
        print(f'chunk {n} salt {salt!r}: ratio {score:.4f} diffs {big[:4]}', flush=True)
        log.append({'chunk': n, 'salt': salt, 'ratio': round(score, 4), 'diffs': big})
        if best is None or score > best[1]:
            best = (salt, score)
        if not big:
            break
    ov[str(n)] = best[0]
    print(f'==> chunk {n} use salt {best[0]!r} ({best[1]:.4f})', flush=True)
json.dump(ov, open(ov_fn, 'w'), indent=1)
json.dump(log, open(os.path.join(outdir, 'retake_log.json'), 'w'), ensure_ascii=False, indent=1)
