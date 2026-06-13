# 🚀 AI Space Shorts Agent

An autonomous agent that produces and publishes a unique space/science **YouTube Short every day** — no human in the loop.

It writes a script with an LLM, narrates it, burns in **word-synced captions**, renders a vertical 1080×1920 video, and uploads it to YouTube. A GitHub Action runs the whole thing on a daily cron.

## How it works

```
topics.py ──► generate_script()      Groq LLM (llama-3.3-70b) → JSON script
              │
              ▼
captions.py ─► voiceover + captions  edge-tts streams audio + word timings
              │                       → karaoke .ass subtitle file
              ▼
agent.py ────► build_video()         ffmpeg: background + synced captions → MP4
              │
              ▼
upload.py ───► upload_video()        YouTube Data API v3 (public Short)
```

| File | Role |
|------|------|
| `agent.py` | Orchestrates the full pipeline + daily de-duplication |
| `captions.py` | edge-tts voiceover **and** TikTok-style word-synced captions in one pass |
| `topics.py` | The pool of 80+ space topics to sample from |
| `upload.py` | YouTube OAuth + upload |
| `.github/workflows/daily.yml` | Daily cron that runs the agent |

## Local setup

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env           # then add your GROQ_API_KEY
```

You also need (both **gitignored** — never commit them):

- `client_secrets.json` — an OAuth **desktop** client from the [Google Cloud Console](https://console.cloud.google.com/) with the YouTube Data API enabled.
- `token.json` — generated automatically the first time you run and sign in.

`ffmpeg` must be available — either on your `PATH` or as a local `ffmpeg.exe` (the agent auto-detects).

## Run

```bash
python agent.py            # build + upload
$env:DRY_RUN=1; python agent.py   # build only, skip the upload (great for testing)
```

A background clip is optional: drop a `background.mp4` (or `bg1.mp4`…`bg5.mp4`) in the folder, otherwise the agent generates a starfield fallback so it never hard-fails.

## CI (daily automation)

The workflow runs at **07:00 UTC** daily (also triggerable manually from the Actions tab). It needs three repository secrets:

| Secret | Value |
|--------|-------|
| `GROQ_API_KEY` | Your Groq API key |
| `YOUTUBE_TOKEN` | Full contents of a working `token.json` |
| `CLIENT_SECRETS` | Full contents of `client_secrets.json` |

## ⚠️ Security

`.env`, `token.json`, and `client_secrets.json` hold live credentials and are gitignored. If they were ever committed in the past, treat them as **compromised**: rotate the Groq key and revoke/regenerate the YouTube OAuth credentials, since git history and forks may retain old copies.
