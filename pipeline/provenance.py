"""Anti-copy provenance manifest: every source asset with SHA-256, size, mtime, and how it was made.
usage: python3 provenance.py exp_name outdir out.json"""
import sys, os, json, hashlib, glob, time, datetime
exp, outdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
def sha(fn):
    h = hashlib.sha256()
    with open(fn, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def entry(fn, kind, note=''):
    st = os.stat(fn)
    return {'file': os.path.relpath(fn, '/home/claude/lab'), 'kind': kind, 'sha256': sha(fn), 'bytes': st.st_size,
            'modified_utc': datetime.datetime.utcfromtimestamp(st.st_mtime).isoformat() + 'Z', 'note': note}
items = []
def add(pattern, kind, note=''):
    for fn in sorted(glob.glob(pattern)): items.append(entry(fn, kind, note))
cfg = json.load(open(os.path.join(outdir, 'provenance_sources.json')))
for pat, kind, note in cfg['sources']: add(pat, kind, note)
ov = json.load(open(os.path.join(outdir, 'overrides.json'))); L = json.load(open(os.path.join(outdir, 'voice_takes.json')))
for n in sorted(ov, key=int):
    r = L.get(f'{n}:{ov[n]}')
    if r: items.append(entry(r['file'], 'narration take', f'chunk {n} salt {ov[n]!r} f0 {r["f0"]} Hz, Gemini TTS Umbriel, channel prompt'))
man = {'experiment': exp, 'generated_utc': datetime.datetime.utcnow().isoformat() + 'Z', 'channel': 'ธรรมะดีดี (@thammadee)',
       'tools': cfg.get('tools', {}), 'assets': items}
json.dump(man, open(out, 'w'), ensure_ascii=False, indent=1)
print(len(items), 'assets ->', out)
