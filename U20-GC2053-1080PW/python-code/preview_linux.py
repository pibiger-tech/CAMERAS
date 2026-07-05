#!/usr/bin/env python3
"""
Generic UVC Camera Live Preview - Linux
=======================================

Standalone preview window for ANY UVC camera on Linux. Vendor-neutral:
the camera, its default resolution/fps and its controls are all discovered
at runtime (see uvc_camera.py). No specific sensor/model assumed.

Features:
  - Live preview with on-screen FPS / resolution / exposure overlay
  - Auto-detect the first UVC camera (or pick by name / device path)
  - Default capture mode = camera's highest-res preferred format
  - Hotkeys: q=quit, s=snapshot, +/-=exposure, [/]=gain, a=auto/manual AE
  - Gracefully skips controls the camera does not expose

Requirements:
  sudo apt install v4l-utils python3-opencv
  # or: pip3 install opencv-python numpy

Usage:
  python3 preview_linux.py                              # auto-detect, best mode
  python3 preview_linux.py -d /dev/video2               # specific device
  python3 preview_linux.py --name "GC2053"              # pick by name regex
  python3 preview_linux.py --width 1280 --height 720 --fps 30
  python3 preview_linux.py --exposure-ms 5 --gain 32    # set exposure/gain at start
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uvc_camera as uvc

try:
    import cv2
except ImportError:
    print("[ERROR] OpenCV not installed. sudo apt install python3-opencv")
    sys.exit(1)


def run_preview(device, width, height, fps, fourcc, exposure_ms=None, gain=None):
    ctrl_ae = uvc.find_control(device, uvc.CTRL_AUTO_EXPOSURE)
    ctrl_exp = uvc.find_control(device, uvc.CTRL_EXPOSURE)
    ctrl_gain = uvc.find_control(device, uvc.CTRL_GAIN)

    if exposure_ms is not None and ctrl_exp:
        uvc.set_manual_exposure(device, int(round(exposure_ms * 10)))
    if gain is not None and ctrl_gain:
        uvc.set_gain(device, gain)

    cap = uvc.open_capture(device, width, height, fps, fourcc)
    if cap is None:
        print(f"[ERROR] Cannot open {device}")
        return

    aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    afps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[Open] {device}: {aw}x{ah} @ {afps:.1f}fps")
    print("Hotkeys: q=quit  s=snapshot  +/-=exposure  ]/[=gain  a=auto/manual AE")
    if not ctrl_exp:
        print("[Note] this camera exposes no exposure control; +/- disabled")

    os.makedirs("snapshots", exist_ok=True)
    current_exp_ms = exposure_ms if exposure_ms else 5.0
    current_gain = gain if gain is not None else 0
    auto_exp = exposure_ms is None

    frame_count, fps_t0, measured_fps = 0, time.time(), 0.0
    win = "UVC Camera Preview (Linux)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Frame read failed")
            time.sleep(0.05)
            continue

        frame_count += 1
        elapsed = time.time() - fps_t0
        if elapsed >= 1.0:
            measured_fps = frame_count / elapsed
            frame_count, fps_t0 = 0, time.time()

        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 70), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        mode_str = "AUTO" if auto_exp else "MANUAL"
        cv2.putText(frame, f"{w}x{h}  {measured_fps:.1f} fps", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        cv2.putText(frame, f"Exp: {current_exp_ms:.1f}ms ({mode_str})  "
                           f"Gain: {current_gain}", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        cv2.imshow(win, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            fname = f"snapshots/snap_{time.strftime('%Y%m%d_%H%M%S')}.png"
            cv2.imwrite(fname, frame)
            print(f"[Save] {fname}")
        elif key in (ord('+'), ord('=')) and ctrl_exp:
            current_exp_ms = min(33.0, current_exp_ms + 1.0)
            uvc.set_manual_exposure(device, int(round(current_exp_ms * 10)))
            auto_exp = False
        elif key in (ord('-'), ord('_')) and ctrl_exp:
            current_exp_ms = max(0.1, current_exp_ms - 1.0)
            uvc.set_manual_exposure(device, int(round(current_exp_ms * 10)))
            auto_exp = False
        elif key == ord(']') and ctrl_gain:
            current_gain += 4
            uvc.set_gain(device, current_gain)
        elif key == ord('[') and ctrl_gain:
            current_gain = max(0, current_gain - 4)
            uvc.set_gain(device, current_gain)
        elif key == ord('a') and ctrl_ae:
            if auto_exp:
                uvc.set_control(device, ctrl_ae, uvc.AE_MANUAL)
                auto_exp = False
                print("[Mode] MANUAL exposure")
            else:
                uvc.set_auto_exposure(device)
                auto_exp = True
                print("[Mode] AUTO exposure")

    cap.release()
    cv2.destroyAllWindows()
    print("[Done]")


def main():
    p = argparse.ArgumentParser(description="Generic UVC live preview (Linux)")
    p.add_argument("-d", "--device", default=None, help="device (default: auto)")
    p.add_argument("--name", default=None, help="pick camera by name regex")
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--fps", type=int, default=None)
    p.add_argument("--fourcc", default=None, help="e.g. MJPG or YUYV")
    p.add_argument("--exposure-ms", type=float, default=None)
    p.add_argument("--gain", type=int, default=None)
    args = p.parse_args()

    device = uvc.pick_camera(args.device, args.name)
    if not device or not os.path.exists(device):
        print(f"[ERROR] Camera not found: {device}")
        sys.exit(1)

    w, h, fps, fourcc = args.width, args.height, args.fps, args.fourcc
    if not (w and h):
        bm = uvc.best_mode(device)
        if bm:
            fourcc = fourcc or bm[0]
            w, h, fps = bm[1], bm[2], fps or int(bm[3])
            print(f"[Auto] default mode: {fourcc} {w}x{h} @ {fps}fps")

    run_preview(device, w, h, fps, fourcc, args.exposure_ms, args.gain)


if __name__ == "__main__":
    main()
