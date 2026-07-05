#!/usr/bin/env python3
"""
Generic UVC Camera Core (Linux)
===============================

Vendor-neutral helpers for ANY USB Video Class (UVC) camera on Linux.
No assumptions about a specific sensor/model. Everything is discovered at
runtime from the kernel via `v4l2-ctl` (v4l-utils):

  - Enumerate real UVC capture cameras (CSI/MIPI & platform nodes excluded)
  - Enumerate supported pixel formats / resolutions / frame rates
  - Discover available controls dynamically (names vary by kernel/camera)
  - Get/set controls (exposure, gain, ... ) with old/new kernel name fallback
  - Headless capture self-test (measure real FPS, save a snapshot)

This module is imported by preview_linux.py and linux/uvc_linux_control.py,
and is also runnable directly:

    python3 uvc_camera.py --list              # list all UVC cameras
    python3 uvc_camera.py --info              # full info for the picked camera
    python3 uvc_camera.py --verify            # headless capture self-test

Requirements:
    sudo apt install v4l-utils          # required (v4l2-ctl)
    pip3 install opencv-python numpy    # only for --verify / preview
"""

import argparse
import glob
import os
import re
import subprocess
import sys
import time


# ============================================================
# Control-name candidates (kernel/camera dependent; try in order)
# ============================================================
CTRL_AUTO_EXPOSURE = ["auto_exposure", "exposure_auto"]
CTRL_EXPOSURE = ["exposure_time_absolute", "exposure_absolute"]
CTRL_GAIN = ["gain", "analogue_gain"]
# Some UVC cameras (e.g. global-shutter trigger modules) repurpose this
# control as a stream/trigger-mode switch. Optional — only used if present.
CTRL_TRIGGER = ["focus_automatic_continuous", "focus_auto"]

# UVC auto_exposure menu values: 1 = Manual, 3 = Aperture-priority (auto)
AE_MANUAL = 1
AE_AUTO = 3


# ============================================================
# Low-level v4l2-ctl wrappers
# ============================================================

