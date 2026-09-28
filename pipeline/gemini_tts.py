"""DhammaLab direct Gemini TTS worker (no Make.com).
Content script -> this worker -> Gemini API (generativelanguage.googleapis.com) -> WAV chunk cache.

Secrets: the API key is read at runtime from $GEMINI_API_KEY or from ~/.config/dhammalab/gemini.env
(line GEMINI_API_KEY=...; file mode 600). It is never printed, logged, cached or written into metadata.

Delivery notes go into systemInstruction; the request `contents` carry ONLY the exact narration text.
Takes are reproducible: salt -> generationConfig.seed. Every successful chunk is cached as
<cache>/<key>.wav + <key>.json (engine, model, voice, style hash, text hash, seed, time, token usage),
so re-renders never call the API for audio that already exists.
"""
import os, io, json, time, wave, base64, hashlib, datetime, random
import requests

API = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
LEDGER = os.path.expanduser('~/.config/dhammalab/tts_ledger.jsonl')

class QuotaExhausted(RuntimeError):
    pass

def _key():
    # 1) DHAMMALAB_GEMINI_API_KEY (environment secret, preferred: survives new sessions/containers)
    # 2) GEMINI_API_KEY  3) ~/.config/dhammalab/gemini.env (chmod 600, this container only)
    k = os.environ.get('DHAMMALAB_GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
    if not k and os.environ.get('DHAMMALAB_NO_LOCAL_KEY') != '1':
        fn = os.path.expanduser('~/.config/dhammalab/gemini.env')
        if os.path.exists(fn):
            for line in open(fn):
                if line.startswith(('DHAMMALAB_GEMINI_API_KEY=', 'GEMINI_API_KEY=')):
                    k = line.split('=', 1)[1].strip()
    # 4) none: the Claude cloud environment's API credential (agent proxy) adds x-goog-api-key for
    #    generativelanguage.googleapis.com after the request leaves the VM -> send without a key header.
    return k or None

def _headers():
    k = _key()
    h = {'Content-Type': 'application/json'}
    if k:
        h['x-goog-api-key'] = k
    return h

def key_source():
    if os.environ.get('DHAMMALAB_GEMINI_API_KEY'): return 'env:DHAMMALAB_GEMINI_API_KEY'
    if os.environ.get('GEMINI_API_KEY'): return 'env:GEMINI_API_KEY'
    if os.environ.get('DHAMMALAB_NO_LOCAL_KEY') != '1' and os.path.exists(os.path.expanduser('~/.config/dhammalab/gemini.env')): return 'file:~/.config/dhammalab/gemini.env (temporary)'
    return 'proxy:cloud-environment API credential'

def seed_for(salt):
    return int(hashlib.sha1(('dhammalab|' + salt).encode()).hexdigest()[:7], 16)

def cache_key(text, voice, model, style, salt):
    return hashlib.sha1(('direct|' + voice + '|' + model + '|' + (style or '') + '|' + text + '|' + salt).encode()).hexdigest()[:16]

def _pcm_to_wav(pcm, sr=24000):
    b = io.BytesIO()
    with wave.open(b, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)
    return b.getvalue()

def _ledger(entry):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def _system_supported(model):
    # Measured 2026-09-28: the TTS models reject systemInstruction ("Developer instruction is not enabled for this model").
    # Set DHAMMALAB_TTS_SYSTEM=1 to try it again if Google enables it.
    return os.environ.get('DHAMMALAB_TTS_SYSTEM') == '1' or '-tts' not in model

def synth(text, voice, model, cache, style=None, salt='', timeout=300, max_attempts=6, use_system=None, prompt_style=None):
    """Return path of a WAV (24 kHz mono PCM16) for exactly `text`. Cached; retries 429/5xx with backoff.
    style        = delivery notes for systemInstruction (used when the model accepts it)
    prompt_style = the same notes as a fixed prompt header ending in '## TRANSCRIPT ...' (used when it does not);
                   the narration text itself is always sent unmodified after the header."""
    # Voice Policy guard (also enforced in build_audio.enforce_voice_policy): one narrator, Umbriel, no character colour
    if os.environ.get('DHAMMALAB_VOICE_POLICY_OVERRIDE') != '1':
        notes = (prompt_style or '') + (style or '')
        if voice != 'Umbriel' or 'for the characters' in notes:
            raise RuntimeError('Voice Policy: only Umbriel with STYLE_CHANNEL is allowed in production (STYLE_STORY is deprecated)')
    os.makedirs(cache, exist_ok=True)
    if use_system is None:
        use_system = _system_supported(model)
    if not use_system and prompt_style:
        style = prompt_style
    key = cache_key(text, voice, model, style, salt)
    wav_fn = os.path.join(cache, key + '.wav'); meta_fn = os.path.join(cache, key + '.json')
    if os.path.exists(wav_fn) and os.path.exists(meta_fn):
        return wav_fn
    body = {'contents': [{'role': 'user', 'parts': [{'text': text}]}],
            'generationConfig': {'responseModalities': ['AUDIO'], 'seed': seed_for(salt),
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}}}
    if style and use_system:
        body['systemInstruction'] = {'parts': [{'text': style}]}
    elif style:
        body['contents'][0]['parts'][0]['text'] = style + text
    url = API.format(model=model)
    last = None
    for attempt in range(max_attempts):
        t0 = time.time()
        try:
            r = requests.post(url, headers=_headers(), json=body, timeout=timeout)
        except requests.RequestException as e:
            last = f'network {type(e).__name__}'; time.sleep(min(60, 5 * 2 ** attempt)); continue
        if r.status_code == 200:
            j = r.json()
            parts = (j.get('candidates') or [{}])[0].get('content', {}).get('parts', [])
            aud = [p['inlineData'] for p in parts if 'inlineData' in p]
            if not aud:
                last = f'no audio (finishReason={(j.get("candidates") or [{}])[0].get("finishReason")})'
                time.sleep(3); continue
            mime = aud[0].get('mimeType', '')
            sr = 24000
            if 'rate=' in mime:
                try: sr = int(mime.split('rate=')[1].split(';')[0])
                except ValueError: pass
            pcm = b''.join(base64.b64decode(a['data']) for a in aud)
            open(wav_fn, 'wb').write(_pcm_to_wav(pcm, sr))
            meta = {'engine': 'gemini-api-direct', 'model': model, 'voice': voice, 'salt': salt, 'seed': seed_for(salt),
                    'style_sha1': hashlib.sha1((style or '').encode()).hexdigest()[:12], 'style_in': 'systemInstruction' if (style and use_system) else ('prompt' if style else 'none'),
                    'text_sha1': hashlib.sha1(text.encode()).hexdigest()[:12], 'chars': len(text), 'mime': mime,
                    'seconds': round(len(pcm) / 2 / sr, 2), 'latency_s': round(time.time() - t0, 1),
                    'usage': j.get('usageMetadata'), 'created_utc': datetime.datetime.utcnow().isoformat() + 'Z'}
            json.dump(meta, open(meta_fn, 'w'), ensure_ascii=False, indent=1)
            _ledger({'t': meta['created_utc'], 'model': model, 'voice': voice, 'chars': len(text), 'ok': True, 'usage': meta['usage'],
                     'category': 'tts', 'exp': os.environ.get('DHAMMALAB_EXP', 'unassigned')})
            return wav_fn
        # errors: never include the key; only status + API message
        try:
            err = r.json().get('error', {})
        except ValueError:
            err = {'message': r.text[:200]}
        last = f'{r.status_code} {err.get("status", "")} {err.get("message", "")[:200]}'
        _ledger({'t': datetime.datetime.utcnow().isoformat() + 'Z', 'model': model, 'ok': False, 'status': r.status_code, 'err': err.get('status')})
        if r.status_code == 400 and use_system and style and any(w in err.get('message', '').lower() for w in ('system', 'developer instruction')):
            return synth(text, voice, model, cache, style, salt, timeout, max_attempts, use_system=False, prompt_style=prompt_style)
        if r.status_code == 429:
            msg = err.get('message', '')
            if 'per day' in msg.lower() or 'daily' in msg.lower():
                raise QuotaExhausted('Gemini TTS daily quota exhausted: ' + msg[:200])
            delay = 30
            for d in err.get('details', []) or []:
                if d.get('@type', '').endswith('RetryInfo'):
                    try: delay = float(d.get('retryDelay', '30s').rstrip('s')) + 2
                    except ValueError: pass
            time.sleep(min(120, delay + random.random() * 3)); continue
        if r.status_code >= 500:
            time.sleep(min(60, 5 * 2 ** attempt)); continue
        break
    raise RuntimeError('Gemini TTS failed: ' + str(last))

