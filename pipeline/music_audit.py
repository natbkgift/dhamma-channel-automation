"""Audit background-music candidates for narration beds: dynamics, transients, bass, speech-band masking.
usage: python3 music_audit.py track.mp3 [...]"""
import sys, subprocess, json, numpy as np, librosa
def decode(fn, sr=22050):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', fn, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32), sr
rows = []
for fn in sys.argv[1:]:
    y, sr = decode(fn)
    y = y[int(3 * sr):len(y) - int(3 * sr)]      # ignore fade in/out
    hop = 512
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop)) ** 2
    fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
    tot = S.sum(0) + 1e-12
    bass = float((S[fr < 150].sum(0) / tot).mean()); speech = float((S[(fr >= 300) & (fr <= 3400)].sum(0) / tot).mean())
    H, P = librosa.decompose.hpss(S)
    perc = float(P.sum() / (H.sum() + P.sum()))
    # short-term level (1 s) and its fastest rise within 2 s
    w = sr; n = len(y) // w
    db = 20 * np.log10(np.sqrt((y[:n * w].reshape(n, w) ** 2).mean(1)) + 1e-9)
    rise = float(max(db[i + 2] - db[i] for i in range(n - 2))) if n > 3 else 0
    on = librosa.onset.onset_strength(S=librosa.power_to_db(S), sr=sr)
    spikes = int((on > np.median(on) + 6 * on.std()).sum())
    rows.append({'track': fn.split('/')[-1], 'bass': round(bass, 3), 'speech_band': round(speech, 3), 'percussive': round(perc, 3),
                 'max_rise_2s_db': round(rise, 1), 'level_range_db': round(float(np.percentile(db, 95) - np.percentile(db, 5)), 1), 'onset_spikes': spikes})
    print(json.dumps(rows[-1]), flush=True)
