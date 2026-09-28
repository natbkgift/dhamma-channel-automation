"""Speaker-consistency QC: one narrator per video.
Embeds each narration chunk (resemblyzer d-vector) + median F0, compares with the channel reference voice
(Primary Dhamma Voice sample) and with the video's own centroid.
usage: python3 speaker_qc.py voice.wav meta.json ref.wav [out.json]"""
import sys, json, numpy as np, soundfile as sf, librosa
from resemblyzer import VoiceEncoder, preprocess_wav
enc = VoiceEncoder('cpu', verbose=False)
def emb(x, sr):
    return enc.embed_utterance(preprocess_wav(x, source_sr=sr))
def f0(x, sr):
    y = librosa.resample(x, orig_sr=sr, target_sr=16000)
    f, v, _ = librosa.pyin(y, fmin=50, fmax=300, sr=16000, frame_length=1024)
    f = f[v & ~np.isnan(f)]
    return float(np.median(f)) if len(f) else 0.0
if __name__ == '__main__':
    x, sr = sf.read(sys.argv[1], dtype='float32')
    if x.ndim > 1: x = x.mean(1)
    m = json.load(open(sys.argv[2])); st = [c[0] for c in m['chunks']] + [m['duration']]
    r, rsr = sf.read(sys.argv[3], dtype='float32')
    if r.ndim > 1: r = r.mean(1)
    ref = emb(r, rsr); ref_f0 = f0(r, rsr)
    rows = []
    for i in range(len(st) - 1):
        seg = x[int(st[i] * sr):int(st[i + 1] * sr)]
        rows.append({'chunk': i + 1, 't': round(st[i], 1), 'e': emb(seg, sr), 'f0': f0(seg, sr)})
    E = np.array([r_['e'] for r_ in rows]); cen = E.mean(0); cen /= np.linalg.norm(cen)
    out = []
    for r_ in rows:
        out.append({'chunk': r_['chunk'], 't': r_['t'], 'sim_ref': round(float(r_['e'] @ ref), 3),
                    'sim_centroid': round(float(r_['e'] @ cen), 3), 'f0': round(r_['f0'], 1)})
    f0s = np.array([o['f0'] for o in out])
    summary = {'ref_f0': round(ref_f0, 1), 'f0_median': round(float(np.median(f0s)), 1),
               'f0_range': [round(float(f0s.min()), 1), round(float(f0s.max()), 1)],
               'sim_ref_min': min(o['sim_ref'] for o in out), 'sim_ref_mean': round(float(np.mean([o['sim_ref'] for o in out])), 3),
               'sim_centroid_min': min(o['sim_centroid'] for o in out)}
    print(json.dumps(summary))
    for o in out: print(o)
    if len(sys.argv) > 4: json.dump({'summary': summary, 'chunks': out}, open(sys.argv[4], 'w'), indent=1)