TRANSCRIBE_PROMPT = ("Transcribe this Thai speech verbatim in Thai script. Output only the words actually spoken, exactly as heard, "
                     "without corrections, punctuation changes or commentary. If a word is unclear write [?].")

def transcribe(audio_bytes, mime='audio/mpeg', model='gemini-3.8-flash', timeout=300, max_attempts=4):
    """Voice QA transcription directly via the Gemini API (inline audio). Returns text or None."""
    body = {'contents': [{'role': 'user', 'parts': [{'inlineData': {'mimeType': mime, 'data': base64.b64encode(audio_bytes).decode()}},
                                                    {'text': TRANSCRIBE_PROMPT}]}],
            'generationConfig': {'temperature': 0}}
    url = API.format(model=model)
    for attempt in range(max_attempts):
        try:
            r = requests.post(url, headers=_headers(), json=body, timeout=timeout)
        except requests.RequestException:
            time.sleep(5 * 2 ** attempt); continue
        if r.status_code == 200:
            j = r.json(); c = (j.get('candidates') or [{}])[0]
            _ledger({'t': datetime.datetime.utcnow().isoformat() + 'Z', 'model': model, 'ok': True, 'usage': j.get('usageMetadata'),
                     'category': 'transcription_qa', 'exp': os.environ.get('DHAMMALAB_EXP', 'unassigned')})
            if c.get('finishReason') not in (None, 'STOP'): return None
            return ''.join(p.get('text', '') for p in c.get('content', {}).get('parts', []) if not p.get('thought')) or None
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(90, 10 * 2 ** attempt)); continue
        return None
    return None
