"""Dhamma Lab audio builder.
Script format: '## Chapter' lines, paragraphs separated by blank lines, '[พัก N]' = N seconds of silence.
Chunks are cut at pauses >= CUT_PAUSE; shorter pauses become sentence breaks inside a chunk.
Usage: python3 build_audio.py script.txt outdir --engine gemini --voice Sulafat --model gemini-3.8-flash-tts
"""
import re, os, sys, json, time, argparse, subprocess, hashlib
import numpy as np, soundfile as sf, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wavclean import extract_pcm

SR = 24000
CUT_PAUSE = 3

def parse(path):
    items = []  # ('chapter', title) | ('text', str) | ('pause', sec)
    for raw in open(path, encoding='utf-8').read().split('\n'):
        l = raw.strip()
        if not l:
            continue
        if l.startswith('## '):
            items.append(('chapter', l[3:].strip()))
            continue
        m = re.fullmatch(r'\[พัก (\d+(?:\.\d+)?)\]', l)
        if m:
            items.append(('pause', float(m.group(1))))
            continue
        items.append(('text', l))
    return items

def chunk(items, max_chars=320):
    chunks = []  # dict(text, pause_after, chapter)
    cur, chap = [], None
    def flush(pause):
        nonlocal cur, chap
        if cur:
            chunks.append({'text': '\n'.join(cur), 'pause_after': pause, 'chapter': chap})
            chap = None
        elif chunks:
            chunks[-1]['pause_after'] += pause
        cur = []
    for kind, v in items:
        if kind == 'chapter':
            flush(0.8)
            chap = v
        elif kind == 'pause':
            if v >= CUT_PAUSE:
                flush(v)
            else:
                if cur:
                    cur[-1] = cur[-1] + ' ...'
        else:
            if cur and sum(len(x) for x in cur) + len(v) > max_chars:
                flush(0.9)
            cur.append(v)
    flush(2.0)
    return chunks

STYLE = ("# AUDIO PROFILE\nA middle-aged Thai man with a warm, deep, gentle voice, narrating a calm Dhamma talk for bedtime listening. He is not a monk or a news announcer.\n\n"
"## DIRECTOR'S NOTES\nNatural Thai, calm and reassuring, slightly slower than normal conversation. Meaningful pauses after important thoughts and between sections; "
"ordinary sentences flow smoothly without long gaps. Intimate rather than formal. Weight each sentence by its meaning (comforting, encouraging, reflective, relaxing). "
"No announcer style, no exaggerated emotion, no robotic rhythm.\n\n"
"## TRANSCRIPT\nRead ONLY the transcript below, word for word, from the first word to the last. Do not add, skip, paraphrase or improvise anything. Do not speak these notes.\n\n")
STYLE_SLOW = STYLE.replace("slightly slower than normal conversation", "softer and a little slower, gently guiding the listener into relaxation and sleep")
SLOW_CHAPTERS = ("ผ่อนคลาย", "แผ่เมตตา", "หลับอย่างสงบ", "ก่อนหลับ")

STYLE_STORY = ("# AUDIO PROFILE\nA middle-aged Thai man with a warm, deep, gentle voice, telling classic Buddhist Jataka tales at bedtime, "
"like a kind storyteller sitting beside the bed. He is not a monk or a news announcer.\n\n"
"## DIRECTOR'S NOTES\nNatural Thai storytelling, calm and warm, slightly slower than normal conversation. Let the story breathe: "
"a little more colour for scenes and for the characters' lines, but never theatrical, never loud, no character voices or accents. "
"Meaningful pauses after important moments. Keep the overall energy low and soothing for sleep.\n\n"
"## TRANSCRIPT\nRead ONLY the transcript below, word for word, from the first word to the last. Do not add, skip, paraphrase or improvise anything. Do not speak these notes.\n\n")
# DEPRECATED (Directive 28 Sep 2026): STYLE, STYLE_SLOW and STYLE_STORY ("a little more colour for the characters")
# are kept only so old caches/legacy scripts still import. tts_gemini() refuses them in normal production.

