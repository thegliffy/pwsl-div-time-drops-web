# PWSL Time Drop Finder (Web)

Web UI for generating PWSL time-drop ribbon labels from a Meet Maestro
**Time Improvement / Personal Best labels** PDF.

Based on the logic from
[LakeRidgeComputers/pwsl-div-time-drops](https://github.com/LakeRidgeComputers/pwsl-div-time-drops).

## What to export from Meet Maestro

Use the **Personal Best** or **Improvement** labels report for a single meet.
Do **not** use the general Results PDF — that layout varies and is not supported.

## Run with Docker

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000).

1. Choose the Improvement labels PDF
2. Optionally change the output file name and minimum drop (default `1.0` seconds)
3. Click **Generate Label Sheet** — the printable PDF downloads in your browser

## Run locally (without Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
