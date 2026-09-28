"""Check which path supplies the Gemini key WITHOUT printing it.
python3 secret_check.py            -> reports the key source used by the worker and a live API check
python3 secret_check.py --migrate  -> if the persistent path (env secret or proxy credential) works on its own,
                                      delete the temporary ~/.config/dhammalab/gemini.env"""
import os, sys, requests
sys.path.insert(0, os.path.dirname(__file__))
os.environ['DHAMMALAB_NO_LOCAL_KEY'] = '1'           # test the persistent path only
import gemini_tts as G
src = G.key_source()
r = requests.get('https://generativelanguage.googleapis.com/v1beta/models?pageSize=1', headers=G._headers(), timeout=30)
ok = r.status_code == 200
print(f'persistent path: {src} -> HTTP {r.status_code} {"OK" if ok else "not configured yet"}')
fn = os.path.expanduser('~/.config/dhammalab/gemini.env')
if '--migrate' in sys.argv:
    if ok and os.path.exists(fn):
        os.remove(fn); print('temporary secret file removed')
    elif not ok:
        print('kept temporary secret file (persistent path not working yet)')
