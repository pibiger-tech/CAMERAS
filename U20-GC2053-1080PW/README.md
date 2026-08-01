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
| [`Firmware-Development/`](./Firmware-Development/) | SPCA firmware tools and SDK for firmware backup, flashing, USB ID editing, and OEM development |
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

## Firmware Development Tools

The [`Firmware-Development/`](./Firmware-Development/) folder contains two packages for SPCA-based firmware development and factory operations:

### SPCA_ISP_Tool_Windows_x64.zip

A standalone Windows x64 GUI tool for Sunplus SPCA USB cameras. No installation required.

**Features:**
- **Read** full ISP flash to a `.bin` file (firmware backup)
- **Write** a `.bin` image to the camera (firmware flash)
- **Edit** USB descriptor fields: VID, PID, product name, manufacturer, serial number

**Package contents:**

| File | Description |
| :--- | :--- |
| `SPCA_ISP_Tool.exe` | Main program — double-click to run |
| `SunplusCamera.dll` | SPCA API library (bundled for override / repair) |
| `README.md` | Usage guide |

**Quick start:**
1. Extract the zip and plug in the camera via USB
2. Run `SPCA_ISP_Tool.exe` → click **Refresh** → select device → **Read Info**
3. **Backup first:** Read Firmware… → save as `.bin`
4. **Flash:** Write Firmware… → select `.bin` → confirm → replug camera
5. **Change USB ID:** Fill from Device → edit VID/PID/name → Apply to Device → replug to verify

> ⚠️ Always backup before flashing or changing USB IDs. A wrong image may prevent the camera from enumerating.

---

### SPCA_System_SDK_Customer.zip

A comprehensive SDK package for OEM/ODM customers integrating SPCA-based USB cameras into their products. Covers Windows, Android, and Linux platforms.

**Package contents:**

| Path | Description |
| :--- | :--- |
| `Windows/SPCA_API_S1_v9.2307.18.1/` | Windows DLL (`SunplusCamera.dll`/`.lib`), C header (`sunpluscamera.h`), Visual Studio demo projects (`SunplusDll_Demo`, `Multi_Demo_DLL`), CHM API reference |
| `Android/FWUpdate_APK/` | Pre-built Android APK for firmware update (`SPCAFWUpdate_20230609.apk`) |
| `Android/SDK/` | Android firmware update demo project (`SPCADemo_FWUpdate_0409.zip`) |
| `Linux/` | Linux firmware upgrade package (`Linux_Upgrade.7z`) |
| `Tools/SPCA_ISP_Tool/` | Same ISP tool as above (included for convenience) |

**Windows development quick start:**
1. Extract the zip
2. Reference `SPCamera/x64/SunplusCamera.lib` in your Visual Studio project
3. Include `SPCamera/sunpluscamera.h`
4. Deploy `SPCamera/x64/SunplusCamera.dll` alongside your executable
5. See `SunplusDll_Demo/` or `Multi_Demo_DLL/` for working example code
6. Refer to the CHM API reference (`readme.chm`) for full API documentation

**Android quick start:**
- Install `FWUpdate_APK/SPCAFWUpdate_20230609.apk` directly for firmware update
- Or open `SDK/SPCADemo_FWUpdate_0409.zip` in Android Studio for integration

**Linux quick start:**
- Extract `Linux/Linux_Upgrade.7z` and follow the included instructions

> **Scope:** This SDK is for SPCA product integration, factory tools, and firmware update. It does not include ISP firmware source code. For chip-specific support (secure download, write-protect, supported IC list), contact your FAE.

---

## Support

| | |
|---|---|
| Website | [www.pibiger-tech.com](https://www.pibiger-tech.com) |
| Sales | sales@pibiger-tech.com |
| Technical Support | support@pibiger-tech.com |
