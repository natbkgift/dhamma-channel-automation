"""DhammaLab direct Gemini media worker (no Make): images (Nano Banana Pro etc.) and image-to-video (Gemini Omni).
Key handling is identical to gemini_tts (runtime only: env secret -> temporary file -> cloud API credential proxy).
Every successful call is written to the cost ledger with category + experiment (env DHAMMALAB_EXP).

CLI
  python3 gemini_media.py image out.jpg "prompt" [--model gemini-3-pro-image] [--aspect 16:9] [--size 4K] [--ref ref.jpg]
  python3 gemini_media.py video_start frame.jpg "prompt" [--res 1080p] [--aspect 16:9]    -> prints interaction id
  python3 gemini_media.py video_get <id> out_dir                                           -> polls, saves out_dir/raw.mp4
"""
import os, sys, io, json, time, base64, datetime, argparse, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_tts as G

BASE = 'https://generativelanguage.googleapis.com/v1beta'

def _log(model, usage, category, extra=None):
    G._ledger({'t': datetime.datetime.utcnow().isoformat() + 'Z', 'model': model, 'ok': True, 'usage': usage,
               'category': category, 'exp': os.environ.get('DHAMMALAB_EXP', 'unassigned'), **(extra or {})})

def _post(url, body, timeout=300, attempts=5):
    last = None
    for k in range(attempts):
        try:
            r = requests.post(url, headers=G._headers(), json=body, timeout=timeout)
        except requests.RequestException as e:
            last = f'network {type(e).__name__}'; time.sleep(5 * 2 ** k); continue
        if r.status_code == 200: return r.json()
        err = (r.json().get('error', {}) if r.headers.get('content-type', '').startswith('application/json') else {'message': r.text[:200]})
        last = f'{r.status_code} {err.get("status", "")} {err.get("message", "")[:200]}'
        if r.status_code == 429 and ('per day' in last.lower() or 'daily' in last.lower()):
            raise G.QuotaExhausted(last)
        if r.status_code in (429, 500, 502, 503, 504): time.sleep(min(90, 10 * 2 ** k)); continue
        break
    raise RuntimeError('Gemini media call failed: ' + str(last))

def _jpeg_b64(path, max_side=1920):
    from PIL import Image
    im = Image.open(path).convert('RGB'); im.thumbnail((max_side, max_side))
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=90); return base64.b64encode(buf.getvalue()).decode()

def image(out, prompt, model='gemini-3-pro-image', aspect='16:9', size='4K', ref=None):
    parts = [{'text': prompt}]
    if ref: parts.insert(0, {'inlineData': {'mimeType': 'image/jpeg', 'data': _jpeg_b64(ref, 1600)}})
    body = {'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': aspect, 'imageSize': size}}}
    j = _post(f'{BASE}/models/{model}:generateContent', body)
    for p in (j.get('candidates') or [{}])[0].get('content', {}).get('parts', []):
        if 'inlineData' in p:
            open(out, 'wb').write(base64.b64decode(p['inlineData']['data']))
            _log(model, j.get('usageMetadata'), 'image', {'size': size})
            return out
    raise RuntimeError('no image in response: finishReason=' + str((j.get('candidates') or [{}])[0].get('finishReason')))

def video_start(frame, prompt, model='gemini-omni-1.1-flash', res='1080p', aspect='16:9'):
    body = {'model': model, 'background': True, 'store': True,
            'input': [{'type': 'image', 'data': _jpeg_b64(frame), 'mime_type': 'image/jpeg'}, {'type': 'text', 'text': prompt}],
            'response_format': {'type': 'video', 'resolution': res, 'aspect_ratio': aspect}}
    j = _post(f'{BASE}/interactions', body)
    return j.get('id'), j.get('status')

def _find_video(j):
    if isinstance(j.get('output_video'), dict) and j['output_video'].get('data'): return j['output_video']
    for key in ('steps', 'outputs'):
        for s in j.get(key) or []:
            for c in (s.get('content') or [s]):
                if isinstance(c, dict) and c.get('type') == 'video': return c
    return None

def video_get(iid, out_dir, polls=90, wait=20):
    os.makedirs(out_dir, exist_ok=True)
    for k in range(polls):
        r = requests.get(f'{BASE}/interactions/{iid}', headers=G._headers(), timeout=120)
        j = r.json() if r.status_code == 200 else {}
        st = j.get('status')
        if st == 'completed':
            v = _find_video(j)
            if v and v.get('data'):
                open(f'{out_dir}/raw.mp4', 'wb').write(base64.b64decode(v['data']))
            elif v and v.get('uri'):
                d = requests.get(v['uri'], headers=G._headers(), timeout=300); open(f'{out_dir}/raw.mp4', 'wb').write(d.content)
            else:
                json.dump(j, open(f'{out_dir}/interaction.json', 'w')); raise RuntimeError('completed without video')
            _log(j.get('model', 'gemini-omni-1.1-flash'), j.get('usage') or j.get('usageMetadata'), 'video', {'interaction': iid})
            return f'{out_dir}/raw.mp4'
        if st in ('failed', 'cancelled') or r.status_code != 200:
            raise RuntimeError(f'video {iid}: http {r.status_code} status {st}')
        time.sleep(wait)
    raise TimeoutError(f'video {iid} not ready')

if __name__ == '__main__':
    import freeze; freeze.check()
    ap = argparse.ArgumentParser(); ap.add_argument('mode'); ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('c', nargs='?'); ap.add_argument('--model'); ap.add_argument('--aspect', default='16:9')
    ap.add_argument('--size', default='4K'); ap.add_argument('--ref'); ap.add_argument('--res', default='1080p')
    x = ap.parse_args()
    if x.mode == 'image':
        print(image(x.a, x.b, x.model or 'gemini-3-pro-image', x.aspect, x.size, x.ref))
    elif x.mode == 'video_start':
        print(json.dumps(dict(zip(('id', 'status'), video_start(x.a, x.b, x.model or 'gemini-omni-1.1-flash', x.res, x.aspect)))))
    elif x.mode == 'video_get':
        print(video_get(x.a, x.b))
