# legacy/ — Make.com rollback scripts (not part of normal production)
Normal DhammaLab production = 0 Make operations. Direct replacements:
- gen_image.py  -> ../gemini_media.py image
- gen_video.py / fetch_videos.py -> ../gemini_media.py video_start / video_get
- retake.py, qc_voice_gemini.py -> ../voice_takes.py (+ gemini_tts.transcribe)
Use only after Nat approves a rollback:
  python3 ../make_guard.py open --reason "..." --max-ops N --approved-by Nat
  DHAMMALAB_MAKE_ROLLBACK=1 python3 legacy/<script>.py ...
  python3 ../make_guard.py close
