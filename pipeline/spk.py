"""ECAPA speaker embeddings (speechbrain spkrec-ecapa-voxceleb)"""
import numpy as np, torch, torchaudio, soundfile as sf
from speechbrain.inference.speaker import EncoderClassifier
_m = None
def model():
    global _m
    if _m is None:
        _m = EncoderClassifier.from_hparams(source='speechbrain/spkrec-ecapa-voxceleb', savedir='/home/claude/lab/models/ecapa', run_opts={'device': 'cpu'})
    return _m
def emb(x, sr):
    x = np.asarray(x, np.float32)
    if x.ndim > 1: x = x.mean(1)
    t = torch.from_numpy(x)[None]
    if sr != 16000: t = torchaudio.functional.resample(t, sr, 16000)
    with torch.no_grad():
        e = model().encode_batch(t)[0, 0].numpy()
    return e / np.linalg.norm(e)
def load(fn):
    x, sr = sf.read(fn, dtype='float32')
    return (x.mean(1) if x.ndim > 1 else x), sr
