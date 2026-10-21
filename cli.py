"""
KeenScreen Studio Green Screen Remover & Compositor — VERSION 2.0 (High-Speed Turbo CLI & CMD Control Center)
Provides 100% Control & Settings Parity with the V2 Desktop GUI (`app_gui.py`):
  - Mode 1: Interactive CMD Control Center (Menu Dashboard) — launched when run with no arguments or `--menu`
  - Mode 2: Direct One-Line Command Flags — for scripting, automation, or quick terminal runs

What's New in Version 2.0 CLI:
  - V2 High-Speed Turbo Engine (Sparse Edge-Band Keying + Multi-Core Worker Pool + Fast Lossless FFmpeg)
  - Quick Output Format Preset Selector (`[F]`):
      1. Both `.MOV` + `.WEBM`
      2. Only `.MOV` (Camtasia Transparent RGBA)
      3. Only `.WEBM` (Web Transparent VP9 Alpha)
      4. Only `.WEBP` (Animated Transparent WebP)
      5. Only `.MP4` (Composited H.264)
  - Individual `[ON / OFF]` Toggles for `.MOV`, `.WEBM`, `.WEBP`, and `.MP4`
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from keyer_engine import (
    ENGINE_VERSION,
    KeyerConfig,
    StudioGreenScreenKeyer,
    VideoGreenProfile,
    discover_videos_in_folder,
    is_video_fully_completed,
    process_video_pipeline,
)

# Enable ANSI colors on Windows CMD
if os.name == "nt":
    os.system("")

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_DIM = "\033[90m"


def _badge_on_off(val: bool) -> str:
    return f"{C_GREEN}[ON ]{C_RESET}" if val else f"{C_DIM}[OFF]{C_RESET}"


def _clean_path_input(raw: str) -> str:
    s = raw.strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1].strip()
    return s


def _native_browse_file(title: str, filetypes: list[tuple[str, str]]) -> Optional[Path]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(title=title, filetypes=filetypes)
        root.destroy()
        if selected:
            return Path(selected).resolve()
    except Exception as exc:
        print(f"  {C_YELLOW}[!] Could not open file dialog ({exc}). Please paste the path directly.{C_RESET}")
    return None


def _native_browse_folder(title: str) -> Optional[Path]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title=title)
        root.destroy()
        if selected:
            return Path(selected).resolve()
    except Exception as exc:
        print(f"  {C_YELLOW}[!] Could not open folder dialog ({exc}). Please paste the path directly.{C_RESET}")
    return None


def _open_in_explorer(target: Path) -> None:
    folder = target if target.is_dir() else target.parent
    if not folder.exists():
        folder = Path(__file__).resolve().parent
    if os.name == "nt":
        os.startfile(str(folder))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(folder)], check=False)
    else:
        subprocess.run(["xdg-open", str(folder)], check=False)


def render_preview_frame_bgr(
    frame_bgr: np.ndarray,
    cfg: KeyerConfig,
    mode: str = "checker",
    bg_source: Optional[str] = None,
) -> tuple[np.ndarray, VideoGreenProfile]:
    keyer = StudioGreenScreenKeyer(config=cfg)
    prof = keyer.auto_calibrate_from_frame(frame_bgr)

    if mode == "original":
        return frame_bgr.copy(), prof

    rgba = keyer.process_frame(frame_bgr)
    h, w = frame_bgr.shape[:2]

    if mode == "checker":
        bg = keyer.make_checkerboard_bgr(h, w, 24)
    elif mode == "dark":
        bg = np.full_like(frame_bgr, 25)
    elif mode == "white":
        bg = np.full_like(frame_bgr, 245)
    else:
        bg = None
        bg_path = Path(bg_source) if bg_source else None
        if bg_path and bg_path.exists():
            if bg_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                bg = cv2.imread(str(bg_path), cv2.IMREAD_COLOR)
            else:
                bcap = cv2.VideoCapture(str(bg_path))
                ret, bframe = bcap.read()
                bcap.release()
                if ret:
                    bg = bframe
        if bg is None:
            bg = keyer.make_checkerboard_bgr(h, w, 24)

    vis_bgr = keyer.composite_rgba_over_bgr(rgba, bg)
    return vis_bgr, prof


def run_interactive_opencv_preview(
    video_path: Path,
    cfg: KeyerConfig,
    initial_mode: str = "checker",
    bg_source: Optional[str] = None,
    initial_frame: int = 0,
) -> None:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  {C_RED}[Error] Cannot open video for preview: {video_path}{C_RESET}")
        return

    total_frames = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    cur_frame_idx = [max(0, min(initial_frame, total_frames - 1))]
    cur_mode = [initial_mode]
    win_name = f"KeenScreen V2 Live Preview - {video_path.name} (Keys 1-5: BG Mode | ESC/Q: Close)"

    print(f"\n  {C_CYAN}Opening Interactive Preview Window...{C_RESET}")
    print("  Controls inside Preview Window:")
    print("    * Drag Trackbar : Scrub through video frames")
    print("    * Key [1]       : Checkerboard Background")
    print("    * Key [2]       : Dark Studio Background")
    print("    * Key [3]       : Pure White Background")
    print("    * Key [4]       : Original Green Screen")
    print("    * Key [5]       : Custom Background Image/Video")
    print("    * Key [Q / ESC] : Close Preview Window and return to CMD\n")

    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1120, 630)

    def _render_and_show() -> None:
        cap.set(cv2.CAP_PROP_POS_FRAMES, cur_frame_idx[0])
        ret, frame = cap.read()
        if not ret or frame is None:
            return
        vis, prof = render_preview_frame_bgr(frame, cfg, mode=cur_mode[0], bg_source=bg_source)
        overlay = vis.copy()
        info_txt = (
            f"Frame {cur_frame_idx[0]}/{total_frames-1} | Mode: {cur_mode[0].upper()} | "
            f"Green: {prof.bg_rgb_hex} (Floor: {prof.adapted_bg_floor if cfg.auto_adapt else cfg.bg_excess_floor:.1f}) | "
            f"Choke: {cfg.matte_choke_px:.2f}px | Despill: {cfg.despill_strength:.2f}"
        )
        cv2.putText(overlay, info_txt, (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(overlay, info_txt, (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (80, 255, 120), 2, cv2.LINE_AA)
        cv2.imshow(win_name, overlay)

    def _on_trackbar(pos: int) -> None:
        cur_frame_idx[0] = pos
        _render_and_show()

    cv2.createTrackbar("Frame", win_name, cur_frame_idx[0], max(1, total_frames - 1), _on_trackbar)
    _render_and_show()

    while True:
        if cv2.getWindowProperty(win_name, cv2.WND_PROP_VISIBLE) < 1:
            break
        key = cv2.waitKey(50) & 0xFF
        if key in (27, ord("q"), ord("Q")):
            break
        elif key == ord("1"):
            cur_mode[0] = "checker"
            _render_and_show()
        elif key == ord("2"):
            cur_mode[0] = "dark"
            _render_and_show()
        elif key == ord("3"):
            cur_mode[0] = "white"
            _render_and_show()
        elif key == ord("4"):
            cur_mode[0] = "original"
            _render_and_show()
        elif key == ord("5"):
            cur_mode[0] = "custom"
            _render_and_show()

    cap.release()
    cv2.destroyAllWindows()


def _print_progress(frame_idx: int, total_frames: int, elapsed: float) -> None:
    pct = (frame_idx / max(1, total_frames)) * 100.0
    fps = frame_idx / max(1e-3, elapsed)
    eta = max(0.0, (total_frames - frame_idx) / max(1e-3, fps))
    bar_len = 26
    filled = int(round(bar_len * frame_idx / max(1, total_frames)))
    bar = "#" * filled + "-" * (bar_len - filled)
    sys.stdout.write(
        f"\r  [{bar}] {frame_idx}/{total_frames} ({pct:5.1f}%) | {fps:4.1f} fps | ETA: {eta:4.1f}s "
    )
    sys.stdout.flush()
    if frame_idx >= total_frames:
        sys.stdout.write("\n")


def _print_profile(prof: VideoGreenProfile) -> None:
    b, g, r = prof.bg_bgr
    print(
        f"  [Auto-Calibrated Green] {prof.bg_rgb_hex} | RGB({int(r)}, {int(g)}, {int(b)}) "
        f"| Luma Y: {prof.bg_luma:.1f} | Excess: {prof.bg_excess:.1f} | Noise: +/-{prof.bg_std:.1f}"
    )
    print(
        f"  [Adapted Thresholds   ] BG Floor: {prof.adapted_bg_floor:.1f} "
        f"| FG Ceiling: {prof.adapted_fg_ceiling:.1f}"
    )


def process_single_file(
    video_path: Path,
    out_dir: Path | None = None,
    export_mov: bool = True,
    export_webm: bool = True,
    export_mp4: bool = False,
    export_webp: bool = False,
    bg_source: str | None = None,
    config: KeyerConfig | None = None,
    batch_index: int | None = None,
    batch_total: int | None = None,
    cancel_check: Optional[callable] = None,
) -> dict:
    target_dir = out_dir if out_dir is not None else video_path.parent
    stem = video_path.stem
    out_mov = (target_dir / f"{stem}_transparent.mov") if export_mov else None
    out_webm = (target_dir / f"{stem}_transparent.webm") if export_webm else None
    out_webp = (target_dir / f"{stem}_transparent.webp") if export_webp else None
    out_mp4 = (target_dir / f"{stem}_composited.mp4") if (export_mp4 or bg_source) else None

    prefix = f"[{batch_index}/{batch_total}] " if (batch_index and batch_total) else ""
    cfg = config or KeyerConfig()

    if cfg.skip_completed and is_video_fully_completed(
        video_path,
        export_mov=export_mov,
        export_webm=export_webm,
        export_mp4=bool(out_mp4),
        export_webp=export_webp,
        out_dir=target_dir,
    ):
        print(f"{C_GREEN}{prefix}SKIPPED (Selected Outputs Already Completed & Verified): {video_path.name}{C_RESET}")
        return {"skipped": True}

    print(f"\n{C_CYAN}======================================================================{C_RESET}")
    print(f"{C_BOLD}{prefix}V2 Turbo Processing : {video_path.name}{C_RESET}")
    print(f"  Source Folder   : {video_path.parent}")
    print(
        f"  Keyer Settings  : Auto-Adapt={'ON' if cfg.auto_adapt else 'OFF'} | "
        f"Choke={cfg.matte_choke_px:.2f}px | Floor={cfg.bg_excess_floor:.1f} | Despill={cfg.despill_strength:.2f}"
    )
    if out_mov:
        print(f"  -> Camtasia MOV : {out_mov.name} (Fast Lossless PNG RGBA + AAC Audio)")
    if out_webm:
        print(f"  -> Web VP9 WebM : {out_webm.name} (Fast VP9 yuva420p Alpha + Opus Audio)")
    if out_webp:
        print(f"  -> Anim WebP    : {out_webp.name} (Animated Transparent WebP)")
    if out_mp4:
        bg_desc = Path(bg_source).name if bg_source else "Studio Dark Gradient"
        print(f"  -> Composite MP4: {out_mp4.name} (Background: {bg_desc})")
    print(f"  {C_DIM}(Tip: Press Ctrl+C at any time to Stop Safely without losing completed videos){C_RESET}")

    results = process_video_pipeline(
        input_video=video_path,
        output_mov=out_mov,
        output_webm=out_webm,
        output_composite_mp4=out_mp4,
        output_webp=out_webp,
        background_source=bg_source,
        config=cfg,
        progress_callback=_print_progress,
        profile_callback=_print_profile,
        status_callback=lambda msg: print(f"\n  [Status] {msg}"),
        cancel_check=cancel_check,
    )

    print(f"  {C_GREEN}Saved in Folder :{C_RESET}")
    for fmt, path_str in results.items():
        p = Path(path_str)
        size_mb = p.stat().st_size / (1024 * 1024) if p.exists() else 0.0
        print(f"    [{fmt.upper():4s}] {p} ({size_mb:.2f} MB)")
    return results


class InteractiveCLISession:
    """
    Version 2.0 Interactive CMD Dashboard mirroring 100% of the V2 Desktop GUI (`app_gui.py`) controls.
    """

    def __init__(self) -> None:
        self.workspace_dir = Path(__file__).resolve().parent
        self.input_display: str = str(self.workspace_dir)
        self.recursive: bool = False
        self.skip_completed: bool = True

        self.export_mov: bool = True
        self.export_webm: bool = True
        self.export_webp: bool = False
        self.export_mp4: bool = False
        self.bg_source: Optional[str] = None
        self.custom_out_dir: Optional[Path] = None

        self.auto_adapt: bool = True
        self.matte_choke_px: float = 1.25
        self.bg_excess_floor: float = 44.0
        self.fg_excess_ceiling: float = 2.5
        self.despill_strength: float = 1.0
        self.edge_smoothness: float = 0.85
        self.alpha_power: float = 1.20

        self.preview_mode: str = "checker"
        self.preview_frame_idx: int = 0
        self.total_frames: int = 1

        self.video_queue: List[Path] = []
        self.active_video_idx: int = 0
        self.active_profile: Optional[VideoGreenProfile] = None

        vids = discover_videos_in_folder(self.workspace_dir, recursive=self.recursive)
        if vids:
            self._set_queue(vids, str(self.workspace_dir if len(vids) > 1 else vids[0]))

    def build_config(self) -> KeyerConfig:
        return KeyerConfig(
            auto_adapt=self.auto_adapt,
            fg_excess_ceiling=self.fg_excess_ceiling,
            bg_excess_floor=self.bg_excess_floor,
            matte_choke_px=self.matte_choke_px,
            edge_smoothness=self.edge_smoothness,
            alpha_power=self.alpha_power,
            despill_strength=self.despill_strength,
            skip_completed=self.skip_completed,
            max_retries=3,
        )

    @property
    def active_video(self) -> Optional[Path]:
        if 0 <= self.active_video_idx < len(self.video_queue):
            return self.video_queue[self.active_video_idx]
        return None

    def _set_queue(self, videos: List[Path], display_path: str) -> None:
        self.input_display = display_path
        self.video_queue = videos
        self.active_video_idx = 0
        if videos:
            self._calibrate_active_video()
        else:
            self.active_profile = None
            self.total_frames = 1
            self.preview_frame_idx = 0

    def _calibrate_active_video(self) -> None:
        v = self.active_video
        if v is None or not v.exists():
            self.active_profile = None
            return
        cap = cv2.VideoCapture(str(v))
        if not cap.isOpened():
            self.active_profile = None
            return
        self.total_frames = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        self.preview_frame_idx = min(60, self.total_frames // 2)
        cap.set(cv2.CAP_PROP_POS_FRAMES, self.preview_frame_idx)
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            keyer = StudioGreenScreenKeyer(self.build_config())
            self.active_profile = keyer.auto_calibrate_from_frame(frame)
            if self.auto_adapt and self.active_profile is not None:
                self.bg_excess_floor = round(self.active_profile.adapted_bg_floor, 1)

    def _queue_counts(self) -> tuple[int, int, int]:
        total = len(self.video_queue)
        done_c = 0
        for v in self.video_queue:
            if is_video_fully_completed(
                v,
                export_mov=self.export_mov,
                export_webm=self.export_webm,
                export_mp4=self.export_mp4 or bool(self.bg_source),
                export_webp=self.export_webp,
                out_dir=self.custom_out_dir,
            ):
                done_c += 1
        return total, done_c, total - done_c

    def _active_formats_summary(self) -> str:
        fmts = []
        if self.export_mov:
            fmts.append(".MOV")
        if self.export_webm:
            fmts.append(".WEBM")
        if self.export_webp:
            fmts.append(".WEBP")
        if self.export_mp4 or self.bg_source:
            fmts.append(".MP4")
        return " + ".join(fmts) if fmts else "NONE"

    def _render_dashboard(self) -> None:
        total, done_c, pend_c = self._queue_counts()
        act_v = self.active_video
        act_name = act_v.name if act_v else "None selected"

        if self.active_profile is not None:
            p = self.active_profile
            b, g, r = int(p.bg_bgr[0]), int(p.bg_bgr[1]), int(p.bg_bgr[2])
            floor_lbl = f"Auto Floor: {p.adapted_bg_floor:.1f}" if self.auto_adapt else f"Manual Floor: {self.bg_excess_floor:.1f}"
            prof_str = (
                f"{C_GREEN}{p.bg_rgb_hex}{C_RESET} RGB({r},{g},{b}) | "
                f"Luma: {p.bg_luma:.1f} | {floor_lbl} | Choke: {self.matte_choke_px:.2f}px"
            )
        else:
            prof_str = f"{C_DIM}Waiting for video...{C_RESET}"

        out_dir_str = str(self.custom_out_dir) if self.custom_out_dir else "Same Folder as Each Source Video (In-Place)"
        bg_str = self.bg_source if self.bg_source else "None (Transparent / Dark Studio Gradient)"

        print(f"\n{C_CYAN}======================================================================================{C_RESET}")
        print(f"{C_BOLD}   KEENSCREEN STUDIO V2 ({ENGINE_VERSION}) - INTERACTIVE CMD CONTROL CENTER{C_RESET}")
        print(f"{C_CYAN}======================================================================================{C_RESET}")
        print(f" {C_BOLD}1. Input & Bulk Queue Controls{C_RESET}")
        print(f"    [1] Select Single Video Path / Browse  : {C_YELLOW}{self.input_display}{C_RESET}")
        print(f"    [2] Select Bulk Folder Path / Browse   : ({total} video(s) queued | {C_GREEN}{done_c} DONE{C_RESET}, {C_YELLOW}{pend_c} PENDING{C_RESET})")
        print(f"    [3] Include Subfolders (Recursive)     : {_badge_on_off(self.recursive)}")
        print(f"    [4] Smart Resume (Skip Completed)      : {_badge_on_off(self.skip_completed)}")
        print(f"    [5] Inspect / Switch Queued Video      : Active -> {C_CYAN}{act_name}{C_RESET} (Frame {self.preview_frame_idx}/{self.total_frames})")
        print(f" {C_BOLD}2. Select Output Format(s) — Active: [{C_GREEN}{self._active_formats_summary()}{C_RESET}{C_BOLD}] ({out_dir_str}){C_RESET}")
        print(f"    [F] Quick Format Preset Selector       : Choose [Only .MOV | Only .WEBM | Only .WEBP | Both | Only .MP4]")
        print(f"    [6] Transparent .MOV (Camtasia RGBA)   : {_badge_on_off(self.export_mov)}")
        print(f"    [7] Transparent .WEBM (Web VP9 Alpha)  : {_badge_on_off(self.export_webm)}")
        print(f"    [W] Transparent .WEBP (Animated WebP)  : {_badge_on_off(self.export_webp)}")
        print(f"    [8] Composited .MP4 (H.264)            : {_badge_on_off(self.export_mp4)}")
        print(f" {C_BOLD}3. Optional Background Image / Video{C_RESET}")
        print(f"    [9] Set / Browse / Clear Custom BG     : {bg_str}")
        print(f" {C_BOLD}4. Per-Video Adaptive Green & Outline Choke{C_RESET}")
        print(f"    Calibrated Green Profile               : {prof_str}")
        print(f"   [10] Auto-Adapt to Video's Green Colour : {_badge_on_off(self.auto_adapt)}")
        print(f"   [11] Outline Choke (0.0 - 2.5px)        : {C_YELLOW}{self.matte_choke_px:.2f} px{C_RESET} (Default: 1.25px)")
        print(f"   [12] Background Green Floor (20 - 90)   : {C_YELLOW}{self.bg_excess_floor:.1f}{C_RESET} {'(Auto-Scaled per video)' if self.auto_adapt else '(Manual Fixed)'}")
        print(f"   [13] Green Spill Suppression (0.0 - 1.0): {C_YELLOW}{self.despill_strength:.2f}{C_RESET} (Default: 1.00)")
        print(f"   [14] Advanced Matte & Output Folder     : FG Ceil={self.fg_excess_ceiling:.1f} | Smooth={self.edge_smoothness:.2f} | Power={self.alpha_power:.2f}")
        print(f" {C_BOLD}5. Preview, Scrub & Execution Actions{C_RESET}")
        print(f"    [P] Live Matte Preview & Frame Scrub   : Mode={C_CYAN}{self.preview_mode.upper()}{C_RESET} (Checker/Dark/White/Original/Custom)")
        print(f"    [S] {C_GREEN}{C_BOLD}START / RESUME TURBO PROCESSING{C_RESET}    : Process {total} queued video(s) (Ctrl+C = Stop Safely)")
        print(f"    [O] Open Video Folder in Explorer      [Q] Quit")
        print(f"{C_CYAN}--------------------------------------------------------------------------------------{C_RESET}")

    def run_loop(self) -> int:
        while True:
            self._render_dashboard()
            try:
                choice = input(f" {C_BOLD}Select option [1-14, F, W, P, S, O, Q]: {C_RESET}").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting KeenScreen CLI.")
                return 0

            if choice in ("Q", "EXIT", "QUIT"):
                print("Goodbye!")
                return 0
            elif choice == "1":
                self._handle_select_single_video()
            elif choice == "2":
                self._handle_select_folder()
            elif choice == "3":
                self.recursive = not self.recursive
                curr = Path(self.input_display)
                if curr.exists() and curr.is_dir():
                    vids = discover_videos_in_folder(curr, recursive=self.recursive)
                    self._set_queue(vids, str(curr))
            elif choice == "4":
                self.skip_completed = not self.skip_completed
            elif choice == "5":
                self._handle_inspect_queue()
            elif choice == "F":
                self._handle_quick_format_preset()
            elif choice == "6":
                self.export_mov = not self.export_mov
            elif choice == "7":
                self.export_webm = not self.export_webm
            elif choice == "W":
                self.export_webp = not self.export_webp
            elif choice == "8":
                self.export_mp4 = not self.export_mp4
            elif choice == "9":
                self._handle_set_background()
            elif choice == "10":
                self.auto_adapt = not self.auto_adapt
                if self.auto_adapt and self.active_profile is not None:
                    self.bg_excess_floor = round(self.active_profile.adapted_bg_floor, 1)
            elif choice == "11":
                self._handle_float_setting(
                    "Outline Choke (px)", "matte_choke_px", 0.0, 2.5, 1.25
                )
            elif choice == "12":
                self._handle_float_setting(
                    "Background Green Floor", "bg_excess_floor", 20.0, 90.0, 44.0
                )
            elif choice == "13":
                self._handle_float_setting(
                    "Green Spill Suppression Strength", "despill_strength", 0.0, 1.0, 1.0
                )
            elif choice == "14":
                self._handle_advanced_settings()
            elif choice == "P":
                self._handle_preview_menu()
            elif choice == "S":
                self._handle_start_batch()
            elif choice == "O":
                target = self.active_video if self.active_video else Path(self.input_display)
                _open_in_explorer(target)
                print(f"  {C_GREEN}Opened folder in Windows Explorer.{C_RESET}")
            else:
                print(f"  {C_YELLOW}Unrecognized option '{choice}'. Please choose from [1-14, F, W, P, S, O, Q].{C_RESET}")

    def _handle_quick_format_preset(self) -> None:
        print(f"\n  {C_BOLD}Quick Output Format Presets:{C_RESET}")
        print("    [1] Both .MOV + .WEBM (Camtasia + Web)")
        print("    [2] Only .MOV         (Fastest for Camtasia Transparent RGBA)")
        print("    [3] Only .WEBM        (Fastest for Web VP9 Alpha)")
        print("    [4] Only .WEBP        (Animated Transparent WebP)")
        print("    [5] Only .MP4         (Composited H.264 Over Custom/Studio Background)")
        print("    [6] All (.MOV + .WEBM + .MP4)")
        p = input("  Choose preset [1-6] (or Enter to cancel): ").strip()
        if p == "1":
            self.export_mov, self.export_webm, self.export_webp, self.export_mp4 = True, True, False, False
        elif p == "2":
            self.export_mov, self.export_webm, self.export_webp, self.export_mp4 = True, False, False, False
        elif p == "3":
            self.export_mov, self.export_webm, self.export_webp, self.export_mp4 = False, True, False, False
        elif p == "4":
            self.export_mov, self.export_webm, self.export_webp, self.export_mp4 = False, False, True, False
        elif p == "5":
            self.export_mov, self.export_webm, self.export_webp, self.export_mp4 = False, False, False, True
        elif p == "6":
            self.export_mov, self.export_webm, self.export_webp, self.export_mp4 = True, True, False, True

    def _handle_select_single_video(self) -> None:
        raw = input(
            "  Paste/drag video path (or type 'B' to open Windows File Browse dialog, Enter to cancel): "
        ).strip()
        if not raw:
            return
        if raw.upper() == "B":
            p = _native_browse_file(
                "Select Green Screen Video",
                [("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All Files", "*.*")],
            )
        else:
            p = Path(_clean_path_input(raw)).resolve()

        if p and p.exists() and p.is_file():
            self._set_queue([p], str(p))
            print(f"  {C_GREEN}Loaded single video: {p.name}{C_RESET}")
        else:
            print(f"  {C_RED}[Error] Valid video file not found: {p}{C_RESET}")

    def _handle_select_folder(self) -> None:
        raw = input(
            "  Paste/drag folder path (or type 'B' to open Windows Folder Browse dialog, Enter to cancel): "
        ).strip()
        if not raw:
            return
        if raw.upper() == "B":
            f_path = _native_browse_folder("Select Folder Containing Green Screen Videos (Bulk Upload)")
        else:
            f_path = Path(_clean_path_input(raw)).resolve()

        if f_path and f_path.exists() and f_path.is_dir():
            vids = discover_videos_in_folder(f_path, recursive=self.recursive)
            self._set_queue(vids, str(f_path))
            print(f"  {C_GREEN}Loaded folder '{f_path}' -> Found {len(vids)} source video(s).{C_RESET}")
        else:
            print(f"  {C_RED}[Error] Valid folder not found: {f_path}{C_RESET}")

    def _handle_inspect_queue(self) -> None:
        if not self.video_queue:
            print(f"  {C_YELLOW}Queue is currently empty. Use [1] or [2] to load videos.{C_RESET}")
            return
        print(f"\n  {C_BOLD}Queued Videos ({len(self.video_queue)}):{C_RESET}")
        for idx, v in enumerate(self.video_queue, start=1):
            done = is_video_fully_completed(
                v,
                export_mov=self.export_mov,
                export_webm=self.export_webm,
                export_mp4=self.export_mp4 or bool(self.bg_source),
                export_webp=self.export_webp,
                out_dir=self.custom_out_dir,
            )
            badge = f"{C_GREEN}[DONE]   {C_RESET}" if done else f"{C_YELLOW}[PENDING]{C_RESET}"
            marker = f"{C_CYAN}*{C_RESET}" if (idx - 1) == self.active_video_idx else " "
            print(f"   {marker} {idx:2d}. {badge} {v.name}  ({v.parent})")

        sel = input(f"\n  Enter video number (1-{len(self.video_queue)}) to make active for preview/calibration (Enter to keep current): ").strip()
        if sel.isdigit():
            n = int(sel) - 1
            if 0 <= n < len(self.video_queue):
                self.active_video_idx = n
                self._calibrate_active_video()
                print(f"  {C_GREEN}Active video set to: {self.video_queue[n].name}{C_RESET}")

    def _handle_set_background(self) -> None:
        raw = input(
            "  Paste/drag background image/video path ('B' to browse, 'C' to clear, Enter to cancel): "
        ).strip()
        if not raw:
            return
        if raw.upper() == "C":
            self.bg_source = None
            if self.preview_mode == "custom":
                self.preview_mode = "checker"
            print(f"  {C_GREEN}Cleared custom background.{C_RESET}")
            return
        if raw.upper() == "B":
            p = _native_browse_file(
                "Select Static Image or Dynamic Background Video",
                [("Media Files", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.webm"), ("All Files", "*.*")],
            )
        else:
            p = Path(_clean_path_input(raw)).resolve()

        if p and p.exists() and p.is_file():
            self.bg_source = str(p)
            self.export_mp4 = True
            self.preview_mode = "custom"
            print(f"  {C_GREEN}Set custom background: {p.name} (Composited .MP4 enabled){C_RESET}")
        else:
            print(f"  {C_RED}[Error] File not found: {p}{C_RESET}")

    def _handle_float_setting(
        self, label: str, attr: str, min_v: float, max_v: float, default_v: float
    ) -> None:
        curr_v = getattr(self, attr)
        raw = input(
            f"  Enter {label} [{min_v} - {max_v}] (Current: {curr_v}, 'D' for default {default_v}): "
        ).strip()
        if not raw:
            return
        if raw.upper() == "D":
            setattr(self, attr, default_v)
            return
        try:
            val = float(raw)
            val = max(min_v, min(max_v, val))
            setattr(self, attr, val)
            if attr == "bg_excess_floor":
                self.auto_adapt = False
        except ValueError:
            print(f"  {C_RED}[Error] Invalid number '{raw}'.{C_RESET}")

    def _handle_advanced_settings(self) -> None:
        print(f"\n  {C_BOLD}Advanced Matte & Output Folder Settings:{C_RESET}")
        print(f"    [1] Foreground Solid Ceiling (0.0 - 15.0) : {self.fg_excess_ceiling:.2f} (Default: 2.50)")
        print(f"    [2] Edge Smoothness (0.0 - 2.0)           : {self.edge_smoothness:.2f} (Default: 0.85)")
        print(f"    [3] Alpha Curve Power (0.5 - 2.5)         : {self.alpha_power:.2f} (Default: 1.20)")
        print(f"    [4] Custom Output Folder                  : {self.custom_out_dir or 'Same Folder as Video (In-Place)'}")
        sub = input("  Select [1-4] (or Enter to return): ").strip()
        if sub == "1":
            self._handle_float_setting("Foreground Solid Ceiling", "fg_excess_ceiling", 0.0, 15.0, 2.5)
        elif sub == "2":
            self._handle_float_setting("Edge Smoothness", "edge_smoothness", 0.0, 2.0, 0.85)
        elif sub == "3":
            self._handle_float_setting("Alpha Curve Power", "alpha_power", 0.5, 2.5, 1.20)
        elif sub == "4":
            raw = input("  Enter custom output folder ('C' to reset to In-Place same folder, 'B' to browse): ").strip()
            if raw.upper() == "C":
                self.custom_out_dir = None
            elif raw.upper() == "B":
                p = _native_browse_folder("Select Custom Output Folder")
                if p:
                    self.custom_out_dir = p
            elif raw:
                p = Path(_clean_path_input(raw)).resolve()
                p.mkdir(parents=True, exist_ok=True)
                self.custom_out_dir = p

    def _handle_preview_menu(self) -> None:
        v = self.active_video
        if v is None or not v.exists():
            print(f"  {C_YELLOW}No active video loaded to preview. Select a video first.{C_RESET}")
            return

        print(f"\n  {C_BOLD}Live Zero-Outline Matte Preview ({v.name}):{C_RESET}")
        print(f"    [1] Open Interactive Scrub & Preview Window (Real-Time Trackbar + Keys 1-5 BG Modes)")
        print(f"    [2] Change Preview Background Mode (Current: {self.preview_mode.upper()})")
        print(f"    [3] Scrub / Set Frame Number (Current: {self.preview_frame_idx} / {self.total_frames - 1})")
        print(f"    [4] Save & Open Snapshot Preview PNG of Current Frame")
        sub = input("  Select preview action [1-4] (or Enter to return): ").strip()

        if sub == "1":
            run_interactive_opencv_preview(
                v,
                self.build_config(),
                initial_mode=self.preview_mode,
                bg_source=self.bg_source,
                initial_frame=self.preview_frame_idx,
            )
        elif sub == "2":
            print("    Modes: [1] Checkerboard  [2] Dark Studio  [3] Pure White  [4] Original Green  [5] Custom BG")
            m = input("    Choose mode [1-5]: ").strip()
            mode_map = {"1": "checker", "2": "dark", "3": "white", "4": "original", "5": "custom"}
            if m in mode_map:
                self.preview_mode = mode_map[m]
        elif sub == "3":
            raw_f = input(f"    Enter frame index [0 - {max(0, self.total_frames - 1)}]: ").strip()
            if raw_f.isdigit():
                self.preview_frame_idx = max(0, min(self.total_frames - 1, int(raw_f)))
        elif sub == "4":
            cap = cv2.VideoCapture(str(v))
            cap.set(cv2.CAP_PROP_POS_FRAMES, self.preview_frame_idx)
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                vis, _ = render_preview_frame_bgr(
                    frame, self.build_config(), mode=self.preview_mode, bg_source=self.bg_source
                )
                out_png = v.parent / f"{v.stem}_preview_f{self.preview_frame_idx}_{self.preview_mode}.png"
                cv2.imwrite(str(out_png), vis)
                print(f"  {C_GREEN}Saved preview snapshot: {out_png}{C_RESET}")
                if os.name == "nt":
                    os.startfile(str(out_png))

    def _handle_start_batch(self) -> None:
        if not self.video_queue:
            print(f"  {C_RED}[Error] No videos in queue. Please select a video or folder first.{C_RESET}")
            return
        if not (self.export_mov or self.export_webm or self.export_webp or self.export_mp4 or self.bg_source):
            print(f"  {C_RED}[Error] Please enable at least one output format (.MOV, .WEBM, .WEBP, or .MP4).{C_RESET}")
            return

        cfg = self.build_config()
        total = len(self.video_queue)
        processed_count = 0
        skipped_count = 0
        failed_list: List[str] = []
        stop_requested = [False]

        print(f"\n{C_GREEN}{C_BOLD}>>> Starting V2 Turbo Batch Processing ({total} video(s) | Outputs: {self._active_formats_summary()})...{C_RESET}")
        print(f"    Press {C_YELLOW}Ctrl+C{C_RESET} at any time to Stop Safely (preserves all completed videos).\n")

        for idx, v in enumerate(self.video_queue, start=1):
            if stop_requested[0]:
                break
            try:
                res = process_single_file(
                    video_path=v,
                    out_dir=self.custom_out_dir,
                    export_mov=self.export_mov,
                    export_webm=self.export_webm,
                    export_mp4=self.export_mp4,
                    export_webp=self.export_webp,
                    bg_source=self.bg_source,
                    config=cfg,
                    batch_index=idx,
                    batch_total=total,
                    cancel_check=lambda: stop_requested[0],
                )
                if res.get("skipped"):
                    skipped_count += 1
                else:
                    processed_count += 1
            except KeyboardInterrupt:
                stop_requested[0] = True
                print(f"\n  {C_YELLOW}[Stop Safely] Interrupt received! Cleaned up temporary files for '{v.name}'.{C_RESET}")
                break
            except Exception as exc:
                if "stopped safely" in str(exc).lower() or "cancelled safely" in str(exc).lower():
                    stop_requested[0] = True
                    print(f"\n  {C_YELLOW}[Stop Safely] Stopped cleanly. Completed videos are preserved.{C_RESET}")
                    break
                failed_list.append(f"{v.name}: {exc}")
                print(f"\n  {C_RED}[Error] Failed on '{v.name}': {exc}{C_RESET}")

        print(f"\n{C_CYAN}======================================================================{C_RESET}")
        if stop_requested[0]:
            print(
                f"  {C_YELLOW}Stopped Safely.{C_RESET} Newly Processed: {processed_count} | "
                f"Skipped (Already Done): {skipped_count}"
            )
        else:
            print(
                f"  {C_GREEN}{C_BOLD}V2 Turbo Batch Complete!{C_RESET} Newly Processed: {processed_count} | "
                f"Skipped (Already Done): {skipped_count} | Failed: {len(failed_list)}"
            )
        print(f"{C_CYAN}======================================================================{C_RESET}")
        input("\n  Press Enter to return to the CMD Control Center...")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"KeenScreen Studio V2 ({ENGINE_VERSION}) — Interactive CMD & Direct CLI"
    )
    parser.add_argument(
        "input_pos",
        nargs="?",
        default=None,
        help="Optional path to a green screen video (.mp4) OR a folder of videos",
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_flag",
        default=None,
        help="Path to a green screen video (.mp4) OR a folder of videos for bulk processing",
    )
    parser.add_argument(
        "-m",
        "--menu",
        "--interactive",
        dest="interactive",
        action="store_true",
        help="Launch the Interactive CMD Control Center dashboard",
    )
    parser.add_argument(
        "--format",
        choices=["both", "mov", "webm", "webp", "mp4", "all"],
        default=None,
        help="Quick format selector: 'both' (.mov+.webm), 'mov' (only .mov), 'webm' (only .webm), 'webp' (only .webp), 'mp4' (only .mp4), or 'all'",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Optional custom output directory (defaults to saving in the same folder as each input video)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When input is a folder, scan subfolders recursively",
    )
    parser.add_argument(
        "--skip-completed",
        dest="skip_completed",
        action="store_true",
        default=True,
        help="Smart Resume: skip videos whose requested outputs already exist and are valid (default: True)",
    )
    parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Re-process and overwrite videos even if valid outputs already exist",
    )
    parser.add_argument(
        "--mov",
        dest="export_mov",
        action="store_true",
        default=True,
        help="Export transparent .mov (Camtasia QuickTime PNG RGBA, default: True)",
    )
    parser.add_argument(
        "--no-mov",
        dest="export_mov",
        action="store_false",
        help="Disable exporting transparent .mov",
    )
    parser.add_argument(
        "--webm",
        dest="export_webm",
        action="store_true",
        default=True,
        help="Export transparent .webm (Web VP9 Alpha, default: True)",
    )
    parser.add_argument(
        "--no-webm",
        dest="export_webm",
        action="store_false",
        help="Disable exporting transparent .webm",
    )
    parser.add_argument(
        "--webp",
        dest="export_webp",
        action="store_true",
        default=False,
        help="Export animated transparent .webp",
    )
    parser.add_argument(
        "--mp4",
        "--composite",
        dest="export_mp4",
        action="store_true",
        default=False,
        help="Also export a composited .mp4 video (over --bg or studio dark gradient)",
    )
    parser.add_argument(
        "--no-mp4",
        dest="export_mp4",
        action="store_false",
        help="Disable exporting composited .mp4",
    )
    parser.add_argument(
        "--bg",
        default=None,
        help="Optional static image (.png/.jpg) or dynamic video (.mp4) background for .mp4 compositing / preview",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all source videos in the input folder",
    )
    parser.add_argument(
        "--auto-adapt",
        dest="auto_adapt",
        action="store_true",
        default=True,
        help="Auto-adapt thresholds to each video's specific green screen colour (default: True)",
    )
    parser.add_argument(
        "--no-auto-adapt",
        dest="auto_adapt",
        action="store_false",
        help="Disable auto-adaptation and use fixed --bg-floor",
    )
    parser.add_argument(
        "--choke",
        type=float,
        default=1.25,
        help="Outline Choke in pixels (0.0 - 2.5, cuts thin green border, default: 1.25)",
    )
    parser.add_argument(
        "--bg-floor",
        "--manual-floor",
        dest="bg_floor",
        type=float,
        default=None,
        help="Background Green Floor (20.0 - 90.0, default: 44.0 or auto-scaled per video)",
    )
    parser.add_argument(
        "--fg-ceiling",
        type=float,
        default=2.5,
        help="Foreground Solid Ceiling (0.0 - 15.0, default: 2.5)",
    )
    parser.add_argument(
        "--despill",
        type=float,
        default=1.0,
        help="Green spill suppression strength 0.0 - 1.0 (default: 1.0)",
    )
    parser.add_argument(
        "--edge-smoothness",
        type=float,
        default=0.85,
        help="Edge anti-aliasing smoothness (default: 0.85)",
    )
    parser.add_argument(
        "--alpha-power",
        type=float,
        default=1.20,
        help="Alpha curve roll-off power (default: 1.20)",
    )
    parser.add_argument(
        "--list-queue",
        action="store_true",
        help="Inspect and list all discovered videos with [DONE] / [PENDING] status badges and exit",
    )
    parser.add_argument(
        "--preview-frame",
        type=int,
        default=None,
        help="Render a preview snapshot at frame N (or open interactive preview with --interactive-preview)",
    )
    parser.add_argument(
        "--preview-mode",
        choices=["checker", "dark", "white", "original", "custom"],
        default="checker",
        help="Preview background mode (checker, dark, white, original, custom)",
    )
    parser.add_argument(
        "--preview-out",
        default=None,
        help="Optional output PNG path when using --preview-frame",
    )
    parser.add_argument(
        "--interactive-preview",
        action="store_true",
        help="Open the interactive OpenCV frame scrub & preview window for the input video",
    )
    parser.add_argument(
        "--open-folder",
        action="store_true",
        help="Open the video/output folder in Windows Explorer after completion",
    )
    return parser


def main() -> int:
    if len(sys.argv) == 1:
        session = InteractiveCLISession()
        return session.run_loop()

    parser = build_arg_parser()
    args = parser.parse_args()

    if args.interactive:
        session = InteractiveCLISession()
        raw_in = args.input_flag or args.input_pos
        if raw_in:
            p = Path(_clean_path_input(raw_in)).resolve()
            if p.exists():
                vids = discover_videos_in_folder(p, recursive=args.recursive) if p.is_dir() else [p]
                session._set_queue(vids, str(p))
        return session.run_loop()

    raw_input = args.input_flag or args.input_pos or "."
    input_path = Path(_clean_path_input(raw_input)).resolve()

    if not input_path.exists():
        print(f"{C_RED}Error: Input path does not exist: {input_path}{C_RESET}", file=sys.stderr)
        return 1

    auto_adapt = args.auto_adapt and (args.bg_floor is None)
    cfg = KeyerConfig(
        auto_adapt=auto_adapt,
        fg_excess_ceiling=args.fg_ceiling,
        bg_excess_floor=args.bg_floor if args.bg_floor is not None else 44.0,
        matte_choke_px=args.choke,
        edge_smoothness=args.edge_smoothness,
        alpha_power=args.alpha_power,
        despill_strength=args.despill,
        skip_completed=(not args.force_overwrite),
        max_retries=3,
    )

    export_mov = args.export_mov
    export_webm = args.export_webm
    export_webp = args.export_webp
    export_mp4 = args.export_mp4 or (args.bg is not None)

    if args.format == "both":
        export_mov, export_webm, export_webp = True, True, False
    elif args.format == "mov":
        export_mov, export_webm, export_webp, export_mp4 = True, False, False, False
    elif args.format == "webm":
        export_mov, export_webm, export_webp, export_mp4 = False, True, False, False
    elif args.format == "webp":
        export_mov, export_webm, export_webp, export_mp4 = False, False, True, False
    elif args.format == "mp4":
        export_mov, export_webm, export_webp, export_mp4 = False, False, False, True
    elif args.format == "all":
        export_mov, export_webm, export_mp4 = True, True, True

    custom_out_dir = Path(_clean_path_input(args.out_dir)).resolve() if args.out_dir else None

    if args.batch or input_path.is_dir():
        folder = input_path if input_path.is_dir() else input_path.parent
        videos: List[Path] = discover_videos_in_folder(folder, recursive=args.recursive)
    else:
        videos = [input_path]

    if not videos:
        print(f"{C_YELLOW}No source video files found in: {input_path}{C_RESET}")
        return 1

    if args.list_queue:
        done_c = 0
        print(f"\n{C_BOLD}Queue Status for '{input_path}' ({len(videos)} video(s)):{C_RESET}")
        for idx, v in enumerate(videos, start=1):
            done = is_video_fully_completed(
                v,
                export_mov=export_mov,
                export_webm=export_webm,
                export_mp4=export_mp4,
                export_webp=export_webp,
                out_dir=custom_out_dir,
            )
            if done:
                done_c += 1
            badge = f"{C_GREEN}[DONE]   {C_RESET}" if done else f"{C_YELLOW}[PENDING]{C_RESET}"
            print(f"  {idx:2d}. {badge} {v.name}  ({v.parent})")
        print(f"\nSummary: {len(videos)} total | {done_c} Done | {len(videos) - done_c} Pending")
        return 0

    if args.interactive_preview:
        run_interactive_opencv_preview(
            videos[0],
            cfg,
            initial_mode=args.preview_mode,
            bg_source=args.bg,
            initial_frame=args.preview_frame if args.preview_frame is not None else 0,
        )
        return 0

    if args.preview_frame is not None:
        v = videos[0]
        cap = cv2.VideoCapture(str(v))
        total_f = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        f_idx = max(0, min(total_f - 1, args.preview_frame))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            print(f"{C_RED}Error: Could not read frame {f_idx} from {v}{C_RESET}", file=sys.stderr)
            return 1
        vis, prof = render_preview_frame_bgr(frame, cfg, mode=args.preview_mode, bg_source=args.bg)
        out_png = (
            Path(_clean_path_input(args.preview_out)).resolve()
            if args.preview_out
            else (v.parent / f"{v.stem}_preview_f{f_idx}_{args.preview_mode}.png")
        )
        cv2.imwrite(str(out_png), vis)
        _print_profile(prof)
        print(f"{C_GREEN}Saved preview frame {f_idx} ({args.preview_mode}) to: {out_png}{C_RESET}")
        return 0

    stop_requested = [False]
    if len(videos) > 1:
        print(f"{C_CYAN}V2 Turbo Bulk Folder Mode: Found {len(videos)} source video(s) in '{input_path}'{C_RESET}")

    for idx, v in enumerate(videos, start=1):
        try:
            process_single_file(
                v,
                out_dir=custom_out_dir,
                export_mov=export_mov,
                export_webm=export_webm,
                export_mp4=export_mp4,
                export_webp=export_webp,
                bg_source=args.bg,
                config=cfg,
                batch_index=idx if len(videos) > 1 else None,
                batch_total=len(videos) if len(videos) > 1 else None,
                cancel_check=lambda: stop_requested[0],
            )
        except KeyboardInterrupt:
            stop_requested[0] = True
            print(f"\n{C_YELLOW}[Stop Safely] Interrupted by user (Ctrl+C). Cleaned up partial files; completed videos are preserved.{C_RESET}")
            return 130

    if len(videos) > 1:
        print(f"\n{C_GREEN}{C_BOLD}V2 Turbo Bulk processing complete! All {len(videos)} video(s) verified in their respective folders.{C_RESET}")

    if args.open_folder:
        _open_in_explorer(custom_out_dir if custom_out_dir else videos[0])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
