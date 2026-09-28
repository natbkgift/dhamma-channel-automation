# DhammaLab Dependency Map (29 Sep 2026)

Normal production: **Make Operations = 0**. Make is reachable only through `legacy/` scripts with an open
`make_guard` rollback session (reason + numeric op cap + expiry) and `DHAMMALAB_MAKE_ROLLBACK=1`.

| Task | Provider | API / Project | Model / Service | Estimated cost (THB) | Make ops |
|---|---|---|---|---|---|
| Narration TTS | Google Gemini API (direct) | generativelanguage v1beta generateContent · project DhammaLab* | gemini-3.8-flash-tts, voice Umbriel | ~฿0.3 per take; ~฿90–180 per 25–30 min video (330–340 takes, 50% billing savings seen in Sep) | 0 |
| Transcript QA | Google Gemini API (direct) | generateContent (inline audio) | gemini-3.8-flash + gemini-3.5-transcribe | ~฿0.1 per chunk check; ~฿25 per video | 0 |
| Voice consistency / click / flash QC | local | — | ECAPA (speechbrain), pyin, qc_scan.py, ffmpeg | ฿0 | 0 |
| Hero / scene images | Google Gemini API (direct) | generateContent, imageConfig | gemini-3-pro-image (Nano Banana Pro) | ~฿5 at 1K, ~฿8 at 4K per image | 0 |
| Motion clips (image→video) | Google Gemini API (direct) | Interactions API `POST /v1beta/interactions` (background) + GET | gemini-omni-1.1-flash | ~฿11 per 10 s at 360p; 1080p higher (Sep: ฿1,034 total, the largest cost) | 0 |
| Music bed (current) | YouTube Audio Library | — | licensed tracks, logged in music_used.json | ฿0 | 0 |
| Music generation (EXP-M) | Google Gemini API (direct) | Interactions API | lyria-3.5 / lyria-3-clip-preview / lyria-realtime-exp (available on the key) | $0.04–0.08 per song (~฿1.3–2.6) | 0 |
| Thumbnails / channel art | local | Playwright HTML render | Pridi + Anuphan, official logo | ฿0 | 0 |
| Mix / render / mux | local | — | ffmpeg, visual_bus.py, music_bed.py | ฿0 | 0 |
| Upload / schedule / metadata | YouTube Studio via Claude in Chrome | — | — | ฿0 | 0 |
| Reporting | Discord (browser), Claude Docs, Project Thamma | — | — | ฿0 | 0 |
| Rollback only | Make.com scenario 4942061 | webhook | legacy/gen_image, gen_video, fetch_videos, retake, qc_voice_gemini, build_audio engine=make | Make ops 3–5 per call | capped per rollback session |

*Until the DhammaLab key is added as a cloud-environment API credential, calls use the temporary key of
"Gemini Project" (gen-lang-client-0632919985, not shared with TWF/FlowBiz). Check with `python3 secret_check.py`.

Cost ledger: `~/.config/dhammalab/tts_ledger.jsonl` (every direct call: model, tokens, category, `DHAMMALAB_EXP`).
Report: `python3 costs.py [--exp EXP-xx]`. Prices calibrated from the Cloud Billing SKU report; re-calibrate monthly.