# Channel voice identity (Voice Policy 28 Sep 2026): ONE narrator, ONE prompt for every chunk of every format.
# Pace/emotion may vary through the text itself and post-production pauses, never through a different persona prompt.
STYLE_CHANNEL = ("# AUDIO PROFILE\nA middle-aged Thai man with a soft, deep, warm, calm and reassuring voice; a kind lay narrator, not a monk, actor or announcer.\n\n"
"## DIRECTOR'S NOTES\nOne single speaker throughout: keep the same voice, pitch and age for every sentence. Quoted speech is read by the same narrator "
"in his own natural pitch, only with a slight change of emphasis and pause; never use a different or character voice. "
"Natural Thai, slightly slower than normal conversation, gentle and low in energy, pauses follow the meaning.\n\n"
"## TRANSCRIPT\nRead ONLY the transcript below, word for word, from the first word to the last. Do not add, skip, paraphrase or improvise anything. Do not speak these notes.\n\n")
PROFILES = {'channel': STYLE_CHANNEL}          # the ONLY narration profile for every format (talk, Jataka, sleep, Shorts)
PRIMARY_VOICE = 'Umbriel'

class VoicePolicyError(RuntimeError):
    pass

def enforce_voice_policy(voice, style):
    """One narrator, one voice, one prompt. Anything else needs an explicit manual override for a documented reason."""
    if os.environ.get('DHAMMALAB_VOICE_POLICY_OVERRIDE') == '1':
        print('WARNING: voice policy override active (manual, not for normal production)', flush=True); return
    if voice != PRIMARY_VOICE:
        raise VoicePolicyError(f'voice {voice!r} blocked: Primary Voice is {PRIMARY_VOICE} (one narrator per video)')
    if style is not None and style != STYLE_CHANNEL:
        name = 'STYLE_STORY' if style == STYLE_STORY else 'STYLE_SLOW' if style == STYLE_SLOW else 'STYLE' if style == STYLE else 'custom style'
        raise VoicePolicyError(f'{name} blocked: every narrated format uses STYLE_CHANNEL (calm adult storyteller, not voice actor)')

def clean(fn):
    """raw Make/Gemini WAV (nested WAV + C2PA box inside data) -> plain PCM WAV next to it"""
    out = fn[:-4] + '.c.wav'
    if not os.path.exists(out):
        x, sr = extract_pcm(fn)
        sf.write(out, x, sr, subtype='PCM_16')
    return out

def style_to_system(style):
    """delivery notes for systemInstruction: same notes, but the transcript travels alone in `contents`"""
    if not style: return None
    notes = style.split('## TRANSCRIPT')[0].rstrip()
    return notes + ("\n\n## TRANSCRIPT RULES\nThe user message is the exact Thai transcript. Speak it word for word, from the first word to the last, "
                    "as one single narrator. Do not add, skip, paraphrase or improvise anything, and never speak these instructions.")

def tts_gemini(text, voice, model, cache, style=None, salt=''):
    """One narration take. Order: (1) existing Make-era cache (never regenerate good audio),
    (2) direct Gemini API worker (default, env DHAMMALAB_TTS_ENGINE=direct), (3) Make webhook only as rollback (=make)."""
    style = style or STYLE_CHANNEL
    enforce_voice_policy(voice, style)
    key = hashlib.sha1((voice + model + style + text + salt).encode()).hexdigest()[:16]
    fn = os.path.join(cache, f'{key}.wav')
    if os.path.exists(fn):
        return clean(fn)
    engine = os.environ.get('DHAMMALAB_TTS_ENGINE', 'direct')
    if engine == 'direct':
        import gemini_tts
        return clean(gemini_tts.synth(text, voice, model, cache, style_to_system(style), salt=salt, prompt_style=style))
    if engine != 'make':
        raise RuntimeError(f'unknown DHAMMALAB_TTS_ENGINE={engine!r} (use direct, or make for a manual rollback)')
    from make_guard import make_endpoint   # refuses unless Make ops were checked today
    hook, secret = make_endpoint('tts rollback')
    for attempt in range(4):
        r = requests.post(hook, json={'key': secret, 'model': model, 'voice': voice, 'text': style + text}, timeout=300)
        if r.status_code == 200 and r.headers.get('content-type', '').startswith('audio'):
            open(fn, 'wb').write(r.content)
            return clean(fn)
        print('  tts retry', attempt, r.status_code, r.text[:200], flush=True)
        time.sleep(15 * (attempt + 1))
    raise RuntimeError('TTS failed')

