# U20-GC2053-1080PW

**USB UVC 1080P Camera Module (GalaxyCore GC2053)**

---

## Overview

The **U20-GC2053-1080PW** is a compact USB UVC camera module based on the **GalaxyCore GC2053** 1/2.9" CMOS sensor, delivering **1920×1080 @ 30fps** over a standard USB 2.0 interface. It is fully UVC-compliant — no driver installation required on Windows, Linux, or macOS.

---

## Repository Contents

| File / Folder | Description |
| :--- | :--- |
| [`U20-GC2053-1080PW_EN.md`](./U20-GC2053-1080PW_EN.md) | Full English user manual (specifications, UVC controls, firmware, Python SDK) |
| [`U20-GC2053-1080PW_CN.md`](./U20-GC2053-1080PW_CN.md) | 中文用户手册 |
| [`firmware/`](./firmware/) | Firmware binaries and flashing tool |
| [`python-code/`](./python-code/) | Cross-platform Python SDK (Windows / Linux / macOS) |
| [`YT10077-HD.pdf`](./YT10077-HD.pdf) | Lens datasheet |

---

## Quick Start

### 1. Connect

Plug the camera into a USB 2.0 or USB 3.0 port. No driver installation required.

### 2. Preview

**Windows:** Open any camera app (e.g., Windows Camera), or use OBS / VLC.

**Linux:**
```bash
sudo apt install v4l-utils
v4l2-ctl --list-devices
ffplay /dev/video0
```

**macOS:** Open QuickTime Player → File → New Movie Recording → select camera.

### 3. Python SDK

```bash
# List cameras
python3 python-code/uvc_camera.py --list

# Verify capture and save snapshot
python3 python-code/uvc_camera.py --verify --frames 90 --snapshot test
```

See [`python-code/README.md`](./python-code/README.md) for full usage.

---

## Firmware

The camera ships with **PIBIGER brand firmware** by default. A generic (white-label) firmware is also provided.

| Firmware | Branding | PID | VID |
| :--- | :--- | :--- | :--- |
| `PIBIGER-U20-GC2053_SN0001.bin` | PIBIGER | 7884 | 5843 |
| `U20-1080P_SN001.bin` | USB_CAMERA (generic) | 7884 | 5843 |

Flash using [`firmware/USBCamDownloadToolV3.6.exe`](./firmware/USBCamDownloadToolV3.6.exe) (Windows).

---

## Support

| | |
|---|---|
| Website | [www.pibiger-tech.com](https://www.pibiger-tech.com) |
| Sales | sales@pibiger-tech.com |
| Technical Support | support@pibiger-tech.com |
