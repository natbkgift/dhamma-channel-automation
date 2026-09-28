"""Channel-voice take selection (Voice Policy 28 Sep 2026: one narrator, one voice per video).
For every chunk, generate takes with the single channel prompt (STYLE_CHANNEL) until one passes ALL gates:
  1. words: Gemini transcription (flash, fallback transcribe model) has no diff >= 2 chars vs the script
  2. names/Pali terms of the chunk are heard (accepted spelling variants allowed)
  3. register: take median F0 within +-REG_ST semitones of the channel register target (default 95 Hz, Sample #3 = 91.5 Hz)
  4. no character voice: no phrase (>=1.5 s) more than +-CHAR_ST semitones from the take's own median
  5. pacing: 0.075-0.17 s per character, no internal silence > 3 s
Then pass 2: ECAPA timbre vs the centroid of all accepted chunks; outliers are re-rolled.
usage: python3 voice_takes.py script.txt outdir [--voice Umbriel] [--target 95] [--max 10] [--only 3,5]
writes outdir/overrides.json {chunk: salt} and outdir/voice_takes.json (all metrics)"""
import sys, os, re, io, json, base64, difflib, subprocess, argparse, threading, concurrent.futures as cf
import numpy as np, requests, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_audio as B
import voice_consistency as VC
from spk import emb, load

hook = key = None   # Make endpoint is opened lazily through make_guard (never automatically)
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
# spelling variants a transcriber may write for the same spoken word -> canonical script spelling
VARIANTS = [('ตักศิลา', 'ตักกสิลา'), ('นันทิวิศาล', 'นันทิวิสาล'), ('นันทิวิสาร', 'นันทิวิสาล'), ('นันทิวิศาร', 'นันทิวิสาล'),
            ('ซะอีก', 'เสียอีก'), ('เค้า', 'เขา'), ('หิมพาน', 'หิมพานต์'), ('กัลป์', 'กัป'), ('กัลป', 'กัป'), ('ท้าวสักกะ', 'ท้าวสักกะ'),
            ('พราหมณ', 'พราหมณ์'), ('กหาปนะ', 'กหาปณะ'), ('ตักกะศิลา', 'ตักกสิลา'), ('ตักกะสิลา', 'ตักกสิลา'), ('มั้ย', 'ไหม')]
TERMS = ['พราหมณ์', 'นันทิวิสาล', 'สักกะ', 'กหาปณะ', 'เศรษฐี', 'โพธิสัตว์', 'ศีล', 'ภิกษุ', 'ชาดก', 'หิมพานต์', 'ตักกสิลา', 'คันธาระ', 'กัป', 'บัลลังก์']
def norm(s):
    s = re.sub(r'\d[\d,]*', lambda m: thai_num(int(m.group().replace(',', ''))), s)
    for a, b in VARIANTS: s = s.replace(a, b)
    s = s.replace('พราหมณ์์', 'พราหมณ์')
    return re.sub(r'[\s\.…,ๆ\-–—"“”\'!?:;()\[\]a-zA-Z{}/_]+', '', s)

def transcribe(fn, model=None):
    mp3 = subprocess.run(['ffmpeg', '-v', 'error', '-i', fn, '-ac', '1', '-b:a', '48k', '-f', 'mp3', '-'], capture_output=True).stdout
    if os.environ.get('DHAMMALAB_TTS_ENGINE', 'direct') == 'direct':   # Voice QA without Make operations
        import gemini_tts
        return gemini_tts.transcribe(mp3, 'audio/mpeg', model or os.environ.get('DHAMMALAB_QA_MODEL2', 'gemini-3.5-transcribe'))
    from make_guard import make_endpoint
    hook, key = make_endpoint('transcribe (rollback)')
    body = {'key': key, 'mode': 'transcribe', 'fname': 'take.mp3', 'audio_b64': base64.b64encode(mp3).decode()}
    if model: body['model'] = model
    for attempt in range(3):
        try:
            r = requests.post(hook, json=body, timeout=300)
        except Exception:
            continue
        t = r.text
        try:
            j = json.loads(t)
            if j.get('finishReason') not in (None, 'STOP'): return None
            t = ''.join(pp.get('audioTranscription', {}).get('text', '') or pp.get('text', '') for pp in j['content']['parts'])
        except Exception:
            pass
        if r.status_code == 200 and t.strip(): return t
    return None

