# PWSL Time Drop Finder (Web)

Web UI for generating PWSL time-drop ribbon labels from a Meet Maestro
**Time Improvement / Personal Best labels** PDF.

Based on the logic from
[LakeRidgeComputers/pwsl-div-time-drops](https://github.com/LakeRidgeComputers/pwsl-div-time-drops).

## What to export from Meet Maestro

Use the **Personal Best** or **Improvement** labels report for a single meet.
Do **not** use the general Results PDF — that layout varies and is not supported.

## Run with Docker (local)

```bash
docker compose up --build -d
```

Open [http://localhost:8000](http://localhost:8000).

1. Choose the Improvement labels PDF
2. Optionally change the output file name and minimum drop (default `1.0` seconds)
3. Click **Generate Label Sheet** — the printable PDF downloads in your browser

## Deploy on a server

The compose file binds to `127.0.0.1:8000` by default so you can put Caddy or
nginx in front for HTTPS.

```bash
git clone git@github.com:thegliffy/pwsl-div-time-drops-web.git
cd pwsl-div-time-drops-web
cp .env.example .env   # optional — edit APP_PORT / APP_BIND if needed
docker compose up --build -d
```

Useful commands:

```bash
docker compose logs -f      # follow logs
docker compose pull         # if you later switch to a published image
docker compose up --build -d
docker compose down
```

Example Caddy reverse proxy:

```caddy
timedrops.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Example nginx location:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 25m;
}
```

To expose the container directly on all interfaces (no reverse proxy):

```bash
APP_BIND=0.0.0.0 APP_PORT=8000 docker compose up --build -d
```

## Run locally (without Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
