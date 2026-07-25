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

The compose file publishes port `8000` on all interfaces by default
(`0.0.0.0:8000`). Open that port in your firewall if needed.

```bash
git clone https://github.com/thegliffy/pwsl-div-time-drops-web.git
cd pwsl-div-time-drops-web
cp .env.example .env   # optional — edit APP_PORT / APP_BIND if needed
docker compose up --build -d
```

Then open `http://YOUR_SERVER_IP:8000`.

Useful commands:

```bash
docker compose logs -f
docker compose up --build -d
docker compose down
```

To bind localhost-only behind a reverse proxy instead:

```bash
APP_BIND=127.0.0.1 docker compose up --build -d
```

Example Caddy reverse proxy (with `APP_BIND=127.0.0.1`):

```caddy
timedrops.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

## Run locally (without Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
