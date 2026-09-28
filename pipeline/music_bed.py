"""Build a licensed-music bed and mix it under narration (no pumping: static levels + slow envelope).
Audio Mixing Policy (28 Sep 2026): narration is the reference; bed ~20 dB under the narration (stereo LUFS),
extra ducking in reflection passages, bed EQ'd out of the speech band and the low end, slightly up only where nobody speaks.
Usage: python3 music_bed.py outdir track1.mp3 track2.mp3 ... [--talk -34] [--outro -28] [--xf 6]
Reads outdir/voice.wav + meta.json; writes outdir/mix.wav (48 kHz stereo) and outdir/music_used.json
"""
import sys, os, json, argparse, subprocess
import numpy as np, soundfile as sf, pyloudnorm as pyln

SR = 48000

def decode(fn, ch=2):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', fn, '-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).copy()

def trim_quiet(x, rel_db=-28):
    """cut leading/trailing parts quieter than (track RMS + rel_db) measured in 0.5 s windows"""
    w = SR // 2
    n = len(x) // w
    rms = np.sqrt((x[:n * w] ** 2).reshape(n, -1).mean(1)) + 1e-9
    db = 20 * np.log10(rms)
    thr = np.median(db) + rel_db
    idx = np.where(db > thr)[0]
    return x[idx[0] * w:(idx[-1] + 1) * w]

ap = argparse.ArgumentParser()
ap.add_argument('outdir'); ap.add_argument('tracks', nargs='+')
ap.add_argument('--talk', type=float, default=-34.0, help='bed LUFS under narration')
ap.add_argument('--outro', type=float, default=-28.0, help='bed LUFS after narration ends')
ap.add_argument('--voice', type=float, default=-17.0)
ap.add_argument('--xf', type=float, default=6.0)
ap.add_argument('--end_fade', type=float, default=25.0)
ap.add_argument('--gap', type=float, default=20.0, help='bed this many dB under the narration (stereo LUFS) while it speaks')
ap.add_argument('--intro', type=float, default=-32.0, help='bed LUFS before the first word')
ap.add_argument('--duck', default='', help='extra ducking ranges "a-b,c-d" in seconds (reflection passages)')
ap.add_argument('--duck_db', type=float, default=3.0)
ap.add_argument('--total', type=float, default=0, help='cut the bed to this length (s)')
ap.add_argument('--eq', type=int, default=1, help='carve the speech band / low end out of the bed')
a = ap.parse_args()
import freeze; freeze.check()
meter = pyln.Meter(SR)

# voice: gentle chain via ffmpeg, then exact loudness in numpy
d = a.outdir
subprocess.run(f"ffmpeg -y -v error -i {d}/voice.wav -af aresample={SR}:resampler=soxr,highpass=f=70,deesser=i=0.35:m=0.5:f=0.5:s=o,"
               f"acompressor=threshold=-28dB:ratio=2.5:attack=15:release=250 -ac 1 -c:a pcm_f32le {d}/voice48.wav",
               shell=True, check=True)
v, _ = sf.read(f'{d}/voice48.wav', dtype='float32')
v *= 10 ** ((a.voice - meter.integrated_loudness(v)) / 20)
# peak-limit the narration alone (music is never compressed, so the bed cannot pump)
sf.write(f'{d}/voice48g.wav', v, SR, subtype='FLOAT')
subprocess.run(f"ffmpeg -y -v error -i {d}/voice48g.wav -af alimiter=limit=0.79:attack=4:release=60:level=disabled:asc=1 "
               f"-c:a pcm_f32le {d}/voice48l.wav", shell=True, check=True)
v, _ = sf.read(f'{d}/voice48l.wav', dtype='float32')
voice_end = json.load(open(f'{d}/meta.json'))['duration']

# music: loudness-match every track to 0 dB reference (-23 LUFS), trim silent tails, equal-power crossfades
bed = None; used = []; xf = int(a.xf * SR)
def carve(x):
    if not a.eq: return x
    import subprocess as sp
    raw = sp.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af',
                  'highpass=f=70,lowshelf=f=160:g=-4,equalizer=f=1800:t=q:w=1.2:g=-4,equalizer=f=3500:t=q:w=1.5:g=-2',
                  '-f', 'f32le', '-'], input=x.astype(np.float32).tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
