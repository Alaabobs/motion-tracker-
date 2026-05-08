# Motion Cam

A simple motion-activated webcam written in Python. It watches a live feed from your webcam, and whenever something moves in the frame it records a short video clip with a timestamp. You can also have it email you when motion is detected.

I built this as a small home-monitoring project — point a laptop at the front door, walk away, and check the clips later. Nothing fancy under the hood: just frame differencing with OpenCV.

## What it does

- Watches your webcam in real time
- Detects motion using frame differencing (no ML, no GPU needed)
- Records 10-second MP4 clips every time it sees something move
- Draws green boxes around the moving stuff while it's recording
- Optionally sends an email alert with the clip's filename

## Requirements

- Python 3.9+
- A working webcam
- The packages listed in `requirements.txt`

## Setup

Clone the repo and install the dependencies:

```bash
git clone https://github.com/<your-username>/motion-cam.git
cd motion-cam
pip install -r requirements.txt
```

If you want email alerts, copy `.env.example` to `.env` and fill in your details:

```bash
cp .env.example .env
```

Then open `.env` and set your sender email, app password, and the address you want alerts sent to. **For Gmail you need an App Password, not your normal password** — see https://myaccount.google.com/apppasswords.

If you don't care about email alerts, just leave `SEND_EMAIL=false` and skip the `.env` step entirely.

## Running it

```bash
python motion_cam.py
```

A window will open showing the webcam feed. Move around in front of it and you should see green boxes appear plus a red `REC` indicator while it captures a clip. Clips are saved to a `clips/` folder by default. Press `Q` to quit.

## Tweaking the sensitivity

All the knobs are at the top of `motion_cam.py`:

- `MOTION_THRESHOLD` — how big a moving blob has to be before it counts. Lower = more sensitive.
- `COOLDOWN_SECONDS` — wait time between clips so you don't get 50 files from one event.
- `CLIP_DURATION` — how long each recording lasts.
- `DRAW_BOXES` — set to `False` if you don't want the green rectangles.

## Project layout

```
motion-cam/
├── motion_cam.py       # the main script
├── requirements.txt    # pip dependencies
├── .env.example        # template for your credentials
├── .gitignore          # files git should ignore
├── LICENSE             # MIT
└── README.md           # you are here
```

## Notes

The `clips/` folder and `.env` file are both in `.gitignore`, so your recordings and credentials never end up on GitHub by accident.

If the webcam fails to open, make sure no other app (Zoom, Teams, browser tab, etc.) is using it.

## License

MIT — do whatever you want with it.
