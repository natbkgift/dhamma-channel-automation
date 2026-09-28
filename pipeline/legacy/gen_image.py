"""LEGACY / ROLLBACK ONLY - spends Make operations. Never called by normal production.
Requires an open make_guard rollback session and DHAMMALAB_MAKE_ROLLBACK=1."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
"""Nano Banana Pro (gemini-3-pro-image) via the DhammaLab Make webhook -> image file.
usage: gen_image.py out.png "prompt" [--size 4K] [--aspect 16:9] [--model gemini-3-pro-image]"""
import sys, base64, argparse, requests, time
ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('prompt')
ap.add_argument('--size', default='4K'); ap.add_argument('--aspect', default='16:9'); ap.add_argument('--model', default='gemini-3-pro-image'); ap.add_argument('--ref')
a = ap.parse_args()
from make_guard import make_endpoint
hook, key = make_endpoint('image')
t = time.time()
payload = {'key': key, 'mode': 'image', 'model': a.model, 'text': a.prompt, 'size': a.size, 'aspect': a.aspect}
if a.ref:
    from PIL import Image; import io
    im = Image.open(a.ref).convert('RGB'); im.thumbnail((1600, 1600)); buf = io.BytesIO(); im.save(buf, 'JPEG', quality=88)
    payload.update(mode='image_ref', image_b64=base64.b64encode(buf.getvalue()).decode())
r = requests.post(hook, json=payload, timeout=300)
b = r.content
print('status', r.status_code, r.headers.get('content-type'), len(b), 'bytes', round(time.time() - t), 's')
if b[:4] != b"\x89PNG" and b[:3] != b"\xff\xd8\xff":
    try:
        b = base64.b64decode(b, validate=True)
    except Exception:
        print('not an image:', r.text[:300]); sys.exit(1)
open(a.out, 'wb').write(b); print('saved', a.out)
