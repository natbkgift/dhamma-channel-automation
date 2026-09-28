#!/usr/bin/env python3
"""DhammaLab SYSTEM-SMOKE (raw API part, stdlib only).

Run ONLY in a Claude Code session whose cloud environment is "Default" (it holds the
"DhammaLab Gemini" API credential for generativelanguage.googleapis.com). The agent proxy
adds the key header after the request leaves the VM, so this script never sends, reads or
prints a key. Cowork sessions do not get that credential and will fail S2-S5 with 403.

Checks (see SYSTEM_SMOKE.md):
  S1 key isolation: no key env var, no local key file
  S2 ListModels                          -> HTTP 200
  S3 generateContent gemini-3.8-flash    -> HTTP 200
  S4 TTS gemini-3.8-flash-tts / Umbriel  -> HTTP 200 + valid audio of plausible length
  S5 transcript QA of the S4 audio       -> similarity >= 0.90
Exit code 0 only when every check passes.

Usage: python3 smoke/system_smoke.py [--skip-tts]
"""
import base64, datetime, difflib, io, json, os, re, sys, time, urllib.error, urllib.request, wave

BASE = 'https://generativelanguage.googleapis.com/v1beta'
TEXT_MODEL = os.environ.get('DHAMMALAB_SMOKE_TEXT_MODEL', 'gemini-3.8-flash')
TTS_MODEL = os.environ.get('DHAMMALAB_SMOKE_TTS_MODEL', 'gemini-3.8-flash-tts')
VOICE = 'Umbriel'  # Voice Policy 28 Sep 2026: one Primary Dhamma Voice
SENTENCE = 'ขอให้ทุกท่านมีจิตใจที่สงบ และพักผ่อนอย่างมีความสุขครับ'
SIM_MIN = 0.90

results = []


def record(check, ok, detail):
    results.append({'check': check, 'ok': bool(ok), 'detail': detail})


def call(method, path, body=None, timeout=180):
    """HTTP call without any auth header; returns (status, parsed_json_or_None, error_text)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or '{}'), ''
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors='replace')
        try:
            msg = json.loads(raw).get('error', {}).get('message', raw)
        except Exception:
            msg = raw
        return e.code, None, msg[:150]
    except Exception as e:  # network / proxy errors
        return 0, None, f'{type(e).__name__}: {str(e)[:120]}'


def norm(s):
    return re.sub(r'[\s\.\,…ๆ\"\'!?\-–—]+', '', s or '')


def pcm_to_wav(pcm, rate=24000):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    return buf.getvalue()


def main():
    skip_tts = '--skip-tts' in sys.argv
    started = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    # S1 key isolation (names / existence only, never values)
    env_hits = [n for n in ('DHAMMALAB_GEMINI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY') if os.environ.get(n)]
    keyfile = os.path.exists(os.path.expanduser('~/.config/dhammalab/gemini.env'))
    record('S1 key isolation', not env_hits and not keyfile,
           f'env key vars set: {len(env_hits)}; local key file: {"present" if keyfile else "absent"}')

    # S2 ListModels
    st, js, err = call('GET', '/models?pageSize=1')
    record('S2 ListModels', st == 200, f'HTTP {st}' + (f' - {err}' if err else ''))

    # S3 generateContent ping
    st, js, err = call('POST', f'/models/{TEXT_MODEL}:generateContent',
                       {'contents': [{'parts': [{'text': 'ping'}]}], 'generationConfig': {'maxOutputTokens': 5}})
    record(f'S3 generateContent {TEXT_MODEL}', st == 200, f'HTTP {st}' + (f' - {err}' if err else ''))

    if skip_tts:
        record('S4 TTS', False, 'skipped (--skip-tts)')
        record('S5 transcript QA', False, 'skipped (--skip-tts)')
    else:
        # S4 TTS, same voice for everything
        body = {'contents': [{'parts': [{'text': SENTENCE}]}],
                'generationConfig': {'responseModalities': ['AUDIO'],
                                     'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICE}}}}}
        t0 = time.time()
        st, js, err = call('POST', f'/models/{TTS_MODEL}:generateContent', body, timeout=300)
        wav_bytes, secs, mime = None, 0.0, ''
        if st == 200:
            try:
                part = next(p for p in js['candidates'][0]['content']['parts'] if 'inlineData' in p)
                mime = part['inlineData'].get('mimeType', '')
                audio = base64.b64decode(part['inlineData']['data'])
                if mime.startswith('audio/wav') or audio[:4] == b'RIFF':
                    wav_bytes = audio
                else:  # raw L16 PCM, e.g. audio/L16;codec=pcm;rate=24000
                    m = re.search(r'rate=(\d+)', mime)
                    wav_bytes = pcm_to_wav(audio, int(m.group(1)) if m else 24000)
                with wave.open(io.BytesIO(wav_bytes)) as w:
                    secs = w.getnframes() / float(w.getframerate())
            except Exception as e:
                err = f'bad audio payload: {type(e).__name__}'
        ok4 = st == 200 and wav_bytes is not None and 1.5 <= secs <= 20
        record(f'S4 TTS {TTS_MODEL} / {VOICE}', ok4,
               f'HTTP {st}, {mime or "-"}, {secs:.1f}s audio, {time.time()-t0:.1f}s wall' + (f' - {err}' if err else ''))

        # S5 transcript QA of that take
        if ok4:
            qa = {'contents': [{'parts': [
                {'inlineData': {'mimeType': 'audio/wav', 'data': base64.b64encode(wav_bytes).decode()}},
                {'text': 'Transcribe this Thai speech exactly, word for word. Output only the Thai transcript.'}]}],
                'generationConfig': {'temperature': 0}}
            st, js, err = call('POST', f'/models/{TEXT_MODEL}:generateContent', qa)
            hyp = ''
            if st == 200:
                try:
                    hyp = ''.join(p.get('text', '') for p in js['candidates'][0]['content']['parts'])
                except Exception:
                    err = 'no transcript in response'
            sim = difflib.SequenceMatcher(None, norm(SENTENCE), norm(hyp)).ratio() if hyp else 0.0
            record('S5 transcript QA', st == 200 and sim >= SIM_MIN,
                   f'HTTP {st}, similarity {sim:.2f} (min {SIM_MIN})' + (f' - {err}' if err else ''))
        else:
            record('S5 transcript QA', False, 'not run (S4 failed)')

    passed = all(r['ok'] for r in results)
    print(f'DhammaLab SYSTEM-SMOKE (raw API) - {started}')
    for r in results:
        print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']}: {r['detail']}")
    print('VERDICT:', 'PASS' if passed else 'FAIL')
    out = os.environ.get('DHAMMALAB_SMOKE_JSON')
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump({'utc': started, 'passed': passed, 'results': results}, f, ensure_ascii=False, indent=1)
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
