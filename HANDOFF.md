# carvera-vision — Session Handoff

**Date:** 2026-03-20  
**Repo:** https://github.com/3DCreationsByChad/carvera-vision

---

## What Was Built

This repo was restructured from `fusion360-cam-assistant` (a Fusion 360 add-in
extension) into a fully standalone MCP server. The Fusion 360 dependency is gone.
The new architecture works with any CAD tool that can export a STEP file.

**Two capabilities:**

1. **Screen Vision** — detects and captures the MakeraCam/Carvera software window
   so Claude can see the current CAM setup. Cross-platform: Windows (pygetwindow),
   macOS (AppleScript), Linux (wmctrl).

2. **STEP Geometry Analysis** — parses STEP AP214/AP242 files with pure regex
   (no OpenCASCADE, no heavy geometry kernel). Extracts bounding box, face type
   inventory, coordinate systems (WCS candidates), and minimum internal tool radius.
   Works with exports from Fusion 360, Plasticity, Shapr3D, or any STEP file.

**Tool library** — loads Makera's Fusion 360 CSV exports from `tools/carvera/`
and queries them by minimum radius, material, and operation type.

---

## The Five MCP Tools

| Tool | What it does |
|------|-------------|
| `view_makera_window` | Auto-detects and captures the MakeraCam/Carvera window as a PNG image |
| `list_windows` | Lists all open window titles — use when auto-detect fails |
| `capture_region` | Captures an arbitrary screen region by pixel coordinates — zoom into any panel |
| `analyze_step_file` | Parses a STEP file: bounding box, face inventory, coordinate systems, min tool radius, auto tool recs |
| `query_tools` | Queries `tools/carvera/*.csv` filtered by min_radius, material, operation |

**Typical Claude workflow:**
```
1. analyze_step_file("/path/to/part.step")
   → learns part dimensions + min internal radius

2. query_tools(min_radius=3.175, material="aluminum", operation="roughing")
   → gets ranked tool list with feeds/speeds

3. view_makera_window()
   → sees current MakeraCam state

4. Claude gives a complete setup recommendation
```

---

## What Still Needs Testing

### High priority (do these first)
- [ ] **`view_makera_window` on Windows with real MakeraCam open** — confirm window
  title matches an alias in `MAKERA_WINDOW_ALIASES`, capture returns a clean PNG
- [ ] **`analyze_step_file` with real STEP exports** — test at least one file from
  each source: Fusion 360, Plasticity, Shapr3D. Verify bounding box and
  `min_internal_radius` are sensible for known parts
- [ ] **`query_tools` with the 3 Makera CSVs** — confirm loading works, test
  `material="aluminum"` + `operation="roughing"` returns flat/o-flute end mills

### Medium priority
- [ ] **`list_windows` and `capture_region`** as fallbacks — confirm `list_windows`
  shows MakeraCam when open, `capture_region` returns correct pixels for a known area
- [ ] **`analyze_step_file` automatic tool recs** — confirm `recommended_tools` in
  the response are actually suitable for the part's min radius
- [ ] **`uv sync` clean install** — clone fresh, run `uv sync`, confirm all deps
  resolve without conflicts (pygetwindow + pyautogui on Windows is the one to watch)

### Low priority / known gaps
- [ ] macOS `view_makera_window` — AppleScript path less tested; may need screen
  recording permission granted to terminal or Claude Desktop
- [ ] Linux — requires `wmctrl` installed; Wayland not supported (X11 only)
- [ ] Minimized windows return blank capture — add a "window is minimized" warning
- [ ] STEP bounding box can include construction geometry points — may be slightly
  oversized for some CAD exporters

---

## Next Priorities

### 1. Integration test pass (immediate)
Run all 5 tools with real hardware and real files. Fix any edge cases found.
See "What Still Needs Testing" above.

### 2. STEP pocket/hole classification (Phase 12)
Current STEP parser extracts raw face counts and radii. The next step is
classifying them: detect pocket features (CYLINDRICAL_SURFACE + PLANE combinations),
classify holes as tap drill / clearance / counterbore, score WCS candidates by
proximity to stock faces. This gives Claude much richer part understanding.

### 3. MakeraCam `.maka` file reading (Phase 13)
MakeraCam saves project files in `.maka` format. Parsing these would let Claude
see the current tool assignments, material setting, and origin location — closing
the loop between STEP analysis and what's actually loaded in the software.

### 4. Auto-focus before capture
`view_makera_window` captures whatever is visible; if the window is behind another
app it may capture a partial or obscured view. Bringing the window to the front
before grabbing (Win32 `SetForegroundWindow`, AppleScript `activate`) would
make captures reliable without the user having to manually focus the window.

### 5. Claude Desktop config snippet
`tools/carvera/` has a `.gitkeep`. Add a `claude_desktop_config_snippet.json`
(already in the CV-files folder from the parallel session) so users have a
copy-paste config ready in the repo.

---

## Key Files for Future Contributors

| File | Purpose |
|------|---------|
| `src/carvera_vision/server.py` | MCP server, all 5 tool registrations and dispatch |
| `src/carvera_vision/window_capture.py` | Window detection + capture, `MAKERA_WINDOW_ALIASES` |
| `src/carvera_vision/step_parser.py` | STEP entity parsing, `StepGeometry` dataclass |
| `src/carvera_vision/tool_library.py` | CSV loader, `query_tools` filter/sort engine |
| `tools/carvera/*.csv` | Makera tool library (Ball Endmills, Drill Bits, O-Flute Bits) |
| `.planning/ROADMAP.md` | Phase breakdown and status |
| `CLAUDE.md` | Full developer guide — read this first |

---

## Migration Notes

This repo was created from `fusion360-cam-assistant` (same GitHub account) rather
than a true fork — GitHub doesn't allow forking to the same account. The git history
starts fresh here. The original repo preserves the full Fusion 360 add-in history
if it's ever needed for reference.

Files removed from the source: `Fusion-360-MCP-Server/` (entire AuraFriday add-in
subtree), `mcp-link-bridge.js`, `mcp-link-claude.bat`, `AUTH_FIX_SUMMARY.md`,
`DIRECT_CONNECT_SETUP.md`, `SESSION_STATUS.md`, `RESUME_CHECKLIST.md`,
`fix_syntax.py`, `get_server_token.py`, `test_mcp_auth.py`, `.mcp.json`.

Files migrated: `.planning/` (updated roadmap, preserved phase history),
`CONTRIBUTING.md`, `LICENSE`, `.gitignore`, `tools/carvera/*.csv`.
