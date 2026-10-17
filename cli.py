"""
Automatic Green Screen Remover & Background Compositor — Command Line Interface (CLI)
Supports Single Video & Bulk Folder Processing with Smart Resume, Auto-Retry, and Per-Video Adaptive Green Calibration.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from keyer_engine import (
    KeyerConfig,
    VideoGreenProfile,
    discover_videos_in_folder,
    is_video_fully_completed,
    process_video_pipeline,
)


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
        f"| Luma Y: {prof.bg_luma:.1f} | Excess: {prof.bg_excess:.1f} | Noise: ±{prof.bg_std:.1f}"
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
    bg_source: str | None = None,
    config: KeyerConfig | None = None,
    batch_index: int | None = None,
    batch_total: int | None = None,
) -> dict:
    target_dir = out_dir if out_dir is not None else video_path.parent
    stem = video_path.stem
    out_mov = (target_dir / f"{stem}_transparent.mov") if export_mov else None
    out_webm = (target_dir / f"{stem}_transparent.webm") if export_webm else None
    out_mp4 = (target_dir / f"{stem}_composited.mp4") if (export_mp4 or bg_source) else None

    prefix = f"[{batch_index}/{batch_total}] " if (batch_index and batch_total) else ""
    cfg = config or KeyerConfig()

    if cfg.skip_completed and is_video_fully_completed(
        video_path, export_mov=export_mov, export_webm=export_webm, export_mp4=bool(out_mp4), out_dir=target_dir
    ):
        print(f"{prefix}SKIPPED (Already Completed & Verified): {video_path.name}")
        return {}

    print(f"\n======================================================================")
    print(f"{prefix}Processing Video : {video_path.name}")
    print(f"  Source Folder   : {video_path.parent}")
    if out_mov:
        print(f"  -> Camtasia MOV : {out_mov.name} (QuickTime PNG RGBA + AAC Audio)")
    if out_webm:
        print(f"  -> Web VP9 WebM : {out_webm.name} (VP9 yuva420p Alpha + Opus Audio)")
    if out_mp4:
        bg_desc = Path(bg_source).name if bg_source else "Studio Dark Gradient"
        print(f"  -> Composite MP4: {out_mp4.name} (Background: {bg_desc})")

    results = process_video_pipeline(
        input_video=video_path,
        output_mov=out_mov,
        output_webm=out_webm,
        output_composite_mp4=out_mp4,
        background_source=bg_source,
        config=cfg,
        progress_callback=_print_progress,
        profile_callback=_print_profile,
        status_callback=lambda msg: print(f"\n  [Status] {msg}"),
    )

    print("  Saved in Folder :")
    for fmt, path_str in results.items():
        p = Path(path_str)
        size_mb = p.stat().st_size / (1024 * 1024) if p.exists() else 0.0
        print(f"    [{fmt.upper():4s}] {p} ({size_mb:.2f} MB)")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automatic Pixel-Perfect Green Screen Remover (Smart Resume + Auto-Retry)"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to a green screen video (.mp4) OR a folder of videos for bulk processing",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Optional custom output directory (defaults to the same folder as each input video)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When input is a folder, also scan subfolders recursively",
    )
    parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Re-process and overwrite videos even if valid outputs already exist",
    )
    parser.add_argument(
        "--no-mov",
        action="store_true",
        help="Skip exporting transparent .mov (Camtasia PNG RGBA)",
    )
    parser.add_argument(
        "--no-webm",
        action="store_true",
        help="Skip exporting transparent .webm (Web VP9 Alpha)",
    )
    parser.add_argument(
        "--composite",
        action="store_true",
        help="Also export a composited .mp4 video (over --bg or studio background)",
    )
    parser.add_argument(
        "--bg",
        default=None,
        help="Optional static image (.png/.jpg) or dynamic video (.mp4) background for .mp4 compositing",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all source videos in the input folder",
    )
    parser.add_argument(
        "--manual-floor",
        type=float,
        default=None,
        help="Override automatic per-video bg_excess_floor with a fixed value",
    )
    parser.add_argument(
        "--despill",
        type=float,
        default=1.0,
        help="Green spill suppression strength 0.0-1.0 (default: 1.0)",
    )

    args = parser.parse_args()
    input_path = Path(args.input).resolve()

    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}", file=sys.stderr)
        return 1

    cfg = KeyerConfig(
        auto_adapt=(args.manual_floor is None),
        bg_excess_floor=args.manual_floor if args.manual_floor is not None else 68.0,
        despill_strength=args.despill,
        skip_completed=(not args.force_overwrite),
    )

    export_mov = not args.no_mov
    export_webm = not args.no_webm
    export_mp4 = args.composite or (args.bg is not None)
    custom_out_dir = Path(args.out_dir).resolve() if args.out_dir else None

    if args.batch or input_path.is_dir():
        folder = input_path if input_path.is_dir() else input_path.parent
        videos: List[Path] = discover_videos_in_folder(folder, recursive=args.recursive)
        if not videos:
            print(f"No source video files found in: {folder}")
            return 1
        print(f"Bulk Folder Mode: Found {len(videos)} source video(s) in '{folder}'")
        for idx, v in enumerate(videos, start=1):
            process_single_file(
                v,
                out_dir=custom_out_dir,
                export_mov=export_mov,
                export_webm=export_webm,
                export_mp4=export_mp4,
                bg_source=args.bg,
                config=cfg,
                batch_index=idx,
                batch_total=len(videos),
            )
        print(f"\nBulk processing complete! All {len(videos)} video(s) verified in their respective folders.")
    else:
        process_single_file(
            input_path,
            out_dir=custom_out_dir,
            export_mov=export_mov,
            export_webm=export_webm,
            export_mp4=export_mp4,
            bg_source=args.bg,
            config=cfg,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
