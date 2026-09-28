"""LEGACY / ROLLBACK ONLY - spends Make operations. Never called by normal production.
Requires an open make_guard rollback session and DHAMMALAB_MAKE_ROLLBACK=1."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
"""poll all started interactions listed in starts.txt ('NAME 200 {json}') and save NAME/raw.mp4"""
import sys, json, base64, time, os, requests
from make_guard import make_endpoint
hook, key = make_endpoint('video_get')
jobs = {}
for line in open(sys.argv[1]):
    name, code, js = line.split(' ', 2)
    try: jobs[name] = json.loads(js)['id']
    except Exception: print('skip', name, js[:100])
done = set()
for rnd in range(40):
    for name, iid in jobs.items():
        if name in done: continue
        r = requests.post(hook, json={'key': key, 'mode': 'video_get', 'id': iid}, timeout=300)
        st = r.headers.get('X-Status')
        if st == 'completed':
            os.makedirs(name, exist_ok=True)
            for s in json.loads(r.text):
                for c in s.get('content', []) or []:
                    if c.get('type') == 'video':
                        open(f'{name}/raw.mp4', 'wb').write(base64.b64decode(c['data']))
            done.add(name); print(name, 'saved', flush=True)
        elif st in ('failed', 'cancelled') or r.status_code != 200:
            done.add(name); print(name, 'FAILED', st, r.status_code, r.text[:200], flush=True)
    if len(done) == len(jobs): break
    time.sleep(30)
print('done', len(done), 'of', len(jobs))
