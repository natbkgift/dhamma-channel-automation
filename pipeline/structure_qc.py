"""Final-audio QC for the Audio Structure Policy (29 Sep 2026).
usage: python3 structure_qc.py mix_or_final first_word_s last_word_s [--json out.json]
Checks: no dead air in 0:00-0:10, loudness around narration end / music-only transition / +30 s / middle of
music-only / last 30 s, largest 1 s loudness step in the transition (abrupt jump), music-only level vs bed,
true peak (ffmpeg ebur128)."""
import sys, json, subprocess, numpy as np, pyloudnorm as pyln
fn, fw, lw = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
SR = 48000
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', fn, '-vn', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2); dur = len(x) / SR
M = pyln.Meter(SR, block_size=0.4)
def st(t0, t1):
    s = x[int(max(0, t0) * SR):int(min(dur, t1) * SR)]
    try: return round(float(M.integrated_loudness(s)), 1)
    except Exception: return None
def rms_db(t0, t1):
    s = x[int(t0 * SR):int(t1 * SR)]; return 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-12)
out = {'file': fn, 'duration_s': round(dur, 2), 'first_word_s': fw, 'last_word_s': lw}
# dead air: 0.25 s windows in the first 10 s (before the first word) that are near-silent
win = [rms_db(t, t + 0.25) for t in np.arange(0, min(fw, 10), 0.25)]
out['intro_first_audible_s'] = next((round(i * 0.25, 2) for i, d in enumerate(win) if d > -60), None)
out['intro_min_db_after_0.5s'] = round(min(win[2:]) if len(win) > 2 else 0, 1)
out['checkpoints_lufs'] = {'0:00-0:10': st(0, 10), '10s before narration end': st(lw - 10, lw),
                           'narration->music (end..+15s)': st(lw, lw + 15), '+30s after narration': st(lw + 25, lw + 35),
                           'middle music-only': st((lw + dur) / 2 - 5, (lw + dur) / 2 + 5), 'last 30s': st(dur - 30, dur)}
# abrupt jumps: 1 s short-term loudness (3 s window) steps across the transition
ts = np.arange(lw + 0.5, min(dur - 3, lw + 60), 1.0)   # music-only side only (the voice ending is not a jump)
L = [st(t, t + 3) for t in ts]; L = [v for v in L if v is not None]
out['transition_max_step_db_per_s'] = round(float(np.max(np.abs(np.diff(L)))), 2) if len(L) > 2 else None
out['music_only_lufs'] = st(lw + 30, dur - 30)
tp = subprocess.run(f"ffmpeg -hide_banner -nostats -i '{fn}' -af ebur128=peak=true -f null - 2>&1 | grep -E 'Peak:' | tail -1", shell=True, capture_output=True, text=True).stdout.split()
out['true_peak_dbtp'] = float(tp[1]) if len(tp) > 1 else None
E = []
if out['intro_first_audible_s'] is None or out['intro_first_audible_s'] > 0.5: E.append('dead air at start')
if out['intro_min_db_after_0.5s'] < -60: E.append('silence before narration')
if not (0.8 <= fw <= 1.5): E.append(f'narration starts at {fw}s (policy 0.8-1.5 s)')
if out['transition_max_step_db_per_s'] and out['transition_max_step_db_per_s'] > 5: E.append('abrupt level change in transition')   # the music's own phrasing moves ~2-4 dB/s
if out['music_only_lufs'] and not (-27.5 <= out['music_only_lufs'] <= -22.5): E.append(f"music-only level {out['music_only_lufs']} LUFS")
if out['true_peak_dbtp'] is not None and out['true_peak_dbtp'] > -1.5: E.append(f"true peak {out['true_peak_dbtp']} dBTP")
out['errors'] = E; out['pass'] = not E
print(json.dumps(out, ensure_ascii=False, indent=1))
if '--json' in sys.argv: json.dump(out, open(sys.argv[sys.argv.index('--json') + 1], 'w'), ensure_ascii=False, indent=1)
