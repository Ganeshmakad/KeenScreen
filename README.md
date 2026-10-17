# KeenScreen — Automatic Studio Green Screen Remover & Compositor

Automatic, studio-grade green screen remover and background compositor designed for **Google Flow (`1080p @ 24fps`)** and studio green screen videos, producing **Camtasia-compatible `.mov` (RGBA PNG)** and **Web-ready `.webm` (VP9 Alpha)** transparent videos in a single pass.

---

## Quick Start for Team Members (Windows)

### Step 1 — One-Time Setup (`setup.bat`)
1. Extract the `KeenScreen_Team_Package.zip` folder anywhere on your PC.
2. Double-click **`setup.bat`**.
   - Automatically checks/installs **Python 3.12**, **FFmpeg / FFprobe**, and required Python libraries (`opencv-python`, `numpy`, `Pillow`).

### Step 2 — Daily Launch (`start.bat`)
1. Double-click **`start.bat`** whenever you want to use the tool.
   - **Auto-Syncs from GitHub**: Automatically checks [`https://github.com/Ganeshmakad/KeenScreen`](https://github.com/Ganeshmakad/KeenScreen) via PowerShell and pulls any latest updates before opening (no need to re-download any `.zip` when improvements are released!).
   - **100% Silent Background Execution**: Opens the Desktop GUI directly with zero background terminal popups while processing videos.

---

## Key Features

- **Dual Transparent Output Formats**:
  - `<video_name>_transparent.mov` — QuickTime `.mov` (`png` `rgba` + `aac` audio), directly drag-and-drop compatible with **TechSmith Camtasia**, Premiere Pro, After Effects, and DaVinci Resolve.
  - `<video_name>_transparent.webm` — WebM (`libvpx-vp9` `yuva420p` + `libopus` audio) for web & lightweight playback.
  - Optional `<video_name>_composited.mp4` — H.264 `.mp4` composited over any custom image or looping background video.
- **Bulk Folder Upload (Saves In-Place)**:
  - Select an entire folder (with optional subfolder scanning) and generate transparent `.mov` / `.webm` files right inside the same folder as each source video.
- **Per-Video Adaptive Green Calibration**:
  - Automatically samples each video's specific green screen shade (`#HEX`, luminance, and compression noise floor) and adapts thresholds automatically.
- **Strict Outer-Ring-Only Keying + 100% Untouched Interior**:
  - Eliminates the 1–2px green screen outline around hair, ears, hands, and shoulders while keeping 100% of the character's interior (eyes, face, white shirt, blue tie, cuffs, suit) locked to `Alpha = 255` and original `RGB` (`0` internal fluctuation).
- **Smart Resume & 3-Stage Auto-Retry**:
  - Automatically skips already-completed valid outputs (`[DONE]`) so accidental clicks never waste time or re-render finished videos.
  - Uses atomic `.tmp_part` files during encoding and automatically retries transient Windows/FFmpeg interruptions.

---

## Command-Line Interface (Optional)

```powershell
# Single video
python cli.py -i "path\to\video.mp4"

# Bulk folder (saves outputs inside the same folder as each video)
python cli.py -i "path\to\folder" --recursive
```
