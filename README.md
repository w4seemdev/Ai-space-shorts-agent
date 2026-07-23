# 🚀 AI Space Shorts Agent

An autonomous agent that produces and publishes a unique space/science **YouTube Short every day**, no human in the loop.

It writes a script with an LLM (with automatic model fallbacks), narrates it, burns in **word-synced captions**, renders a vertical 1080×1920 video over a procedurally generated drifting starfield with an ambient audio bed, and uploads it to YouTube. A GitHub Action runs the whole thing on a daily cron.

## How it works

```
topics.py ──► generate_script()      Groq LLM (fallback chain) → validated JSON script
              │                       word budget + content guard + retries
              ▼
captions.py ─► voiceover + captions  edge-tts streams audio + word timings (with retry)
              │                       → karaoke .ass captions sized to never clip
              ▼
agent.py ────► build_video()         ffmpeg: starfield/nebula background + captions
              │                       + ambient bed, loudness-normalized to -14 LUFS
              ▼
upload.py ───► upload_video()        YouTube Data API v3, chunked resumable upload
```

| File | Role |
|------|------|
| `agent.py` | Orchestrates the full pipeline + daily de-duplication |
| `captions.py` | edge-tts voiceover **and** TikTok-style word-synced captions in one pass |
| `topics.py` | The pool of 80+ space topics to sample from |
| `upload.py` | YouTube OAuth + resumable upload with retries |
| `authorize.py` | One-time local OAuth flow → writes a fresh `token.json` |
| `.github/workflows/daily.yml` | Daily cron that runs the agent |
| `.github/workflows/ci.yml` | pytest suite on every push/PR |

## Local setup

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env           # then add your GROQ_API_KEY
python authorize.py              # one-time browser sign-in → token.json
```

You also need (both **gitignored**, never commit them):

- `client_secrets.json` — an OAuth **desktop** client from the [Google Cloud Console](https://console.cloud.google.com/) with the YouTube Data API enabled.
- `token.json` — created by `python authorize.py`.

`ffmpeg` must be available, either on your `PATH` or as a local `ffmpeg.exe` (the agent auto-detects).

> **Important:** set the OAuth consent screen's Publishing status to **"In production"**. In "Testing" status Google expires refresh tokens every 7 days, which kills the daily automation weekly.

## Run

```bash
python agent.py            # build + upload
$env:DRY_RUN=1; python agent.py   # build only, skip the upload (great for testing)
pytest -q                  # run the test suite
```

A background clip is optional: drop a `background.mp4` (or `bg1.mp4`…`bg5.mp4`) in the folder to use real footage. Otherwise the agent **generates a fresh space scene per run** — drifting starfield + animated nebula wash with a randomized palette, so no two days look identical.

## CI (automation)

The workflow runs at **16:00 UTC** daily (noon US Eastern — prime Shorts window; also triggerable manually from the Actions tab). It needs three repository secrets:

| Secret | Value |
|--------|-------|
| `GROQ_API_KEY` | Your Groq API key ([console.groq.com/keys](https://console.groq.com/keys)) |
| `YOUTUBE_TOKEN` | Full contents of a working `token.json` (from `python authorize.py`) |
| `CLIENT_SECRETS` | Full contents of `client_secrets.json` |

Reliability features baked into the workflow:

- **Topic history is committed back** after every successful run (`history.json`), so de-duplication works across CI runs — and the daily commit keeps GitHub from auto-disabling the schedule after 60 days of inactivity.
- **Failures open/refresh a GitHub issue** (lands in your email) and upload the intermediate mp3/ass/mp4 as debug artifacts — a broken day can never again go unnoticed.
- **Every run writes a step summary** (topic, title, voice, model, video URL) on its Actions page.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401 Invalid API Key` from Groq | Rotate `GROQ_API_KEY` in `.env` **and** the repo secret |
| `invalid_grant` from Google | Re-run `python authorize.py`, update the `YOUTUBE_TOKEN` secret |
| `invalid_grant` recurs weekly | Set the OAuth consent screen to **In production** |
| Schedule stopped firing | Actions tab → the workflow may be disabled — click *Enable workflow* |

## ⚠️ Security

`.env`, `token.json`, and `client_secrets.json` are gitignored, keep them local (or in GitHub Secrets for CI) and never commit them.

---

Built by [Waseem Abu Fares](https://github.com/w4seemdev)