_ASR = None
def asr_sim(fn, text):
    global _ASR
    import difflib
    if _ASR is None:
        from faster_whisper import WhisperModel
        _ASR = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)
    segs, _ = _ASR.transcribe(fn, language="th", beam_size=1, vad_filter=True, condition_on_previous_text=False)
    hyp = re.sub(r'[\s\.…,ๆ]+', '', ''.join(x.text for x in segs))
    ref = re.sub(r'[\s\.…,ๆ]+', '', text)
    return round(difflib.SequenceMatcher(None, ref, hyp).ratio(), 3)

def load(fn):
    d, sr = sf.read(fn, dtype='float32', always_2d=True)
    d = d.mean(axis=1)
    if sr != SR:
        import scipy.signal as ss
        d = ss.resample_poly(d, SR, sr).astype('float32')
    return d

def trim(x, thr=0.004):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(0.05 * SR)); b = min(len(x), idx[-1] + int(0.12 * SR))
    return x[a:b]

def squeeze_gaps(x, max_gap=2.0, to_gap=1.6, thr_db=-45):
    """shorten internal silences longer than max_gap to to_gap (keeps pause rhythm consistent across takes)"""
    w = int(0.02 * SR); n = len(x) // w
    if n < 3: return x
    db = 20 * np.log10(np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(1)) + 1e-9)
    sil = db < thr_db; out = []; i = 0; last = 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            if (j - i) * w / SR > max_gap and i > 0 and j < n:
                keep = int(to_gap * SR / 2)
                out.append(x[last:i * w + keep]); last = j * w - keep
            i = j
        else:
            i += 1
    out.append(x[last:])
    return np.concatenate(out)

def stretch(x, tempo):
    """pitch- and formant-preserving tempo change (same voice, a little slower)"""
    import subprocess as sp
    raw = sp.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-af',
                  f'rubberband=tempo={tempo}:pitch=1:formant=preserved:pitchq=quality:transients=mixed:detector=compound',
                  '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-'], input=x.astype('float32').tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()