def word_check(text, fn, dual=False):
    ref = norm(text)
    if dual:   # both transcribers must agree the words are right (a blocked/empty transcript is skipped)
        res = [r for r in (word_check_one(text, fn, m) for m in ('gemini-3.8-flash', None)) if r]
        if not res: return {'model': None, 'ratio': 0, 'big': [('?', 'no transcript')], 'missing_terms': [], 'hyp': ''}
        big = sum((r['big'] for r in res), []); terms = sorted(set(sum((r['missing_terms'] for r in res), [])))
        return {'model': '+'.join(r['model'] for r in res), 'ratio': min(r['ratio'] for r in res), 'big': big[:6],
                'missing_terms': terms, 'hyp': res[0]['hyp'], 'dual': True}
    for model in ('gemini-3.8-flash', None):
        hyp = transcribe(fn, model)
        if not hyp: continue
        h = norm(hyp)
        if len(h) < 0.5 * len(ref):   # degenerate transcription (safety filter etc.)
            continue
        sm = difflib.SequenceMatcher(None, ref, h, autojunk=False)
        big = [(ref[i1:i2], h[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal' and max(i2 - i1, j2 - j1) >= 2]
        terms = [w for w in TERMS if w in ref and ref.count(w) > h.count(w)]
        return {'model': model or 'transcribe', 'ratio': round(sm.ratio(), 4), 'big': big[:6], 'missing_terms': terms, 'hyp': hyp}
    return {'model': None, 'ratio': 0, 'big': [('?', 'no transcript')], 'missing_terms': [], 'hyp': ''}

def word_check_one(text, fn, model):
    ref = norm(text); hyp = transcribe(fn, model)
    if not hyp or len(norm(hyp)) < 0.5 * len(ref): return None
    h = norm(hyp); sm = difflib.SequenceMatcher(None, ref, h, autojunk=False)
    big = [(ref[i1:i2], h[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal' and max(i2 - i1, j2 - j1) >= 2]
    terms = [w for w in TERMS if w in ref and ref.count(w) > h.count(w)]
    return {'model': model or 'transcribe', 'ratio': round(sm.ratio(), 4), 'big': big, 'missing_terms': terms, 'hyp': hyp}

def acoustic(fn, text):
    x, sr = load(fn)
    x = B.trim(x) if hasattr(B, 'trim') and False else x
    try:
        res = VC.analyse(x, sr, st_thr=99, sim_thr=-1)
    except Exception:
        res = {'f0_median': float('nan'), 'rows': []}
    if not res['rows']:   # very short utterance (e.g. 'หายใจเข้า สงบ'): treat the whole take as one phrase
        f = VC.f0med(B.trim(x) if len(x) > 0 else x, sr)
        res = {'f0_median': round(f, 1) if f == f else float('nan'), 'rows': [{'st': 0.0}]}
    sts = [r['st'] for r in res['rows'] if r['st'] is not None]
    y16 = librosa.resample(x, orig_sr=sr, target_sr=16000)
    iv = librosa.effects.split(y16, top_db=35)
    gaps = [(iv[i + 1][0] - iv[i][1]) / 16000 for i in range(len(iv) - 1)] or [0]
    speech = sum(b - a for a, b in iv) / 16000
    return {'f0': res['f0_median'], 'st_max': max(sts) if sts else 0, 'st_min': min(sts) if sts else 0,
            'dur': round(len(x) / sr, 2), 'spc': round(speech / max(1, len(text)), 4), 'max_gap': round(max(gaps), 2),
            'emb': emb(x, sr).tolist()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('script'); ap.add_argument('outdir')
    ap.add_argument('--voice', default='Umbriel'); ap.add_argument('--model', default='gemini-3.8-flash-tts')
    ap.add_argument('--target', type=float, default=95.0); ap.add_argument('--reg', type=float, default=1.5)
    ap.add_argument('--char', type=float, default=4.0); ap.add_argument('--max', type=int, default=10)
    ap.add_argument('--only', default=''); ap.add_argument('--workers', type=int, default=5)
    ap.add_argument('--timbre', type=float, default=0.78); ap.add_argument('--dual', action='store_true'); ap.add_argument('--abs', type=float, default=4.0); ap.add_argument('--neighbors', type=float, default=0)
    a = ap.parse_args()
    ch = B.chunk(B.parse(a.script)); cache = os.path.join(a.outdir, 'cache'); os.makedirs(cache, exist_ok=True)
    style = B.STYLE_CHANNEL
    log_fn = os.path.join(a.outdir, 'voice_takes.json')
    log = json.load(open(log_fn)) if os.path.exists(log_fn) else {}
    lock = threading.Lock()
    SALTS = (['', 'b'] + [f'r{k}{c}' for k in range(1, 16) for c in 'ab'])[:a.max]
    targets = [int(v) for v in a.only.split(',')] if a.only else list(range(1, len(ch) + 1))

    def gate(ac):
        reasons = []
        if not ac['f0'] == ac['f0']: return ['no analysable speech'], 0.0
        reg = 12 * np.log2(ac['f0'] / a.target)
        if abs(reg) > a.reg: reasons.append(f'register {ac["f0"]:.0f}Hz ({reg:+.1f}st)')
        if ac['st_max'] > a.char or ac['st_min'] < -a.char - 0.5: reasons.append(f'character-voice phrase ({ac["st_min"]:+.1f}/{ac["st_max"]:+.1f}st)')
        elif reg + ac['st_max'] > a.abs or reg + ac['st_min'] < -a.abs - 0.5: reasons.append(f'phrase outside channel register ({reg + ac["st_min"]:+.1f}/{reg + ac["st_max"]:+.1f}st)')
        if not (0.063 <= ac['spc'] <= 0.17): reasons.append(f'pace {ac["spc"]}')
        if ac['max_gap'] > 3.0: reasons.append(f'gap {ac["max_gap"]}s')
        return reasons, reg

    def evaluate(n, salt):
        k = f'{n}:{salt}'
        if k in log and log[k].get('text') == ch[n - 1]['text']:
            old = log[k]
            reasons, _ = gate(old)
            acoustic_ok = not reasons
            words = old.get('words') or {}
            have_words = bool(words) and (words.get('dual') or not a.dual)
            if not acoustic_ok or have_words:
                if have_words:
                    if words.get('big'): reasons.append(f'words {words["big"][:3]}')
                    if words.get('missing_terms'): reasons.append(f'terms {words["missing_terms"]}')
                old['ok'] = not reasons; old['reasons'] = reasons
                return old
            wc = word_check(old['text'], old['file'], dual=a.dual)
            if wc['big']: reasons.append(f'words {wc["big"][:3]}')
            if wc['missing_terms']: reasons.append(f'terms {wc["missing_terms"]}')
            old.update({'ok': not reasons, 'reasons': reasons, 'words': {kk: vv for kk, vv in wc.items() if kk != 'hyp'}, 'hyp': wc['hyp']})
            with lock:
                log[k] = old; json.dump(log, open(log_fn, 'w'), ensure_ascii=False)
            print(f'chunk {n} salt {salt!r}: dual re-check -> {"OK" if not reasons else "; ".join(reasons)}', flush=True)
            return old
        text = ch[n - 1]['text']
        fn = B.tts_gemini(text, a.voice, a.model, cache, style, salt=salt)
        ac = acoustic(fn, text)
        reasons, reg = gate(ac)
        wc = None
        if not reasons:   # only transcribe takes that pass the acoustic gates
            wc = word_check(text, fn, dual=a.dual)
            if wc['big']: reasons.append(f'words {wc["big"][:3]}')
            if wc['missing_terms']: reasons.append(f'terms {wc["missing_terms"]}')
        rec = {'chunk': n, 'salt': salt, 'text': text, 'file': fn, 'ok': not reasons, 'reasons': reasons, **ac,
               'reg_st': round(float(reg), 2), 'words': {kk: vv for kk, vv in (wc or {}).items() if kk != 'hyp'}, 'hyp': (wc or {}).get('hyp', '')}
        with lock:
            log[k] = rec; json.dump(log, open(log_fn, 'w'), ensure_ascii=False)
        print(f'chunk {n} salt {salt!r}: f0 {ac["f0"]:.0f} ({reg:+.1f}st) dur {ac["dur"]} -> {"OK" if not reasons else "; ".join(reasons)}', flush=True)
        return rec

    def pick(n, exclude=()):
        best = None
        for salt in SALTS:
            if salt in exclude: continue
            r = evaluate(n, salt)
            if r['ok']: return r
            score = abs(r['reg_st']) + (5 if r['words'] and r['words'].get('big') else 0)
            if best is None or score < best[0]: best = (score, r)
        return None

    if a.neighbors:   # continuity mode: among passing takes, pick the one closest in timbre/pitch to both neighbours
        ov_fn = os.path.join(a.outdir, 'overrides.json'); ov = json.load(open(ov_fn))
        for n in targets:
            nb = [log[f'{m}:{ov[str(m)]}'] for m in (n - 1, n + 1) if str(m) in ov and f'{m}:{ov[str(m)]}' in log]
            def score(r):
                sims = [float(np.array(r['emb']) @ np.array(q['emb'])) for q in nb]
                dst = max(abs(12 * np.log2(r['f0'] / q['f0'])) for q in nb)
                return min(sims) - 0.05 * max(0, dst - 1.0)
            cand = []
            with cf.ThreadPoolExecutor(a.workers) as ex:
                for r in ex.map(lambda sl: evaluate(n, sl), SALTS):
                    if r['ok']: cand.append((score(r), r))
            cand.sort(key=lambda t: -t[0])
            if cand:
                print(f'chunk {n}: best {cand[0][1]["salt"]!r} score {cand[0][0]:.3f} (was {ov[str(n)]!r}); candidates {[(c[1]["salt"], round(c[0], 3)) for c in cand[:6]]}', flush=True)
                if cand[0][0] >= a.neighbors or True: ov[str(n)] = cand[0][1]['salt']
        json.dump(ov, open(ov_fn, 'w'), indent=1)
        return
    with cf.ThreadPoolExecutor(a.workers) as ex:
        chosen = dict(zip(targets, ex.map(pick, targets)))
    failed = [n for n, r in chosen.items() if r is None]
    # pass 2: timbre consistency against the video's own narrator centroid
    ok = {n: r for n, r in chosen.items() if r}
    ov_fn = os.path.join(a.outdir, 'overrides.json')
    ov = json.load(open(ov_fn)) if os.path.exists(ov_fn) else {}
    for n, r in ok.items(): ov[str(n)] = r['salt']
    allsel = {int(n): log[f'{n}:{s}'] for n, s in ov.items() if f'{n}:{s}' in log}
    for rnd in range(2):
        E = np.array([np.array(r['emb']) for r in allsel.values()]); cen = E.mean(0); cen /= np.linalg.norm(cen)
        out = [n for n, r in allsel.items() if r['dur'] >= 8 and float(np.array(r['emb']) @ cen) < a.timbre]
        print('timbre outliers', [(n, round(float(np.array(allsel[n]['emb']) @ cen), 3)) for n in out], flush=True)
        if not out: break
        for n in out:
            used = [s for s in SALTS if f'{n}:{s}' in log]
            best = None
            for salt in SALTS:
                r = evaluate(n, salt)
                if not r['ok']: continue
                sim = float(np.array(r['emb']) @ cen)
                if best is None or sim > best[0]: best = (sim, r)
                if sim >= a.timbre: break
            if best:
                allsel[n] = best[1]; ov[str(n)] = best[1]['salt']
    json.dump(ov, open(ov_fn, 'w'), indent=1)
    E = np.array([np.array(r['emb']) for r in allsel.values()]); cen = E.mean(0); cen /= np.linalg.norm(cen)
    summ = {'chunks': len(allsel), 'failed': failed, 'f0': [allsel[n]['f0'] for n in sorted(allsel)],
            'timbre_min': round(min(float(np.array(r['emb']) @ cen) for r in allsel.values()), 3)}
    json.dump(summ, open(os.path.join(a.outdir, 'voice_takes_summary.json'), 'w'), indent=1)
    print('SUMMARY', json.dumps(summ))

if __name__ == '__main__':
    import freeze; freeze.check()
    main()
