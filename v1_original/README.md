# KeenScreen — Automatic Studio Green Screen Remover & Compositor

Automatic, studio-grade green screen remover and background compositor designed for **Google Flow (`1080p @ 24fps`)** and studio green screen videos, producing **Camtasia-compatible `.mov` (RGBA PNG)** and **Web-ready `.webm` (VP9 Alpha)** transparent videos in a single pass.

---

## Quick Start for Team Members (Windows)

### Step 1 — One-Time Setup (`setup.bat`)
1. Extract `KeenScreen_Team_Package.zip` anywhere on your PC.
2. Double-click **`setup.bat`**.
   - Automatically checks/installs **Python 3.12**, **FFmpeg / FFprobe**, and required Python libraries (`opencv-python`, `numpy`, `Pillow`).

### Step 2 — Launch GUI (`start.bat`) or Interactive CMD Control Center (`Launch_CLI.bat`)
- **Desktop GUI Mode**: Double-click **`start.bat`**
  - Auto-syncs the latest code from [`https://github.com/Ganeshmakad/KeenScreen`](https://github.com/Ganeshmakad/KeenScreen) via PowerShell and opens the Desktop GUI silently in the background.
- **Interactive CMD Control Center Mode (100% GUI Parity)**: Double-click **`Launch_CLI.bat`** (or run `start.bat --cli` / `python cli.py`)
  - Auto-syncs from GitHub and opens an interactive CMD dashboard with the exact same controls, toggles, sliders, `[DONE]`/`[PENDING]` queue badges, live frame preview/scrubbing, and safe `Ctrl+C` stop as the GUI.

---

## Interactive CMD Control Center & CLI Reference

### Mode 1: Interactive CMD Menu (`Launch_CLI.bat` or `python cli.py`)
Provides numbered interactive controls matching every setting in the GUI:
- `[1]` **Select Single Video** (Paste/drag-and-drop path or press `B` for Windows File Browse dialog)
- `[2]` **Select Bulk Folder** (Paste/drag-and-drop folder path or press `B` for Windows Folder Browse dialog)
- `[3]` **Include Subfolders (`Recursive`)**: `[ON / OFF]`
- `[4]` **Smart Resume (`Skip Completed`)**: `[ON / OFF]`
- `[5]` **Inspect / Switch Queued Video**: View numbered list with `[DONE]` and `[PENDING]` status badges
- `[6]` **Transparent `.MOV` (Camtasia RGBA)**: `[ON / OFF]`
- `[7]` **Transparent `.WEBM` (Web VP9 Alpha)**: `[ON / OFF]`
- `[8]` **Composited `.MP4` (H.264)**: `[ON / OFF]`
- `[9]` **Set / Browse / Clear Custom Background Image or Video**
- `[10]` **Auto-Adapt to Video's Green Screen Colour**: `[ON / OFF]` + live calibrated `#HEX`, `RGB`, `Luma`, and `Floor`
- `[11]` **Outline Choke (`0.0 – 2.5px`, default `1.25px`)**
- `[12]` **Background Green Floor (`20.0 – 90.0`, default `44.0`)**
- `[13]` **Green Spill Suppression Strength (`0.0 – 1.0`, default `1.0`)**
- `[14]` **Advanced Matte & Output Folder (`FG Ceiling`, `Edge Smoothness`, `Alpha Power`, `Custom Out-Dir`)**
- `[P]` **Live Matte Preview & Frame Scrubbing** (`Checkerboard`, `Dark Studio`, `Pure White`, `Original Green`, `Custom BG`)
- `[S]` **Start / Resume Processing** (`Ctrl+C` stops safely and cleans up `.tmp_part` files while preserving completed videos)
- `[O]` **Open Video Folder in Explorer**

### Mode 2: Direct One-Line CLI Flags
```powershell
# Bulk folder processing with custom Outline Choke and Despill
python cli.py -i "E:\lesson 00\video 2" --choke 1.25 --despill 1.0 --recursive

# Inspect queue status ([DONE] vs [PENDING]) without encoding
python cli.py -i "E:\lesson 00\video 2" --list-queue

# Export a preview snapshot at frame 60 on Checkerboard background
python cli.py -i "video.mp4" --preview-frame 60 --preview-mode checker

# Open interactive OpenCV frame scrub & preview window from CLI
python cli.py -i "video.mp4" --interactive-preview
```
