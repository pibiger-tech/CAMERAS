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
| [`firmware/`](./firmware/) | Firmware binaries, flashing tool, and XChip firmware editor |
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

### XChip XC8031 Firmware Editor

**[`firmware/XChip_XC8031_Tool_Windows.zip`](./firmware/XChip_XC8031_Tool_Windows.zip)** — Windows GUI/CLI tool for offline editing of XChip XC8031 packaged firmware (`.bin`). Allows viewing and patching VID, PID, product name, manufacturer, and serial number without live camera connection.

**Package contents:**

| File | Description |
| :--- | :--- |
| `XChip_XC8031_Tool.exe` | Standalone GUI — double-click to run (Python embedded) |
| `USBCam Download Tool V3.6.exe` | Vendor flash tool for programming patched firmware to camera |
| `samples/PIBIGER-U20-GC2053_SN0001.bin` | Sample firmware binary |
| `README.md` | Usage guide |

**Workflow:**
1. Extract the zip
2. Run `XChip_XC8031_Tool.exe` → **Open .bin** (e.g. `PIBIGER-U20-GC2053_SN0001.bin`)
3. Review chip info (VID / PID / product name / frame table)
4. Edit USB identity fields → **Apply to image** → **Save As…** `*_patched.bin`
5. Open `USBCam Download Tool V3.6.exe` → select patched `.bin` → flash → replug and verify

**CLI usage:**
```powershell
# View firmware info
python xchip_cli.py info -i PIBIGER-U20-GC2053_SN0001.bin --section

# Patch VID/PID and product name
python xchip_cli.py patch -i original.bin -o patched.bin --vid 0x1234 --pid 0xABCD --manufacturer "MyCompany" --product "MyCam" --serial "SN001"
```

> ⚠️ Always keep a backup of the original `.bin` before patching. A corrupted image may prevent the camera from enumerating.

---

## Support

| | |
|---|---|
| Website | [www.pibiger-tech.com](https://www.pibiger-tech.com) |
| Sales | sales@pibiger-tech.com |
| Technical Support | support@pibiger-tech.com |
