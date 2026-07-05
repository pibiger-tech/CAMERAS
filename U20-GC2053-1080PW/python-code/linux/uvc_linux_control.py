#!/usr/bin/env python3
"""
Generic UVC Camera Control - Linux
==================================

Vendor-neutral control CLI for ANY UVC camera via v4l2-ctl. Works with any
USB camera; controls are discovered at runtime (names differ across kernels
and cameras). Built on the shared core in ../uvc_camera.py.

  - Show status + full control list of the picked camera
  - Set manual exposure (ms or raw UVC units) / restore auto exposure
  - Set gain
  - Optional stream/trigger mode switch -- ONLY if the camera exposes the
    focus_automatic_continuous control (used by some global-shutter trigger
    modules). Skipped with a clear message otherwise.
  - Headless verify or GUI preview to confirm settings

Exposure unit (UVC standard): exposure_time_absolute is in 100us units.
    value 1=0.1ms, 50=5ms, 100=10ms, 333=33.3ms (~30fps floor)

Requirements:
  sudo apt install v4l-utils          # required
  sudo apt install python3-opencv     # only for --preview (GUI)

Usage:
  python3 uvc_linux_control.py --status
  python3 uvc_linux_control.py --list-cameras
  python3 uvc_linux_control.py --exposure-ms 5 --gain 32
  python3 uvc_linux_control.py --auto-exposure
  python3 uvc_linux_control.py --mode stream            # if supported
  python3 uvc_linux_control.py --mode trigger           # if supported
  python3 uvc_linux_control.py --exposure-ms 5 --verify
  python3 uvc_linux_control.py -d /dev/video2 --status
  python3 uvc_linux_control.py --name "GC2053" --status
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import uvc_camera as uvc


def switch_mode(device, mode):
    """Optional stream/trigger switch via focus_automatic_continuous."""
    ctrl = uvc.find_control(device, uvc.CTRL_TRIGGER)
    if not ctrl:
        print("[Mode] this camera has no stream/trigger switch "
              "(focus_automatic_continuous) - skipping")
        return False
    if mode == "trigger":
        ae = uvc.find_control(device, uvc.CTRL_AUTO_EXPOSURE)
        if ae:
            uvc.set_control(device, ae, uvc.AE_MANUAL)
        ok = uvc.set_control(device, ctrl, 1)
        if ok:
            print(f"  [Mode] {ctrl}=1 -> TRIGGER (waiting for external pulse)")
    else:
        ok = uvc.set_control(device, ctrl, 0)
        if ok:
            print(f"  [Mode] {ctrl}=0 -> STREAM (free-running)")
    return ok


def show_status(device):
    print("=" * 64)
    print(f"  Camera Status: {device}  ({uvc._card_name(device)})")
    print("=" * 64)
    ctrl_trig = uvc.find_control(device, uvc.CTRL_TRIGGER)
    ctrl_ae = uvc.find_control(device, uvc.CTRL_AUTO_EXPOSURE)
    ctrl_exp = uvc.find_control(device, uvc.CTRL_EXPOSURE)
    ctrl_gain = uvc.find_control(device, uvc.CTRL_GAIN)

    if ctrl_trig:
        v = uvc.get_control(device, ctrl_trig)
        print(f"  {ctrl_trig} = {v}  "
              f"(continuous-AF on standard cameras; "
              f"stream/trigger switch only on modules that repurpose it)")
    if ctrl_ae:
        v = uvc.get_control(device, ctrl_ae)
        n = uvc.ctrl_int(v)
        # v may already carry a menu label, e.g. "1 (Manual Mode)"
        label = "" if "(" in (v or "") else \
            {uvc.AE_MANUAL: " (MANUAL)", uvc.AE_AUTO: " (AUTO)"}.get(n, "")
        print(f"  Exposure Mode:   {ctrl_ae} = {v}{label}")
    if ctrl_exp:
        v = uvc.get_control(device, ctrl_exp)
        n = uvc.ctrl_int(v)
        ms = f"{n/10.0:.1f} ms" if n is not None else "?"
        print(f"  Exposure Value:  {ctrl_exp} = {v} ({ms})")
    if ctrl_gain:
        print(f"  Gain:            {ctrl_gain} = {uvc.get_control(device, ctrl_gain)}")
    bm = uvc.best_mode(device)
    if bm:
        print(f"  Default mode:    {bm[0]} {bm[1]}x{bm[2]} @ {bm[3]:.0f}fps")
    print("\n  Full control list:")
    print("-" * 64)
    print(uvc.list_controls_raw(device))


def main():
    p = argparse.ArgumentParser(
        description="Generic UVC camera control (Linux)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-d", "--device", default=None, help="device (default: auto)")
    p.add_argument("--name", default=None, help="pick camera by name regex")
    p.add_argument("--list-cameras", action="store_true",
                   help="list all UVC cameras and exit")
    p.add_argument("--status", action="store_true", help="show status and exit")
    p.add_argument("--mode", choices=["stream", "trigger"], default=None)
    p.add_argument("--exposure", type=int, default=None,
                   help="exposure in UVC units (100us each)")
    p.add_argument("--exposure-ms", type=float, default=None,
                   help="exposure in milliseconds")
    p.add_argument("--auto-exposure", action="store_true")
    p.add_argument("--gain", type=int, default=None)
    p.add_argument("--verify", action="store_true",
                   help="headless capture self-test after applying")
    p.add_argument("--preview", action="store_true",
                   help="GUI preview after applying (needs opencv)")
    args = p.parse_args()

    if args.list_cameras:
        cams = uvc.list_uvc_cameras()
        if not cams:
            print("No UVC cameras found.")
            return
        for c in cams:
            print(f"  {c['node']}  [{c['name']}]  bus={c['bus']}")
        return

    device = uvc.pick_camera(args.device, args.name)
    if not device or not os.path.exists(device):
        print(f"[ERROR] no UVC camera found (device={device})")
        sys.exit(1)

    if args.status:
        show_status(device)
        return

    has_action = any([args.mode, args.exposure is not None,
                      args.exposure_ms is not None, args.auto_exposure,
                      args.gain is not None, args.verify, args.preview])
    if not has_action:
        show_status(device)
        return

    print("=" * 64)
    print(f"  Configuring {device}")
    print("=" * 64)

    if args.mode:
        switch_mode(device, args.mode)

    if args.auto_exposure:
        uvc.set_auto_exposure(device)
    else:
        exposure_uvc = args.exposure
        if exposure_uvc is None and args.exposure_ms is not None:
            exposure_uvc = int(round(args.exposure_ms * 10))
            print(f"  [Convert] {args.exposure_ms} ms -> UVC {exposure_uvc}")
        if exposure_uvc is not None:
            uvc.set_manual_exposure(device, exposure_uvc)

    if args.gain is not None:
        uvc.set_gain(device, args.gain)

    print("\n  Final state:")
    show_status(device)

    if args.verify:
        print()
        uvc.verify(device, frames=60)
    if args.preview:
        # Delegate to the generic preview tool
        import importlib.util
        prev = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "preview_linux.py")
        spec = importlib.util.spec_from_file_location("preview_linux", prev)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        bm = uvc.best_mode(device)
        if bm:
            mod.run_preview(device, bm[1], bm[2], int(bm[3]), bm[0])


if __name__ == "__main__":
    main()
