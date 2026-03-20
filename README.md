# carvera-vision

**MCP server for Carvera CNC — gives Claude Desktop and Claude Code eyes on
your machine and 3D understanding of your parts.**

> **Status:** MVP / early alpha. Fully working on Windows. macOS and Linux
> support included but less tested — PRs welcome.

## What it does

Two capabilities, five tools:

| Tool | What it does |
|------|--------------|
| `view_makera_window` | Captures the MakeraCam/Carvera window as an image — Claude sees your current CAM setup |
| `list_windows` | Lists all open windows — use this if auto-detect fails |
| `capture_region` | Captures an arbitrary screen region by pixel coordinates — zoom into any panel |
| `analyze_step_file` | Parses a STEP file: bounding box, face inventory, coordinate systems, min tool radius |
| `query_tools` | Queries the Carvera tool library — filter by minimum radius, material, and operation |

Example prompts:
- *"Show me what's on my MakeraCam screen and check the WCS looks right"*
- *"Analyze this STEP file and tell me what stock I need for aluminum"*
- *"What's the smallest end mill I need for the internal features in this part?"*
- *"Look at my feeds panel — zoom into the bottom-right corner"*
- *"What roughing tools do I have for soft wood?"*

## The evolution story

This project grew out of [fusion360-cam-assistant](https://github.com/3DCreationsByChad/fusion360-cam-assistant),
which started as a Fusion 360 add-in extension. After building solid screen
vision and realizing that the most useful geometry data — bounding box, face
types, minimum tool radius — is fully accessible from plain STEP files, the
project outgrew its Fusion 360 dependency.

**carvera-vision is tool-agnostic.** STEP files from any CAD tool work the
same way. You don't need Fusion 360 open or any add-in installed.

## Supported CAD sources

Anything that exports STEP:
- **Fusion 360** — File → Export → STEP AP214
- **Plasticity** — File → Export → STEP
- **Shapr3D** — Export → STEP
- **Any downloaded `.step` / `.stp` file** from GrabCAD, McMaster, Makera, etc.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended)
- Claude Desktop or Claude Code
- MakeraCam or Carvera desktop app (for the window capture tools)
- **Linux only:** `wmctrl` for window detection (`sudo apt install wmctrl`)

## Quick install

```bash
git clone https://github.com/3DCreationsByChad/carvera-vision
cd carvera-vision
uv sync
```

Add to your Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "carvera-vision": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "C:\\path\\to\\carvera-vision",
        "carvera-vision"
      ]
    }
  }
}
```

For Claude Code:
```bash
claude mcp add carvera-vision -- uv run --project /path/to/carvera-vision carvera-vision
```

Restart Claude Desktop. The five tools will appear automatically.

## Tools in detail

### `view_makera_window`

Auto-detects and captures the MakeraCam/Carvera window.

**Example prompts:**
- *"Show me what's on my MakeraCam screen"*
- *"Look at my Carvera setup and check the origin location"*
- *"What toolpath strategy is currently loaded?"*

| Parameter | Default | Description |
|-----------|---------|-------------|
| `scale` | 1.0 | Resize factor — use 0.5 on 4K monitors to reduce token usage |

---

### `list_windows`

Lists all currently open window titles. Run this first if `view_makera_window`
cannot find the window — it shows you exactly what title to add as an alias.

---

### `capture_region`

Captures an arbitrary screen region by pixel coordinates.

**Example prompts:**
- *"Zoom into the feeds & speeds panel at coordinates 1200, 400, 600x300"*
- *"Capture the tool library area on my second monitor"*

| Parameter | Required | Description |
|-----------|----------|-------------|
| `left` | yes | Left edge in screen pixels |
| `top` | yes | Top edge in screen pixels |
| `width` | yes | Width in pixels |
| `height` | yes | Height in pixels |
| `scale` | no | Resize factor (default 1.0) |

---

### `analyze_step_file`

Parses a STEP file without any CAD kernel dependency.

**Example prompts:**
- *"Analyze /Downloads/bracket.step and tell me what stock I need"*
- *"What's the minimum tool radius for this part?"*
- *"Analyze the STEP file and suggest tools for aluminum pockets"*

**Example output:**
```json
{
  "part_name": "bracket",
  "units": "mm",
  "bounding_box": {
    "size": {"x": 75.5, "y": 40.0, "z": 12.0}
  },
  "dimensions_summary": "75.50 x 40.00 x 12.00 mm",
  "face_inventory": {
    "plane": 12, "cylindrical_surface": 4, "total": 16
  },
  "min_internal_radius": 3.175,
  "recommended_tools": [...]
}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `file_path` | required | Absolute path to `.step` or `.stp` file |
| `verbose` | false | Include raw entity type counts |

---

### `query_tools`

Query the Carvera tool library with optional filters.

**Example prompts:**
- *"What tools do I have for aluminum with radius <= 3mm?"*
- *"Show me roughing end mills for softwood"*
- *"What drills are in the library?"*

| Parameter | Description |
|-----------|-------------|
| `min_radius` | Max tool radius (mm) — from `analyze_step_file` |
| `material` | `aluminum`, `wood`, `plastic`, `copper`, `brass`, `pcb`, `steel` |
| `operation` | `roughing`, `finishing`, `drilling`, `engraving`, `profiling`, `pocketing` |

## Troubleshooting

**`view_makera_window` can't find the window**
- Make sure MakeraCam or Carvera is open and not minimized
- Run `list_windows` to see all visible window titles
- If the title doesn't match, add a substring to `MAKERA_WINDOW_ALIASES`
  in `src/carvera_vision/window_capture.py`

**macOS: screen recording permission**
Grant screen recording permission to your terminal or Claude Desktop under
System Settings → Privacy & Security → Screen Recording.

**Linux: wmctrl not found**
```bash
sudo apt install wmctrl   # Debian/Ubuntu
sudo dnf install wmctrl   # Fedora
```

**`analyze_step_file` returns unexpected bounding box**
- Check the `units` field — some exporters default to inches
- Use `verbose=true` to see entity counts — very low counts suggest a
  surface-only or mesh export rather than a solid B-rep

**`query_tools` returns no results**
- Check that `tools/carvera/*.csv` files are present
- Try relaxing filters (remove `operation`, try a different `material`)

**Server won't start**
```bash
uv run carvera-vision
# or
uv run python -c "from carvera_vision.server import main; main()"
```

## Roadmap

- [x] 5 MCP tools: window capture + STEP analysis + tool library
- [x] Cross-platform window detection (Windows/macOS/Linux)
- [x] Lightweight STEP parser (no OpenCASCADE)
- [ ] STEP pocket/hole classification (depth, diameter, type)
- [ ] MakeraCam `.maka` project file reading
- [ ] Auto-focus window before capture (bring to front)
- [ ] Windows installer / one-click setup

## Credits

- **[AuraFriday](https://github.com/AuraFriday)** — [Fusion-360-MCP-Server](https://github.com/AuraFriday/Fusion-360-MCP-Server),
  the original MCP integration that inspired this project's architecture
- **[Makera](https://www.makera.com/)** — Carvera tool library CSV exports
- **Carvera Community** — tool profiles and feeds/speeds validation

## License

MIT
