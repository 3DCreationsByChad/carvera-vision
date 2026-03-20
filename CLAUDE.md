# carvera-vision — Claude Code Guide

## What This Is

**carvera-vision** is an MCP server that gives Claude Desktop and Claude Code
two AI-native capabilities for Carvera CNC users:

1. **Screen Vision** — auto-detect and capture the MakeraCam/Carvera software
   window, so Claude can see the current CAM setup, toolpaths, or machine status
2. **STEP Geometry Analysis** — parse STEP files (from any CAD tool) to extract
   bounding box, face types, coordinate systems, and minimum tool radius,
   giving Claude genuine 3D understanding of the part being machined

**Target users:** Carvera Air owners using any CAD tool — Fusion 360, Plasticity,
Shapr3D, or working from downloaded STEP files.

## Project Structure

```
carvera-vision/
  src/carvera_vision/
    __init__.py
    server.py          <- MCP server; registers 5 tools, dispatches to implementations
    window_capture.py  <- Cross-platform window detection + mss screenshot
    step_parser.py     <- Pure-regex STEP parser; no OpenCASCADE required
    tool_library.py    <- Makera CSV loader + query_tools filter/sort engine
  tools/
    carvera/           <- Makera CSV exports: Ball Endmills, Drill Bits, O-Flute Bits
  docs/
  .planning/           <- GSD planning: PROJECT.md, ROADMAP.md, phases/
  pyproject.toml
  CLAUDE.md            <- This file
  README.md
```

## Five MCP Tools

| Tool | Module | Description |
|------|--------|-------------|
| `view_makera_window` | window_capture.py | Auto-detect + capture Carvera/MakeraCam window |
| `list_windows` | window_capture.py | Enumerate all open windows (debug/fallback) |
| `capture_region` | window_capture.py | Capture arbitrary screen region by coordinates |
| `analyze_step_file` | step_parser.py | Parse STEP file → bbox, faces, min radius |
| `query_tools` | tool_library.py | Query Makera CSV library by radius/material/op |

## Two-Capability Architecture

### Capability 1: Window Vision

`window_capture.py` provides three public functions used by three tools:

- `find_makera_window() -> Optional[WindowInfo]` — searches open windows
  against `MAKERA_WINDOW_ALIASES`, case-insensitive substring match
- `capture_window(window, scale) -> (b64_str, width, height)` — captures
  the window region with `mss`, optionally resizes with Pillow, returns
  base64-encoded PNG ready for MCP ImageContent
- `list_all_windows() -> list[str]` — enumerates all window titles

**Platform implementations:**
- **Windows:** `pygetwindow` — most reliable, handles off-screen coords
- **macOS:** AppleScript via `osascript` — no extra deps, native enumeration
- **Linux:** `wmctrl -lG` — standard X11 window manager (install: `apt install wmctrl`)

`MAKERA_WINDOW_ALIASES` is a list at the top of `window_capture.py`:
```python
MAKERA_WINDOW_ALIASES = [
    "makeracam",
    "makera cam",
    "carvera",
    "makera",
]
```
Matching is case-insensitive substring. Adding `"carvera air"` would match
both "Carvera Air 1.2" and "Carvera".

**To add a new alias:** append a lowercase substring to `MAKERA_WINDOW_ALIASES`.

**To find the exact window title:**
- Call `list_windows` from Claude — it returns all visible titles
- Or: `python -c "import pygetwindow as gw; print([w.title for w in gw.getAllWindows()])"`

### Capability 2: STEP Geometry Analysis

`step_parser.py` → `analyze_step_file` tool

STEP (ISO 10303) is plain ASCII text. The parser extracts all entities with
a single regex, builds an entity map, then queries it for the data Claude needs.

| Extracted field | Source entity | Why Claude needs it |
|----------------|--------------|---------------------|
| Bounding box | `CARTESIAN_POINT` (all, then min/max XYZ) | Part size → stock setup |
| Face inventory | `PLANE`, `CYLINDRICAL_SURFACE`, etc. | Understand part complexity |
| Coordinate systems | `AXIS2_PLACEMENT_3D` | Identify WCS datum candidates |
| Min internal radius | Last float from `CYLINDRICAL_SURFACE` + `CIRCLE` | Min tool diameter needed |
| Part name | `PRODUCT` first quoted string | Confirm correct file |
| Units | `SI_UNIT` / `CONVERSION_BASED_UNIT` | Correct dimensional output |

**Why no geometry kernel?** OpenCASCADE/pythonocc adds 200–500MB and requires
platform-specific compilation. Regex extraction gets Claude what it needs
in milliseconds, zero extra dependencies.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No CAD kernel | Zero extra deps; bbox/faces/radius all present in plain STEP text |
| Stdio MCP transport | Works with Claude Desktop and Claude Code without network config |
| Makera CSV format | Makera publishes Fusion 360 exports; no custom format needed |
| Tool-agnostic STEP | Works with any CAD exporter, no add-in required |
| pygetwindow + mss | Reliable Windows path; AppleScript/wmctrl for other platforms |

## Common Tasks

### Adding a window alias
Edit `MAKERA_WINDOW_ALIASES` in `src/carvera_vision/window_capture.py`.
Add a lowercase substring. No restart needed if using `mcp dev`.

### Adding a tool profile
Drop a new `.csv` into `tools/carvera/`. Headers must match the Makera
Fusion 360 tool library export format. Server reloads tools at startup.

### Testing without MakeraCam open
- **view_makera_window / capture_region:** Open any window with "Carvera" in
  the title. Even a Notepad window renamed in Task Manager works.
- **list_windows:** Works any time — shows all currently visible windows.
- **analyze_step_file:** Any STEP file. Export from your CAD tool or use a
  sample from GrabCAD.
- **query_tools:** Requires CSV files in `tools/carvera/`.

### Running the server
```bash
uv sync
uv run carvera-vision           # stdio MCP server
uv run mcp dev src/carvera_vision/server.py  # with MCP Inspector
```

### claude_desktop_config.json
```json
{
  "mcpServers": {
    "carvera-vision": {
      "command": "uv",
      "args": ["run", "--project", "C:/path/to/carvera-vision", "carvera-vision"]
    }
  }
}
```

## Known Limitations

- Minimized windows cannot be captured (mss returns blank/black region)
- macOS Screen Recording permission may need to be granted to the terminal
  or Claude Desktop under System Settings → Privacy & Security
- Linux Wayland: `wmctrl` is X11-only; Wayland support is a known gap
- STEP bounding box may be slightly oversized if the file contains
  construction geometry with points far from the actual part

## .planning/ Directory

- `PROJECT.md` — project definition, goals, migration history  
- `ROADMAP.md` — milestone and phase breakdown  
- `STATE.md` — current work state (updated by GSD commands)  
- `phases/` — historical Fusion 360 CAM assistant phases (1–4, archived) and
  new carvera-vision phases (10+)
