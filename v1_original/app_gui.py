"""
Automatic Green Screen Remover & Compositor — Desktop GUI Application
Includes:
  - Bulk Folder Upload & In-Place Output Saving
  - Smart Resume (Automatically skips already-completed valid outputs so zero resources are wasted)
  - Sub-Pixel Matte Choke & Outward Interior Color Propagation (Zero Green Screen Outline, Buttery-Smooth Edges)
  - 100% Silent Background Subprocesses (Zero Terminal / Console Popups)
  - Per-Video Adaptive Green Screen Calibration
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image, ImageTk

from keyer_engine import (
    KeyerConfig,
    StudioGreenScreenKeyer,
    VideoGreenProfile,
    discover_videos_in_folder,
    is_video_fully_completed,
    process_video_pipeline,
)


class GreenScreenApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Studio Green Screen Remover — Zero-Outline + Smart Resume + Bulk Folder")
        self.geometry("1260x850")
        self.minsize(1080, 770)
        self.configure(bg="#141820")

        self.input_path_var = tk.StringVar()
        self.bg_source_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=False)
        self.skip_completed_var = tk.BooleanVar(value=True)

        self.export_mov_var = tk.BooleanVar(value=True)
        self.export_webm_var = tk.BooleanVar(value=True)
        self.export_mp4_var = tk.BooleanVar(value=False)

        self.auto_adapt_var = tk.BooleanVar(value=True)
        self.preview_mode_var = tk.StringVar(value="checker")
        self.bg_floor_var = tk.DoubleVar(value=44.0)
        self.choke_var = tk.DoubleVar(value=1.25)
        self.despill_var = tk.DoubleVar(value=1.0)
        self.frame_slider_var = tk.IntVar(value=0)
        self.profile_info_var = tk.StringVar(value="Auto-Calibrated Green: Waiting for video...")
        self.status_var = tk.StringVar(
            value="Ready. Zero-Outline Choke + Smart Resume ON (100% silent background processing)."
        )

        self.video_queue: List[Path] = []
        self.active_video_path: Optional[Path] = None
        self.current_frame_bgr: Optional[np.ndarray] = None
        self.total_frames: int = 1
        self.is_processing: bool = False
        self.stop_requested: bool = False
        self._tk_img: Optional[ImageTk.PhotoImage] = None

        self._build_ui()

        workspace_dir = Path(__file__).resolve().parent
        vids = discover_videos_in_folder(workspace_dir)
        if vids:
            self._set_queue(vids, str(workspace_dir if len(vids) > 1 else vids[0]))

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#141820")
        style.configure("Card.TFrame", background="#1e2430")
        style.configure("TLabel", background="#1e2430", foreground="#e6edf3", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#141820", foreground="#58a6ff", font=("Segoe UI", 14, "bold"))
        style.configure("TCheckbutton", background="#1e2430", foreground="#e6edf3", font=("Segoe UI", 10))
        style.configure("TRadiobutton", background="#1e2430", foreground="#e6edf3", font=("Segoe UI", 10))
        style.configure("Accent.TButton", background="#238636", foreground="#ffffff", font=("Segoe UI", 11, "bold"))
        style.map("Accent.TButton", background=[("active", "#2ea043")])

        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=16, pady=(10, 4))
        ttk.Label(
            header_frame,
            text="Automatic Studio Green Screen Remover — Zero-Outline & Smart Resume (.MOV + .WEBM)",
            style="Header.TLabel",
        ).pack(side=tk.LEFT)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)

        left_panel = ttk.Frame(body, style="Card.TFrame", width=460)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12), ipadx=12, ipady=8)
        left_panel.pack_propagate(False)

        right_panel = ttk.Frame(body, style="Card.TFrame")
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipadx=10, ipady=8)

        # --- LEFT PANEL ---
        ttk.Label(
            left_panel,
            text="1. Select Video or Bulk Folder (Saves in Same Folder)",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(6, 4))

        in_row = ttk.Frame(left_panel, style="Card.TFrame")
        in_row.pack(fill=tk.X, padx=12, pady=2)
        in_entry = ttk.Entry(in_row, textvariable=self.input_path_var)
        in_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_row = ttk.Frame(left_panel, style="Card.TFrame")
        btn_row.pack(fill=tk.X, padx=12, pady=(4, 2))
        ttk.Button(btn_row, text="Select Single Video...", command=self._browse_single_video).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4)
        )
        ttk.Button(btn_row, text="Select Folder (Bulk Upload)...", command=self._browse_folder).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0)
        )

        ttk.Checkbutton(
            left_panel,
            text="Include subfolders when uploading a folder",
            variable=self.recursive_var,
            command=self._refresh_folder_if_dir,
        ).pack(anchor="w", padx=14, pady=(2, 1))

        ttk.Checkbutton(
            left_panel,
            text="Smart Resume: Skip already-completed videos (Saves resources)",
            variable=self.skip_completed_var,
            command=self._refresh_queue_badges,
        ).pack(anchor="w", padx=14, pady=(0, 4))

        self.queue_label = ttk.Label(left_panel, text="Queued Videos (0):", font=("Segoe UI", 9, "bold"))
        self.queue_label.pack(anchor="w", padx=12, pady=(2, 2))

        q_frame = ttk.Frame(left_panel, style="Card.TFrame")
        q_frame.pack(fill=tk.X, padx=12, pady=2)
        self.queue_listbox = tk.Listbox(
            q_frame,
            height=4,
            bg="#141820",
            fg="#e6edf3",
            selectbackground="#1f6feb",
            font=("Consolas", 9),
            relief=tk.FLAT,
        )
        self.queue_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.queue_listbox.bind("<<ListboxSelect>>", self._on_select_queue_item)
        q_scroll = ttk.Scrollbar(q_frame, orient=tk.VERTICAL, command=self.queue_listbox.yview)
        q_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.queue_listbox.configure(yscrollcommand=q_scroll.set)

        # 2. Output Formats
        ttk.Label(left_panel, text="2. Output Formats (Saved in Video's Folder)", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=12, pady=(8, 2)
        )
        ttk.Checkbutton(
            left_panel,
            text="Transparent .MOV (QuickTime PNG RGBA — For Camtasia)",
            variable=self.export_mov_var,
            command=self._refresh_queue_badges,
        ).pack(anchor="w", padx=16, pady=1)
        ttk.Checkbutton(
            left_panel,
            text="Transparent .WEBM (VP9 Alpha — For Web / HTML5 / OBS)",
            variable=self.export_webm_var,
            command=self._refresh_queue_badges,
        ).pack(anchor="w", padx=16, pady=1)
        ttk.Checkbutton(
            left_panel,
            text="Composited .MP4 (Over Static Image or Dynamic Video)",
            variable=self.export_mp4_var,
            command=self._refresh_queue_badges,
        ).pack(anchor="w", padx=16, pady=1)

        # 3. Optional Background Image / Video
        ttk.Label(
            left_panel,
            text="3. Optional Background Image/Video (for .MP4 or Preview)",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(8, 2))
        bg_row = ttk.Frame(left_panel, style="Card.TFrame")
        bg_row.pack(fill=tk.X, padx=12, pady=2)
        bg_entry = ttk.Entry(bg_row, textvariable=self.bg_source_var)
        bg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(bg_row, text="Browse...", command=self._browse_bg).pack(side=tk.RIGHT)

        # 4. Adaptive Green Screen & Outline Choke Settings
        ttk.Label(
            left_panel,
            text="4. Per-Video Adaptive Green & Outline Choke",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(8, 2))

        ttk.Checkbutton(
            left_panel,
            text="Auto-Adapt to Each Video's Green Screen Colour (Recommended)",
            variable=self.auto_adapt_var,
            command=self._update_preview,
        ).pack(anchor="w", padx=16, pady=(2, 4))

        swatch_row = ttk.Frame(left_panel, style="Card.TFrame")
        swatch_row.pack(fill=tk.X, padx=16, pady=(0, 4))
        self.color_swatch = tk.Label(swatch_row, text="   ", bg="#15F120", relief=tk.SOLID, borderwidth=1)
        self.color_swatch.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(swatch_row, textvariable=self.profile_info_var, font=("Consolas", 9)).pack(side=tk.LEFT)

        ttk.Label(left_panel, text="Outline Choke (Cuts thin green border — Default: 1.25px):").pack(
            anchor="w", padx=16
        )
        self.choke_scale = ttk.Scale(
            left_panel,
            from_=0.0,
            to=2.5,
            variable=self.choke_var,
            command=lambda _: self._update_preview(),
        )
        self.choke_scale.pack(fill=tk.X, padx=16, pady=(1, 4))

        ttk.Label(left_panel, text="Background Green Floor (Auto-Scaled per video):").pack(anchor="w", padx=16)
        self.floor_scale = ttk.Scale(
            left_panel,
            from_=20.0,
            to=90.0,
            variable=self.bg_floor_var,
            command=lambda _: self._update_preview(),
        )
        self.floor_scale.pack(fill=tk.X, padx=16, pady=(1, 4))

        ttk.Label(left_panel, text="Green Spill Suppression Strength (Default: 1.0):").pack(anchor="w", padx=16)
        self.despill_scale = ttk.Scale(
            left_panel,
            from_=0.0,
            to=1.0,
            variable=self.despill_var,
            command=lambda _: self._update_preview(),
        )
        self.despill_scale.pack(fill=tk.X, padx=16, pady=(1, 4))

        # 5. Action Buttons + Progress Bar
        action_row = ttk.Frame(left_panel, style="Card.TFrame")
        action_row.pack(fill=tk.X, padx=12, pady=(6, 4))
        self.run_btn = ttk.Button(
            action_row,
            text="Start / Resume Processing (.MOV + .WEBM)",
            style="Accent.TButton",
            command=self._start_processing,
        )
        self.run_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)

        self.stop_btn = ttk.Button(
            action_row,
            text="Stop Safely",
            state=tk.DISABLED,
            command=self._request_stop,
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=(6, 0), ipady=5)

        self.progress = ttk.Progressbar(left_panel, orient=tk.HORIZONTAL, length=100, mode="determinate")
        self.progress.pack(fill=tk.X, padx=12, pady=(2, 6))

        ttk.Button(left_panel, text="Open Video Folder in Explorer", command=self._open_output_folder).pack(
            fill=tk.X, padx=12, pady=2
        )

        # --- RIGHT PANEL ---
        preview_top = ttk.Frame(right_panel, style="Card.TFrame")
        preview_top.pack(fill=tk.X, padx=10, pady=(6, 4))
        ttk.Label(preview_top, text="Live Zero-Outline Matte Preview", font=("Segoe UI", 11, "bold")).pack(
            side=tk.LEFT
        )
        self.frame_info_lbl = ttk.Label(preview_top, text="Frame: 0 / 0")
        self.frame_info_lbl.pack(side=tk.RIGHT)

        modes_bar = ttk.Frame(right_panel, style="Card.TFrame")
        modes_bar.pack(fill=tk.X, padx=10, pady=(0, 4))
        ttk.Label(modes_bar, text="Preview Background:").pack(side=tk.LEFT, padx=(0, 8))
        for label, val in [
            ("Checkerboard", "checker"),
            ("Dark Studio", "dark"),
            ("Pure White", "white"),
            ("Original Green", "original"),
            ("Custom BG", "custom"),
        ]:
            ttk.Radiobutton(
                modes_bar,
                text=label,
                value=val,
                variable=self.preview_mode_var,
                command=self._update_preview,
            ).pack(side=tk.LEFT, padx=6)

        self.canvas_lbl = ttk.Label(right_panel)
        self.canvas_lbl.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        scrub_row = ttk.Frame(right_panel, style="Card.TFrame")
        scrub_row.pack(fill=tk.X, padx=10, pady=(2, 8))
        ttk.Label(scrub_row, text="Scrub Frame:").pack(side=tk.LEFT, padx=(0, 8))
        self.scrub_slider = ttk.Scale(
            scrub_row,
            from_=0,
            to=100,
            variable=self.frame_slider_var,
            command=self._on_scrub,
        )
        self.scrub_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        status_bar = ttk.Frame(self, style="Card.TFrame")
        status_bar.pack(fill=tk.X, padx=16, pady=(2, 10))
        ttk.Label(status_bar, textvariable=self.status_var).pack(anchor="w", padx=10, pady=6)

    def _refresh_queue_badges(self) -> None:
        sel = self.queue_listbox.curselection()
        sel_idx = int(sel[0]) if sel else 0
        self.queue_listbox.delete(0, tk.END)
        done_count = 0
        for v in self.video_queue:
            done = is_video_fully_completed(
                v,
                export_mov=bool(self.export_mov_var.get()),
                export_webm=bool(self.export_webm_var.get()),
                export_mp4=bool(self.export_mp4_var.get()),
            )
            if done:
                done_count += 1
            badge = "[DONE]   " if done else "[PENDING]"
            self.queue_listbox.insert(tk.END, f"{badge} {v.name}")
        pending_count = len(self.video_queue) - done_count
        self.queue_label.configure(
            text=f"Queued Videos ({len(self.video_queue)} total | {done_count} Done, {pending_count} Pending):"
        )
        if self.video_queue and 0 <= sel_idx < len(self.video_queue):
            self.queue_listbox.selection_set(sel_idx)

    def _set_queue(self, videos: List[Path], display_path: str) -> None:
        self.input_path_var.set(display_path)
        self.video_queue = videos
        self._refresh_queue_badges()
        if videos:
            self._load_video_metadata(videos[0])
            done_c = sum(
                1
                for v in videos
                if is_video_fully_completed(
                    v,
                    export_mov=bool(self.export_mov_var.get()),
                    export_webm=bool(self.export_webm_var.get()),
                    export_mp4=bool(self.export_mp4_var.get()),
                )
            )
            if len(videos) > 1:
                self.status_var.set(
                    f"Bulk Mode: {len(videos)} videos found ({done_c} already completed, {len(videos)-done_c} pending)."
                )
            else:
                self.status_var.set(f"Loaded '{videos[0].name}'. Ready to process.")
        else:
            self.status_var.set("No source videos found in selected location.")

    def _browse_single_video(self) -> None:
        if self.is_processing:
            return
        path = filedialog.askopenfilename(
            title="Select Green Screen Video",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All Files", "*.*")],
        )
        if path:
            p = Path(path).resolve()
            self._set_queue([p], str(p))

    def _browse_folder(self) -> None:
        if self.is_processing:
            return
        folder = filedialog.askdirectory(title="Select Folder Containing Green Screen Videos (Bulk Upload)")
        if folder:
            f_path = Path(folder).resolve()
            vids = discover_videos_in_folder(f_path, recursive=self.recursive_var.get())
            self._set_queue(vids, str(f_path))

    def _refresh_folder_if_dir(self) -> None:
        curr = Path(self.input_path_var.get())
        if curr.exists() and curr.is_dir():
            vids = discover_videos_in_folder(curr, recursive=self.recursive_var.get())
            self._set_queue(vids, str(curr))

    def _on_select_queue_item(self, _event: object) -> None:
        sel = self.queue_listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.video_queue):
            self._load_video_metadata(self.video_queue[idx])

    def _browse_bg(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Static Image or Dynamic Background Video",
            filetypes=[
                ("Media Files", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.webm"),
                ("All Files", "*.*"),
            ],
        )
        if path:
            self.bg_source_var.set(path)
            self.export_mp4_var.set(True)
            self.preview_mode_var.set("custom")
            self._refresh_queue_badges()
            self._update_preview()

    def _load_video_metadata(self, video_path: Path) -> None:
        self.active_video_path = video_path
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return
        self.total_frames = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        mid_frame = min(60, self.total_frames // 2)
        self.scrub_slider.configure(to=max(0, self.total_frames - 1))
        self.frame_slider_var.set(mid_frame)
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            self.current_frame_bgr = frame
            self.frame_info_lbl.configure(text=f"{video_path.name} — Frame: {mid_frame} / {self.total_frames}")
            self._update_preview()

    def _on_scrub(self, _val: str) -> None:
        if self.active_video_path is None or not self.active_video_path.exists():
            return
        idx = int(float(self.frame_slider_var.get()))
        cap = cv2.VideoCapture(str(self.active_video_path))
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                self.current_frame_bgr = frame
                self.frame_info_lbl.configure(
                    text=f"{self.active_video_path.name} — Frame: {idx} / {self.total_frames}"
                )
                self._update_preview()

    def _update_preview(self) -> None:
        if self.current_frame_bgr is None:
            return
        frame = self.current_frame_bgr
        mode = self.preview_mode_var.get()

        cfg = KeyerConfig(
            auto_adapt=bool(self.auto_adapt_var.get()),
            bg_excess_floor=float(self.bg_floor_var.get()),
            matte_choke_px=float(self.choke_var.get()),
            despill_strength=float(self.despill_var.get()),
        )
        keyer = StudioGreenScreenKeyer(config=cfg)
        prof = keyer.auto_calibrate_from_frame(frame)

        self.color_swatch.configure(bg=prof.bg_rgb_hex)
        if self.auto_adapt_var.get():
            self.bg_floor_var.set(round(prof.adapted_bg_floor, 1))
            self.profile_info_var.set(
                f"{prof.bg_rgb_hex} | Auto Floor: {prof.adapted_bg_floor:.1f} | Choke: {self.choke_var.get():.2f}px"
            )
        else:
            self.profile_info_var.set(
                f"{prof.bg_rgb_hex} | Manual Floor: {self.bg_floor_var.get():.1f} | Choke: {self.choke_var.get():.2f}px"
            )

        if mode == "original":
            vis_bgr = frame.copy()
        else:
            rgba = keyer.process_frame(frame)
            h, w = frame.shape[:2]

            if mode == "checker":
                bg = keyer.make_checkerboard_bgr(h, w, 24)
            elif mode == "dark":
                bg = np.full_like(frame, 25)
            elif mode == "white":
                bg = np.full_like(frame, 245)
            else:
                bg = None
                bg_path = Path(self.bg_source_var.get()) if self.bg_source_var.get() else None
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

        disp_w = max(480, self.canvas_lbl.winfo_width() - 16)
        disp_h = max(270, self.canvas_lbl.winfo_height() - 16)
        fh, fw = vis_bgr.shape[:2]
        scale = min(disp_w / fw, disp_h / fh)
        nw, nh = max(1, int(fw * scale)), max(1, int(fh * scale))
        resized = cv2.resize(vis_bgr, (nw, nh), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self._tk_img = ImageTk.PhotoImage(pil_img)
        self.canvas_lbl.configure(image=self._tk_img)

    def _open_output_folder(self) -> None:
        if self.active_video_path and self.active_video_path.exists():
            os.startfile(str(self.active_video_path.parent))
            return
        in_p = Path(self.input_path_var.get())
        if in_p.exists():
            os.startfile(str(in_p if in_p.is_dir() else in_p.parent))
        else:
            os.startfile(str(Path(__file__).resolve().parent))

    def _request_stop(self) -> None:
        if self.is_processing:
            self.stop_requested = True
            self.status_var.set("Stopping safely... (Completed videos are preserved)")

    def _start_processing(self) -> None:
        if self.is_processing:
            return

        raw_input = self.input_path_var.get().strip()
        if raw_input:
            p = Path(raw_input).resolve()
            if p.exists():
                if p.is_dir():
                    self.video_queue = discover_videos_in_folder(p, recursive=self.recursive_var.get())
                elif p.is_file() and (not self.video_queue or self.video_queue[0] != p):
                    self.video_queue = [p]

        if not self.video_queue:
            messagebox.showerror("No Videos Found", "Please select a valid video file or a folder containing videos.")
            return

        if not (self.export_mov_var.get() or self.export_webm_var.get() or self.export_mp4_var.get()):
            messagebox.showwarning("No Output Selected", "Please select at least one output format (.MOV, .WEBM, or .MP4).")
            return

        self.is_processing = True
        self.stop_requested = False
        self.run_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.progress["value"] = 0

        threading.Thread(target=self._worker_run_batch, args=(list(self.video_queue),), daemon=True).start()

    def _worker_run_batch(self, videos: List[Path]) -> None:
        try:
            total_vids = len(videos)
            processed_count = 0
            skipped_count = 0
            failed_videos: List[str] = []
            bg_src = self.bg_source_var.get().strip() or None

            cfg = KeyerConfig(
                auto_adapt=bool(self.auto_adapt_var.get()),
                bg_excess_floor=float(self.bg_floor_var.get()),
                matte_choke_px=float(self.choke_var.get()),
                despill_strength=float(self.despill_var.get()),
                skip_completed=bool(self.skip_completed_var.get()),
                max_retries=3,
            )

            for v_idx, in_path in enumerate(videos, start=1):
                if self.stop_requested:
                    break

                stem = in_path.stem
                out_dir = in_path.parent
                out_mov = (out_dir / f"{stem}_transparent.mov") if self.export_mov_var.get() else None
                out_webm = (out_dir / f"{stem}_transparent.webm") if self.export_webm_var.get() else None
                out_mp4 = (out_dir / f"{stem}_composited.mp4") if self.export_mp4_var.get() else None

                if cfg.skip_completed and is_video_fully_completed(
                    in_path,
                    export_mov=bool(out_mov),
                    export_webm=bool(out_webm),
                    export_mp4=bool(out_mp4),
                    out_dir=out_dir,
                ):
                    skipped_count += 1
                    overall_pct = (v_idx / max(1, total_vids)) * 100.0
                    self.after(
                        0,
                        lambda pct=overall_pct, vn=in_path.name, vi=v_idx: (
                            self.progress.configure(value=pct),
                            self.status_var.set(
                                f"[{vi}/{total_vids}] Skipped '{vn}' (Already completed & verified)"
                            ),
                        ),
                    )
                    continue

                current_hex = ["#15F120"]
                current_floor = [44.0]

                def on_prof(prof: VideoGreenProfile) -> None:
                    current_hex[0] = prof.bg_rgb_hex
                    current_floor[0] = prof.adapted_bg_floor
                    self.after(
                        0,
                        lambda: (
                            self.color_swatch.configure(bg=prof.bg_rgb_hex),
                            self.profile_info_var.set(
                                f"{prof.bg_rgb_hex} | Auto Floor: {prof.adapted_bg_floor:.1f} | Choke: {self.choke_var.get():.2f}px"
                            ),
                        ),
                    )

                def on_prog(idx: int, total: int, elapsed: float, v_i: int = v_idx, v_name: str = in_path.name) -> None:
                    video_pct = idx / max(1, total)
                    overall_pct = (((v_i - 1) + video_pct) / max(1, total_vids)) * 100.0
                    fps = idx / max(1e-3, elapsed)
                    eta = max(0.0, (total - idx) / max(1e-3, fps))
                    self.after(
                        0,
                        lambda: (
                            self.progress.configure(value=overall_pct),
                            self.status_var.set(
                                f"[Video {v_i}/{total_vids}: {v_name}] Frame {idx}/{total} ({video_pct*100:.1f}%) "
                                f"| Green {current_hex[0]} | {fps:.1f} fps | ETA: {eta:.1f}s"
                            ),
                        ),
                    )

                try:
                    process_video_pipeline(
                        input_video=in_path,
                        output_mov=out_mov,
                        output_webm=out_webm,
                        output_composite_mp4=out_mp4,
                        background_source=bg_src,
                        config=cfg,
                        progress_callback=on_prog,
                        profile_callback=on_prof,
                        status_callback=lambda msg: self.after(0, lambda m=msg: self.status_var.set(m)),
                        cancel_check=lambda: self.stop_requested,
                    )
                    processed_count += 1
                    self.after(0, self._refresh_queue_badges)
                except Exception as vid_exc:
                    if self.stop_requested:
                        break
                    failed_videos.append(f"{in_path.name}: {vid_exc}")

            self.after(0, self._refresh_queue_badges)

            if self.stop_requested:
                self.after(
                    0,
                    lambda: self.status_var.set(
                        f"Stopped safely. ({processed_count} processed, {skipped_count} skipped). Click Start to resume."
                    ),
                )
            elif failed_videos:
                err_summary = "\n".join(failed_videos)
                self.after(
                    0,
                    lambda: (
                        self.status_var.set(
                            f"Batch finished with {len(failed_videos)} error(s). Click Start to retry failed items."
                        ),
                        messagebox.showwarning(
                            "Batch Completed with Warnings",
                            f"Processed: {processed_count} | Skipped (Already Done): {skipped_count}\n\n"
                            f"Failed items:\n{err_summary}",
                        ),
                    ),
                )
            else:
                msg = (
                    f"Batch Complete!\n\n"
                    f"• Newly Processed: {processed_count} video(s)\n"
                    f"• Skipped (Already Completed): {skipped_count} video(s)\n\n"
                    f"All .MOV and .WEBM files are saved in each video's folder."
                )
                self.after(
                    0,
                    lambda: (
                        self.status_var.set(
                            f"Completed! Newly processed: {processed_count}, Skipped (already done): {skipped_count}."
                        ),
                        messagebox.showinfo("Export Complete", msg),
                    ),
                )
        finally:
            self.after(
                0,
                lambda: (
                    setattr(self, "is_processing", False),
                    self.run_btn.configure(state=tk.NORMAL),
                    self.stop_btn.configure(state=tk.DISABLED),
                ),
            )


if __name__ == "__main__":
    app = GreenScreenApp()
    app.mainloop()
