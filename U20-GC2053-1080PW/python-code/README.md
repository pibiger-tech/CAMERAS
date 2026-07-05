# Generic UVC Camera Python Toolkit

Vendor-neutral Python tools for **any** USB Video Class (UVC) camera. Nothing is
hardwired to a specific sensor or model — the camera, its formats/resolutions/
frame-rates, and its controls are all discovered at runtime.

## Layout

```
python_code/
├── uvc_camera.py            # shared core (Linux): detect, enumerate, control, verify
├── preview_linux.py         # live GUI preview (Linux, OpenCV)
├── preview_macos.py         # live GUI preview (macOS, uvc-util + OpenCV)
├── preview_windows.py       # live GUI preview (Windows, DirectShow)
├── linux/
│   ├── uvc_linux_control.py # control CLI (status/exposure/gain/verify/preview)
│   └── README_linux.md
├── macos/
│   ├── uvc_exposure_macos.py
│   ├── minimal_capture_macos.py
│   └── README_macos.md
└── windows/
    ├── uvc_windows_control.py
    ├── minimal_capture_windows.py
    └── README_windows.md
```

## Linux quick start (no extra Python deps needed for detection/verify)

```bash
sudo apt install v4l-utils                 # required (v4l2-ctl)

# list every UVC camera (CSI/MIPI excluded automatically)
python3 uvc_camera.py --list

# full info: formats, resolutions, fps, available controls
python3 uvc_camera.py --info

# headless capture self-test: measures real FPS, saves a frame.
# Uses v4l2-ctl streaming if OpenCV is absent (no pip install required).
python3 uvc_camera.py --verify --frames 90 --snapshot test

# control: status / set exposure / gain / verify
python3 linux/uvc_linux_control.py --status
python3 linux/uvc_linux_control.py --exposure-ms 5 --gain 16 --verify
python3 linux/uvc_linux_control.py --auto-exposure

# live preview (needs OpenCV: sudo apt install python3-opencv)
python3 preview_linux.py
```

Pick a specific camera by path or name:

```bash
python3 uvc_camera.py --info -d /dev/video2
python3 linux/uvc_linux_control.py --status --name "GC2053"
```

## What "generic" means here

- **No model filter** — `--list` returns any USB camera that can capture;
  Raspberry Pi CSI/MIPI sensors and platform/codec nodes (`platform:` bus) are
  excluded so they don't get mistaken for a UVC camera.
- **Default mode is discovered** — instead of a hardwired `1280x800@120`, the
  tools pick the camera's highest-resolution preferred (MJPG) mode and its top
  frame rate (`best_mode()`).
- **Controls are discovered** — old/new kernel control-name pairs are tried
  (`auto_exposure`/`exposure_auto`, `exposure_time_absolute`/`exposure_absolute`,
  `gain`/`analogue_gain`). Missing controls are skipped with a clear message.
- **Adapts to the camera's real menus** — e.g. `--auto-exposure` reads the actual
  `auto_exposure` menu and picks a valid "auto" entry; if the camera is
  manual-only it says so instead of erroring.
- **Trigger mode is treated as vendor-specific** — `--mode stream|trigger` only
  acts if the camera exposes `focus_automatic_continuous`, and the tool is honest
  that this is continuous-AF on standard cameras.

## Cross-platform exposure units (genuinely UVC, not model-specific)

| OS | Backend | Exposure unit | Manual switch |
|----|---------|---------------|---------------|
| Linux | `v4l2-ctl` | `exposure_time_absolute`, 100 µs units | `auto_exposure=1` |
| macOS | `uvc-util` | `exposure-time-abs`, 100 µs units | `auto-exposure-mode=1` |
| Windows | OpenCV `CAP_DSHOW` | `CAP_PROP_EXPOSURE` = log2(seconds) | `CAP_PROP_AUTO_EXPOSURE=0.25` |

See each platform's README for details.

## Verified

The Linux toolkit was verified against the currently-attached camera
(a GalaxyCore **GC2053** UVC module, `5843:7884`):

- `--list` / `--info`: detected `/dev/video0`, enumerated MJPG+YUYV at
  1920×1080 / 1280×720 / 800×600 / 640×480, picked **MJPG 1920×1080@30** as the
  default mode.
- `--verify`: streamed at **~30 fps** and saved a valid 1920×1080 color JPEG.
- control: `--exposure-ms 5` applied and read back (50 → 5.0 ms); the tool
  correctly reported this camera is **manual-exposure-only** (its `auto_exposure`
  menu offers only "Manual Mode") instead of failing.