for fn in a.tracks:
    x = carve(trim_quiet(decode(fn)))
    x *= 10 ** ((-23 - meter.integrated_loudness(x)) / 20)
    start = 0.0 if bed is None else (len(bed) - xf) / SR
    used.append({'file': os.path.basename(fn), 'start_s': round(start, 1), 'dur_s': round(len(x) / SR, 1)})
    if bed is None:
        bed = x
    else:
        t = np.linspace(0, np.pi / 2, xf)[:, None]
        mid = bed[-xf:] * np.cos(t) + x[:xf] * np.sin(t)
        bed = np.concatenate([bed[:-xf], mid, x[xf:]])
if a.total:
    assert len(bed) >= int(a.total * SR), f'bed too short: {len(bed)/SR:.1f}s < {a.total}s'
    bed = bed[:int(a.total * SR)]
total = len(bed) / SR
print('bed length', round(total, 1), 's; voice ends', round(voice_end, 1))

# gain envelope (dB relative to -23 LUFS reference): talk level, slow 40 s rise after voice ends, fade at the very end
tc = np.arange(0, total, 0.01)  # envelope at 100 Hz, applied blockwise
g_talk, g_out = a.talk + 23, a.outro + 23
g_talk = (a.voice + 3.0 - a.gap) + 23          # mono narration at a.voice LUFS plays at a.voice+3 in stereo
g_intro = a.intro + 23
first_word = json.load(open(f'{d}/meta.json'))['chunks'][0][0]
env_db = np.where(tc < voice_end + 4, g_talk, g_talk + (g_out - g_talk) * np.clip((tc - voice_end - 4) / 40, 0, 1))
env_db = np.where(tc < first_word, g_talk + (g_intro - g_talk) * np.clip((first_word - 0.5 - tc) / 2.5, 0, 1), env_db)
for rng in [r for r in a.duck.split(',') if r]:
    t0, t1 = [float(v) for v in rng.split('-')]
    w = np.clip(np.minimum(tc - (t0 - 2.5), (t1 + 2.5) - tc) / 2.5, 0, 1)
    env_db = env_db - a.duck_db * w
print('bed levels (stereo LUFS): intro %.1f, under narration %.1f (duck -%.1f), outro %.1f' % (g_intro - 23, g_talk - 23, a.duck_db, g_out - 23))
envc = 10 ** (env_db / 20) * np.sin(np.clip(tc / 4.0, 0, 1) * np.pi / 2) * np.sin(np.clip((total - tc) / a.end_fade, 0, 1) * np.pi / 2)
B = SR * 10
for i in range(0, len(bed), B):
    tb = (np.arange(i, min(i + B, len(bed))) / SR)
    bed[i:i + B] *= np.interp(tb, tc, envc).astype(np.float32)[:, None]

mix = bed
n = min(len(v), len(mix))
mix[:n] += v[:n, None] * 0.98
pk = np.abs(mix).max()
print('peak dBFS', round(20 * np.log10(pk), 2))
if pk > 0.89:  # keep true-peak headroom without a limiter (no pumping)
    mix *= 0.89 / pk
sf.write(f'{d}/mix.wav', mix, SR, subtype='PCM_24')
del bed, mix
print(subprocess.run(f"ffmpeg -hide_banner -nostats -i {d}/mix.wav -af ebur128=peak=true -f null - 2>&1 | grep -E 'I:|Peak:' | tail -2", shell=True, capture_output=True, text=True).stdout)
json.dump({'tracks': used, 'bed_total_s': round(total, 1), 'talk_lufs': round(g_talk - 23, 1), 'gap_db': a.gap, 'duck': a.duck,
           'intro_lufs': a.intro, 'outro_lufs': a.outro, 'eq': bool(a.eq)},
          open(f'{d}/music_used.json', 'w'), indent=1)