def _run(args, timeout=5):
    """Run a command, return stdout (str). '' on any failure."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except FileNotFoundError:
        if args and args[0] == "v4l2-ctl":
            print("[ERROR] v4l2-ctl not found. Install: sudo apt install v4l-utils",
                  file=sys.stderr)
            sys.exit(1)
        return ""
    except Exception:
        return ""


def _bus_info(node):
    """Return the 'Bus info' string for a /dev/videoN node (e.g. usb-xhci...)."""
    out = _run(["v4l2-ctl", "-d", node, "--info"])
    m = re.search(r"Bus info\s*:\s*(.+)", out)
    return m.group(1).strip() if m else ""


def _card_name(node):
    out = _run(["v4l2-ctl", "-d", node, "--info"])
    m = re.search(r"Card type\s*:\s*(.+)", out)
    return m.group(1).strip() if m else ""


def _is_capture(node):
    """True if the node exposes at least one capture pixel format."""
    out = _run(["v4l2-ctl", "-d", node, "--list-formats-ext"])
    return "[" in out and "Size" in out


# ============================================================
# Camera discovery (generic UVC, no model filter)
# ============================================================

def list_uvc_cameras():
    """
    Return a list of dicts for every real UVC *capture* camera:
        {"node", "index", "name", "bus"}
    Only USB (UVC) nodes that can capture are returned. Raspberry Pi
    CSI/MIPI sensors and platform/codec nodes (Bus info 'platform:...')
    are excluded by design.
    """
    cams = []
    seen_bus = set()
    for node in sorted(glob.glob("/dev/video*"),
                       key=lambda p: int(re.sub(r"\D", "", p) or 0)):
        bus = _bus_info(node)
        # UVC cameras report a USB bus; CSI/codecs report 'platform:'
        if not bus.lower().startswith("usb"):
            continue
        if not _is_capture(node):
            continue
        # A single physical UVC camera often exposes several /dev/video
        # nodes (capture + metadata). Keep only the first capture node
        # per USB bus path.
        if bus in seen_bus:
            continue
        seen_bus.add(bus)
        idx = int(re.sub(r"\D", "", node) or 0)
        cams.append({"node": node, "index": idx,
                     "name": _card_name(node) or "USB Camera", "bus": bus})
    return cams


def pick_camera(device=None, name_filter=None):
    """
    Resolve a camera node.
      - device given        -> use it as-is
      - name_filter given   -> first UVC camera whose name matches (regex, i)
      - otherwise           -> first detected UVC camera
    Returns a node path string, or None if nothing suitable is found.
    """
    if device:
        return device
    cams = list_uvc_cameras()
    if not cams:
        return None
    if name_filter:
        for c in cams:
            if re.search(name_filter, c["name"], re.IGNORECASE):
                return c["node"]
    return cams[0]["node"]


# ============================================================
# Format / resolution / fps enumeration
# ============================================================

def list_formats(device):
    """
    Parse `v4l2-ctl --list-formats-ext` into:
        {fourcc: [ {"w":W, "h":H, "fps":[f1,f2,...]}, ... ], ...}
    """
    out = _run(["v4l2-ctl", "-d", device, "--list-formats-ext"])
    formats = {}
    cur_fmt = None
    cur_size = None
    for line in out.splitlines():
        mf = re.search(r"\]\s*:\s*'(\w+)'", line)
        if mf:
            cur_fmt = mf.group(1)
            formats.setdefault(cur_fmt, [])
            cur_size = None
            continue
        ms = re.search(r"Size:\s*\w+\s+(\d+)x(\d+)", line)
        if ms and cur_fmt:
            cur_size = {"w": int(ms.group(1)), "h": int(ms.group(2)), "fps": []}
            formats[cur_fmt].append(cur_size)
            continue
        mr = re.search(r"\(([\d.]+)\s*fps\)", line)
        if mr and cur_size is not None:
            cur_size["fps"].append(float(mr.group(1)))
    return formats


def best_mode(device, prefer=("MJPG", "MJPEG")):
    """
    Choose a sensible default capture mode: highest resolution of a preferred
    (compressed) format, with its highest frame rate. Falls back to any format.
    Returns (fourcc, w, h, fps) or None.
    """
    formats = list_formats(device)
    if not formats:
        return None
    order = [f for f in prefer if f in formats] + \
            [f for f in formats if f not in prefer]
    fourcc = order[0]
    sizes = formats[fourcc]
    if not sizes:
        return None
    big = max(sizes, key=lambda s: s["w"] * s["h"])
    fps = max(big["fps"]) if big["fps"] else 30.0
    return (fourcc, big["w"], big["h"], fps)


# ============================================================
# Controls
# ============================================================

def list_controls_raw(device):
    return _run(["v4l2-ctl", "-d", device, "-l"])


def parse_controls(device):
    """Return {name: {min,max,default,value,type}} parsed from `v4l2-ctl -l`."""
    out = list_controls_raw(device)
    ctrls = {}
    for line in out.splitlines():
        m = re.match(r"\s*([\w_]+)\s+0x[0-9a-f]+\s+\((\w+)\)\s*:\s*(.+)", line)
        if not m:
            continue
        name, ctype, rest = m.group(1), m.group(2), m.group(3)
        d = {"type": ctype}
        for key in ("min", "max", "default", "value", "step"):
            mm = re.search(rf"{key}=(-?\d+)", rest)
            if mm:
                d[key] = int(mm.group(1))
        ctrls[name] = d
    return ctrls


def find_control(device, candidates):
    """Return the first candidate control name that exists on the device."""
    text = list_controls_raw(device)
    for name in candidates:
        if re.search(rf"^\s*{re.escape(name)}\s+0x", text, re.MULTILINE):
            return name
    return None


def get_control(device, name):
    if not name:
        return None
    out = _run(["v4l2-ctl", "-d", device, "-C", name])
    return out.split(":", 1)[1].strip() if ":" in out else None


def ctrl_int(value):
    """
    Extract the leading integer from a control value. v4l2-ctl returns menu
    controls as 'N (Label)' (e.g. '1 (Manual Mode)') and plain controls as
    'N'. Returns int or None.
    """
    if value is None:
        return None
    m = re.match(r"\s*(-?\d+)", str(value))
    return int(m.group(1)) if m else None


def set_control(device, name, value, verbose=True):
    if not name:
        return False
    try:
        r = subprocess.run(["v4l2-ctl", "-d", device, "-c", f"{name}={value}"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            if verbose:
                print(f"  [v4l2-ctl] FAILED {name}={value}: {r.stderr.strip()}")
            return False
        return True
    except Exception as e:
        if verbose:
            print(f"  [v4l2-ctl] ERROR {name}={value}: {e}")
        return False


def set_manual_exposure(device, exposure_uvc):
    """Switch to manual AE (if available) then set exposure (UVC 100us units)."""
    ae = find_control(device, CTRL_AUTO_EXPOSURE)
    exp = find_control(device, CTRL_EXPOSURE)
    if not exp:
        print("  [Exp] no exposure control on this camera")
        return False
    if ae:
        set_control(device, ae, AE_MANUAL)
    ok = set_control(device, exp, exposure_uvc)
    if ok:
        print(f"  [Exp] {exp}={exposure_uvc} ({exposure_uvc/10.0:.1f} ms), "
              f"verify={get_control(device, exp)}")
    return ok


def control_menu(device, name):
    """Return {int_value: label} for a menu control (from `v4l2-ctl -L`)."""
    out = _run(["v4l2-ctl", "-d", device, "-L"])
    menu, in_ctrl = {}, False
    for line in out.splitlines():
        if re.match(rf"\s*{re.escape(name)}\s+0x", line):
            in_ctrl = True
            continue
        if in_ctrl:
            m = re.match(r"\s*(\d+):\s*(.+)", line)
            if m:
                menu[int(m.group(1))] = m.group(2).strip()
            elif re.match(r"\s*[\w_]+\s+0x", line):
                break  # next control reached
    return menu


def set_auto_exposure(device):
    """
    Restore auto exposure, adapting to the camera's actual menu. Many UVC
    cameras use 3 (Aperture Priority); some expose only Manual. We pick a
    menu entry whose label looks 'auto', else the control default.
    """
    ae = find_control(device, CTRL_AUTO_EXPOSURE)
    if not ae:
        print("  [Exp] no auto-exposure control on this camera")
        return False
    menu = control_menu(device, ae)
    candidates = [v for v, lbl in menu.items()
                  if re.search(r"auto|aperture|priority", lbl, re.IGNORECASE)]
    if not candidates and AE_AUTO in menu:
        candidates = [AE_AUTO]
    for val in candidates:
        if set_control(device, ae, val, verbose=False):
            print(f"  [Exp] {ae}={val} ({menu.get(val, 'auto')})")
            return True
    print(f"  [Exp] this camera offers no auto-exposure mode "
          f"(menu={menu or 'n/a'}); leaving manual")
    return False


def set_gain(device, value):
    g = find_control(device, CTRL_GAIN)
    if not g:
        print("  [Gain] no gain control on this camera")
        return False
    ok = set_control(device, g, value)
    if ok:
        print(f"  [Gain] {g}={value} (verify={get_control(device, g)})")
    return ok


# ============================================================
# Capture / verification (OpenCV optional)
# ============================================================

def node_to_index(device):
    m = re.search(r"/dev/video(\d+)", device)
    return int(m.group(1)) if m else 0


def open_capture(device, width=None, height=None, fps=None, fourcc=None):
    """Open a cv2.VideoCapture on the V4L2 backend with optional format hints."""
    import cv2
    cap = cv2.VideoCapture(node_to_index(device), cv2.CAP_V4L2)
    if not cap.isOpened():
        return None
    if fourcc:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc[:4]))
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps:
        cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


def verify_v4l2(device, width=None, height=None, fps=None, fourcc=None,
                frames=60, snapshot=None):
    """
    Dependency-free capture self-test using `v4l2-ctl --stream-mmap`.
    Used automatically when OpenCV is not installed. Measures the real
    streaming FPS and (optionally) saves one raw frame. Returns True on
    success.
    """
    mode = best_mode(device) if not (width and height) else None
    if mode:
        fourcc = fourcc or mode[0]
        width, height, fps = mode[1], mode[2], fps or mode[3]
    fourcc = fourcc or "MJPG"
    print(f"[verify] requested: {width}x{height} {fourcc} (v4l2-ctl backend)")
    cmd = ["v4l2-ctl", "-d", device,
           f"--set-fmt-video=width={width},height={height},pixelformat={fourcc}",
           "--stream-mmap", f"--stream-count={frames}", "--stream-to=/dev/null"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=max(20, frames // 2))
    except Exception as e:
        print(f"[verify] streaming failed: {e}")
        return False
    fps_vals = re.findall(r"([\d.]+)\s*fps", r.stdout + r.stderr)
    if fps_vals:
        print(f"[verify] measured: {fps_vals[-1]} fps over {frames} frames")
    ok = (r.returncode == 0)
    if snapshot:
        ext = "mjpg" if fourcc.startswith("M") else "raw"
        snap = snapshot if "." in snapshot else f"{snapshot}.{ext}"
        subprocess.run(["v4l2-ctl", "-d", device,
                        f"--set-fmt-video=width={width},height={height},"
                        f"pixelformat={fourcc}",
                        "--stream-mmap", "--stream-count=1",
                        f"--stream-to={snap}"],
                       capture_output=True, timeout=15)
        if os.path.exists(snap):
            print(f"[verify] snapshot saved: {snap} ({os.path.getsize(snap)} bytes)")
    print(f"[verify] {'OK' if ok else 'FAILED'}")
    return ok


def verify(device, width=None, height=None, fps=None, fourcc=None,
           frames=60, snapshot=None):
    """
    Headless capture self-test: grab `frames` frames, report the actual
    negotiated format and measured FPS. Optionally save a snapshot.
    Returns True if frames were captured. No GUI needed.

    Uses OpenCV when available; otherwise falls back to v4l2-ctl streaming
    so verification needs no extra Python packages.
    """
    try:
        import cv2
    except ImportError:
        return verify_v4l2(device, width, height, fps, fourcc, frames, snapshot)

    mode = None
    if not (width and height):
        mode = best_mode(device)
        if mode:
            fourcc = fourcc or mode[0]
            width, height, fps = mode[1], mode[2], fps or mode[3]

    cap = open_capture(device, width, height, fps, fourcc)
    if cap is None:
        print(f"[verify] cannot open {device}")
        return False

    aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    afps = cap.get(cv2.CAP_PROP_FPS)
    fcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    fcc_str = "".join([chr((fcc >> 8 * i) & 0xFF) for i in range(4)]).strip()
    print(f"[verify] negotiated: {aw}x{ah} @ {afps:.1f}fps  fourcc={fcc_str!r}")

    ok = 0
    last = None
    t0 = time.time()
    for _ in range(frames):
        ret, frame = cap.read()
        if ret:
            ok += 1
            last = frame
    dt = time.time() - t0
    meas = ok / dt if dt > 0 else 0.0
    print(f"[verify] captured {ok}/{frames} frames in {dt:.2f}s "
          f"-> {meas:.1f} fps measured")

    if snapshot and last is not None:
        cv2.imwrite(snapshot, last)
        print(f"[verify] snapshot saved: {snapshot}")

    cap.release()
    return ok > 0


# ============================================================
# Pretty info
# ============================================================

def print_info(device):
    print("=" * 64)
    print(f"  Camera: {device}   ({_card_name(device)})")
    print(f"  Bus:    {_bus_info(device)}")
    print("=" * 64)

    bm = best_mode(device)
    if bm:
        print(f"  Suggested default mode: {bm[0]} {bm[1]}x{bm[2]} @ {bm[3]:.0f}fps")
    print("\n  Supported formats:")
    for fcc, sizes in list_formats(device).items():
        res = ", ".join(sorted({f"{s['w']}x{s['h']}" for s in sizes},
                               key=lambda r: int(r.split('x')[0]), reverse=True))
        print(f"    {fcc}: {res}")

    print("\n  Notable controls:")
    for label, cands in (("auto-exposure", CTRL_AUTO_EXPOSURE),
                         ("exposure", CTRL_EXPOSURE),
                         ("gain", CTRL_GAIN),
                         ("focus-AF (vendor trigger?)", CTRL_TRIGGER)):
        name = find_control(device, cands)
        if name:
            print(f"    {label:22s}: {name} = {get_control(device, name)}")
        else:
            print(f"    {label:22s}: (not available)")


# ============================================================
# CLI
# ============================================================

def main():
    ap = argparse.ArgumentParser(description="Generic UVC camera core (Linux)")
    ap.add_argument("-d", "--device", default=None, help="/dev/videoN (default: auto)")
    ap.add_argument("--name", default=None, help="pick camera by name regex")
    ap.add_argument("--list", action="store_true", help="list all UVC cameras")
    ap.add_argument("--info", action="store_true", help="show formats/controls")
    ap.add_argument("--verify", action="store_true", help="headless capture self-test")
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--snapshot", default=None, help="save a frame during --verify")
    args = ap.parse_args()

    if args.list:
        cams = list_uvc_cameras()
        if not cams:
            print("No UVC cameras found.")
            return
        for c in cams:
            print(f"  {c['node']}  [{c['name']}]  bus={c['bus']}")
        return

    device = pick_camera(args.device, args.name)
    if not device or not os.path.exists(device):
        print(f"[ERROR] no UVC camera found (device={device})")
        sys.exit(1)

    if args.verify:
        ok = verify(device, frames=args.frames, snapshot=args.snapshot)
        sys.exit(0 if ok else 2)

    # default / --info
    print_info(device)


if __name__ == "__main__":
    main()