def level(x, target=-20.0, max_gain_db=4.0):
    """equal loudness per chunk (speech-gated LUFS), bounded gain"""
    import pyloudnorm as pyln
    if len(x) < SR: return x
    L = pyln.Meter(SR).integrated_loudness(x)
    if not np.isfinite(L): return x
    g = float(np.clip(target - L, -max_gain_db, max_gain_db))
    return (x * 10 ** (g / 20)).astype('float32')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('script'); ap.add_argument('outdir')
    ap.add_argument('--engine', default='gemini'); ap.add_argument('--voice', default='Umbriel')
    ap.add_argument('--model', default='gemini-3.8-flash-tts'); ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--lead', type=float, default=1.2)   # Audio Structure Policy: narration starts 0.8-1.5 s in, no dead air
    ap.add_argument('--profile', default='channel', choices=['channel'])
    ap.add_argument('--slow_tempo', type=float, default=0.94, help='channel profile: tempo for relaxation/sleep chapters (same voice)')
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True); cache = os.path.join(a.outdir, 'cache'); os.makedirs(cache, exist_ok=True)
    ch = chunk(parse(a.script))
    if a.limit:
        ch = ch[:a.limit]
    print('chunks', len(ch), 'chars', sum(len(c['text']) for c in ch), flush=True)
    parts = [np.zeros(int(a.lead * SR), dtype='float32')]
    t = a.lead; chapters = []
    import concurrent.futures as cf
    styles = []; slow = False; slow_flags = []
    base = PROFILES[a.profile]
    for c in ch:
        if c['chapter']:
            slow = any(k in c['chapter'] for k in SLOW_CHAPTERS)
        styles.append(STYLE_SLOW if (slow and a.profile != 'channel') else base)
        slow_flags.append(slow)  # channel profile: one prompt for everything
    with cf.ThreadPoolExecutor(6) as ex:   # prefetch first take of every chunk in parallel
        first = list(ex.map(lambda k: tts_gemini(ch[k]['text'], a.voice, a.model, cache, styles[k], salt=''), range(len(ch))))
    print('prefetched', len(first), flush=True)
    qa = []; starts = []
    ov_fn = os.path.join(a.outdir, 'overrides.json')
    overrides = json.load(open(ov_fn)) if os.path.exists(ov_fn) else {}
    for i, c in enumerate(ch):
        if c['chapter']:
            chapters.append((t, c['chapter']))
        best = None
        hi = 0.16 if styles[i] is STYLE_SLOW else 0.135
        salts = ['', 'b', 'r1a', 'r1b', 'r2a']
        if str(i + 1) in overrides:          # take verified word-exact by retake.py
            salts = [overrides[str(i + 1)]]
        for sl in salts:
            fn = tts_gemini(c['text'], a.voice, a.model, cache, styles[i], salt=sl)
            x = trim(load(fn)); spc = (len(x) / SR) / max(1, len(c['text']))
            suspicious = len(c['text']) >= 60 and not (0.075 <= spc <= hi)
            sim = asr_sim(fn, c['text']) if suspicious else None
            score = sim if sim is not None else 0.9
            qa.append({'chunk': i + 1, 'salt': sl, 'sec_per_char': round(spc, 3), 'asr_checked': suspicious, 'sim': sim})
            if best is None or score > best[1]:
                best = (x, score)
            if score >= 0.75 or str(i + 1) in overrides:
                break
            print(f'  chunk {i+1} suspicious (spc {spc:.3f}, sim {sim}) -> retake', flush=True)
        x = best[0].copy()
        if a.profile == 'channel':
            x = squeeze_gaps(x)
            if slow_flags[i] and a.slow_tempo < 1.0:
                x = stretch(x, a.slow_tempo)
            x = level(x)
        fl = min(int(0.008 * SR), len(x) // 4)   # 8 ms raised-cosine edges: no step at chunk joins
        ramp = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fl))).astype('float32')
        x[:fl] *= ramp; x[-fl:] *= ramp[::-1]
        assert np.abs(x[:int(0.004 * SR)]).max() < 0.2, f'chunk {i+1}: loud head (header bytes?)'
        starts.append((round(t, 2), c['text'][:40])); parts.append(x); t += len(x) / SR
        gap = np.zeros(int(c['pause_after'] * SR), dtype='float32'); parts.append(gap); t += len(gap) / SR
        print(f'  [{i+1}/{len(ch)}] {len(x)/SR:.1f}s sim={best[1]}', flush=True)
    json.dump(qa, open(os.path.join(a.outdir, 'qa.json'), 'w'), ensure_ascii=False, indent=1)
    voice = np.concatenate(parts)
    sf.write(os.path.join(a.outdir, 'voice.wav'), voice, SR)
    json.dump({'duration': len(voice) / SR, 'chapters': chapters, 'chunks': starts}, open(os.path.join(a.outdir, 'meta.json'), 'w'), ensure_ascii=False, indent=1)
    print('voice duration', len(voice) / SR)

if __name__ == '__main__':
    import freeze; freeze.check()
    main()
