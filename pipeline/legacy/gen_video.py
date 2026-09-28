"""LEGACY / ROLLBACK ONLY - spends Make operations. Never called by normal production.
Requires an open make_guard rollback session and DHAMMALAB_MAKE_ROLLBACK=1."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
"""Gemini Omni image-to-video via the DhammaLab Make webhook.
usage: gen_video.py start frame.jpg "prompt"  -> prints interaction id
       gen_video.py get <id> out_dir           -> polls, saves raw json + any video"""
import sys, json, base64, time, requests, io, os, re
from PIL import Image
from make_guard import make_endpoint
hook, key = make_endpoint('video')
if sys.argv[1] == 'start':
    im = Image.open(sys.argv[2]).convert('RGB'); im = im.resize((1920, 1080), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=90)
    r = requests.post(hook, json={'key': key, 'mode': 'video_start', 'text': sys.argv[3],
                                  'image_b64': base64.b64encode(buf.getvalue()).decode()}, timeout=300)
    print(r.status_code, r.text[:500])
else:
    iid, out = sys.argv[2], sys.argv[3]; os.makedirs(out, exist_ok=True)
    for k in range(60):
        r = requests.post(hook, json={'key': key, 'mode': 'video_get', 'id': iid}, timeout=300)
        st = r.headers.get('X-Status') or r.headers.get('x-status'); t = r.text
        open(f'{out}/interaction.json', 'w').write(t)
        print(k, 'http', r.status_code, 'status', st, 'bytes', len(t), flush=True)
        if st in ('completed', 'failed', 'cancelled') or r.status_code != 200: break
        time.sleep(20)
