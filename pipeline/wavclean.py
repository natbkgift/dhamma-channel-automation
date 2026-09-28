"""Gemini TTS via Make returns a WAV whose data chunk is itself a complete WAV:
   outer RIFF > data = [inner RIFF header (44 B)] + [PCM] + [C2PA/JUMBF provenance manifest ~6 KB].
Reading the outer data as PCM turns the inner header into a click at the start and the C2PA box into a
~130 ms full-scale noise burst at the end. extract_pcm() returns only the inner PCM."""
import struct, numpy as np

def _chunks(b, start):
    i = start
    while i + 8 <= len(b):
        cid = b[i:i + 4]; sz = struct.unpack('<I', b[i + 4:i + 8])[0]
        yield cid, i + 8, sz
        i += 8 + sz + (sz & 1)

def parse(b):
    """-> (sr, channels, bits, pcm_bytes) of the innermost WAV"""
    assert b[:4] == b'RIFF' and b[8:12] == b'WAVE', 'not a WAV'
    fmt = None
    for cid, off, sz in _chunks(b, 12):
        if cid == b'fmt ':
            fmt = struct.unpack('<HHIIHH', b[off:off + 16])
        elif cid == b'data':
            payload = b[off:off + sz]
            if payload[:4] == b'RIFF' and payload[8:12] == b'WAVE':
                return parse(payload)          # nested WAV -> recurse
            return fmt[2], fmt[1], fmt[5], payload
    raise ValueError('no data chunk')

def extract_pcm(fn):
    b = open(fn, 'rb').read()
    sr, ch, bits, pcm = parse(b)
    assert bits == 16, bits
    pcm = pcm[:len(pcm) // (2 * ch) * 2 * ch]
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    # defence in depth: a C2PA/JUMBF box must never be inside the PCM we return
    assert pcm.find(b'jumb') < 0 or pcm.find(b'c2pa') < 0, f'provenance box inside PCM: {fn}'
    return x, sr

if __name__ == '__main__':
    import sys, glob
    bad = 0
    for f in sys.argv[1:]:
        x, sr = extract_pcm(f)
        head = np.abs(x[:int(0.005 * sr)]).max()
        if head > 0.2:
            bad += 1; print('HEAD CLICK', f, head)
    print('checked', len(sys.argv) - 1, 'files, head clicks:', bad)
