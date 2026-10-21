# KeenScreen V2 Turbo — Automatic Studio Green Screen Remover & Compositor

High-speed, studio-grade green screen remover and background compositor designed for **Google Flow (`1080p @ 24fps`)** and studio green screen videos, producing **Camtasia-compatible `.mov` (RGBA PNG)**, **Web-ready `.webm` (VP9 Alpha)**, **Animated `.webp`**, and **Composited `.mp4`** outputs with **6x–15x faster multi-core performance** and **100% untouched interior accuracy**.

---

## What's New in Version 2.0 (Turbo Engine)
1. **Sparse Edge-Band Keying (`uint8` C++ SIMD + `float32` Boundary Ring)**:
   - Immediately locks the ~98.4% solid green background and solid character interior in native C++ `uint8`, running `float32` sub-pixel matte choke and color unmixing only on the ~1.6% boundary ring (**100% bit-exact accuracy to V1 at up to 15x faster multi-core frame rates**).
2. **Multi-Core Parallel Frame Pipeline (`ThreadPoolExecutor`)**:
   - Processes sliding batches of frames concurrently across your CPU cores while streaming strictly ordered frames to FFmpeg.
3. **Flexible Output Format Selection (GUI & CLI)**:
   - Choose **Both (`.MOV` + `.WEBM`)**, **Only `.MOV`** (Camtasia RGBA), **Only `.WEBM`** (Web VP9 Alpha), **Only `.WEBP`** (Animated Transparent WebP), or **Only `.MP4`** (Composited H.264), or any custom combination.
4. **Original Version 1 Preserved**:
   - A complete, untouched copy of Version 1 is preserved in `v1_original/` and `KeenScreen_Team_Package_v1.zip`.

---

## Quick Start for Team Members (Windows)

### Step 1 — One-Time Setup (`setup.bat`)
1. Extract `KeenScreen_Team_Package.zip` anywhere on your PC.
2. Double-click **`setup.bat`**.

### Step 2 — Launch GUI (`start.bat`) or Interactive CMD Control Center (`Launch_CLI.bat`)
- **Desktop GUI Mode**: Double-click **`start.bat`**
  - Auto-syncs from [`https://github.com/Ganeshmakad/KeenScreen`](https://github.com/Ganeshmakad/KeenScreen) and opens the V2 Turbo Desktop GUI silently.
- **Interactive CMD Control Center Mode (100% GUI Parity)**: Double-click **`Launch_CLI.bat`** (or run `start.bat --cli` / `python cli.py`)
  - Opens the V2 Interactive CMD dashboard with Quick Format Preset Selector `[F]`, individual `.MOV`/`.WEBM`/`.WEBP`/`.MP4` toggles, sliders, `[DONE]`/`[PENDING]` queue badges, and live frame preview.

---

## Command-Line Interface Reference

```powershell
# Interactive CMD Control Center
python cli.py

# Export ONLY Camtasia .MOV (Fastest for Camtasia editing)
python cli.py -i "E:\lesson 00\video 2" --format mov

# Export ONLY Web .WEBM
python cli.py -i "E:\lesson 00\video 2" --format webm

# Export ONLY Animated Transparent .WEBP
python cli.py -i "E:\lesson 00\video 2" --format webp

# Export Both .MOV + .WEBM
python cli.py -i "E:\lesson 00\video 2" --format both

# Export ONLY Composited .MP4 over custom background
python cli.py -i "E:\lesson 00\video 2" --format mp4 --bg "background.png"
```
