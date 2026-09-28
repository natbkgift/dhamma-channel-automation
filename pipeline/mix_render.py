"""Mix narration with a generative ambient bed and render a static-image video.
Usage: python3 mix_render.py outdir background.png --outro 180 --target small|hq
"""
import sys, os, json, argparse, subprocess

def sh(cmd):
    print('+', cmd[:160], flush=True); subprocess.run(cmd, shell=True, check=True)

ap = argparse.ArgumentParser()
ap.add_argument('outdir'); ap.add_argument('bg')
ap.add_argument('--outro', type=float, default=180); ap.add_argument('--target', default='small')
ap.add_argument('--bedvol', type=float, default=0.14); ap.add_argument('--seed', type=int, default=5)
a = ap.parse_args()
d = a.outdir
meta = json.load(open(f'{d}/meta.json'))
total = meta['duration'] + a.outro
sh(f'python3 /home/claude/lab/bed.py {total:.1f} {d}/bed.wav {a.seed}')
# voice chain: gentle HPF, light compression, de-ess-ish lowpass; bed fades out over the last 20 s
fade_st = max(0, total - 20)
sh(f"ffmpeg -y -loglevel error -i {d}/voice.wav -i {d}/bed.wav -filter_complex "
   f"\"[0:a]aresample=48000,highpass=f=70,lowpass=f=11000,acompressor=threshold=-22dB:ratio=2.5:attack=15:release=250,apad=whole_dur={total:.1f}[v];"
   f"[1:a]aresample=48000,volume={a.bedvol},afade=t=out:st={fade_st:.1f}:d=20[b];"
   f"[v][b]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[o]\" -map \"[o]\" -ac 1 -c:a pcm_s16le {d}/mix.wav")
if a.target == 'small':
    # fits browser upload (<10 MB) for ~40 min: VP9 still image @1 fps + Opus 28 kbps mono
    sh(f"ffmpeg -y -loglevel error -loop 1 -framerate 1 -i {a.bg} -i {d}/mix.wav -c:v libvpx-vp9 -b:v 0 -crf 40 -row-mt 1 -deadline good -cpu-used 5 "
       f"-g 600 -pix_fmt yuv420p -vf scale=1280:720 -c:a libopus -b:a 32k -ac 1 -shortest {d}/final.webm")
    out = f'{d}/final.webm'
else:
    sh(f"ffmpeg -y -loglevel error -loop 1 -framerate 2 -i {a.bg} -i {d}/mix.wav -c:v libx264 -tune stillimage -preset medium -crf 20 "
       f"-g 120 -pix_fmt yuv420p -vf scale=1920:1080 -c:a aac -b:a 160k -ar 48000 -shortest -movflags +faststart {d}/final.mp4")
    out = f'{d}/final.mp4'
sz = os.path.getsize(out) / 1e6
dur = float(subprocess.check_output(f'ffprobe -v error -show_entries format=duration -of csv=p=0 {out}', shell=True))
print(json.dumps({'out': out, 'MB': round(sz, 2), 'duration': round(dur, 1)}))
