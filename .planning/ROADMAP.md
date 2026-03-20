# carvera-vision — Roadmap

**GitHub:** https://github.com/3DCreationsByChad/carvera-vision

> **Migration note:** This project was restructured from
> [fusion360-cam-assistant](https://github.com/3DCreationsByChad/fusion360-cam-assistant).
> Phases 1–4 of the original CAM assistant are archived in `.planning/phases/`
> (Fusion 360 add-in work: CAM state access, geometry analysis, stock suggestions,
> toolpath strategy). The carvera-vision architecture starts fresh below.

---

## Milestone 1: carvera-vision MVP

**Goal:** Standalone MCP server with screen vision + STEP geometry analysis.
No CAD software dependency. Works with Claude Desktop and Claude Code.

**Success Criteria:**
- `view_makera_window` captures the MakeraCam/Carvera window and returns it as an image
- `list_windows` and `capture_region` provide fallback / zoom capabilities
- `analyze_step_file` parses any STEP file and returns bbox, face inventory, min radius
- `query_tools` queries Makera CSV tool profiles with material/operation filtering
- Installable via `uv sync`, runs as stdio MCP server on Windows/macOS/Linux

---

## Phase 10: Foundation — MCP Skeleton + All Five Tools ✓

**Goal:** Deployable MCP server with all capabilities working end-to-end.

**Status:** COMPLETE (2026-03-20)

### Deliverables
- [x] `pyproject.toml` — carvera-vision package, Python 3.11+, all deps
- [x] `server.py` — MCP server, 5 tool registrations
- [x] `window_capture.py` — cross-platform: pygetwindow (Windows), AppleScript (macOS), wmctrl (Linux)
- [x] `step_parser.py` — pure-regex STEP parser, StepGeometry dataclass
- [x] `tool_library.py` — CSV loader, query_tools by radius/material/operation
- [x] `tools/carvera/` — Makera Ball Endmills, Drill Bits, O-Flute Bits CSVs
- [x] `CLAUDE.md` — full developer guide
- [x] `README.md` — public-facing docs

---

## Phase 11: Integration Testing

**Goal:** End-to-end test with real Carvera hardware and STEP files.

**Status:** NEXT

### Tasks
- [ ] Test analyze_step_file with Fusion 360, Plasticity, Shapr3D exports
- [ ] Test query_tools across all three CSV libraries
- [ ] Test view_makera_window with MakeraCam open on Windows
- [ ] Test list_windows and capture_region as fallbacks
- [ ] Fix any edge cases from real-world testing

---

## Phase 12: Enhanced STEP Analysis

**Goal:** Richer geometry intelligence from STEP files.

### Planned Features
- Pocket detection: CYLINDRICAL_SURFACE + PLANE combinations → classified holes/pockets
- Hole diameter classification: tap drill / clearance / counterbore
- WCS candidate scoring: rank AXIS2_PLACEMENT_3D by proximity to stock face
- Better bounding box: filter out construction geometry / tiny reference points

---

## Phase 13: MakeraCam Config Reading

**Goal:** Read .maka project files to understand current tool assignments.

### Planned Features
- Parse MakeraCam .maka format
- Extract assigned tools per operation, material setting, origin location
- Feed into tool recommendations so Claude knows what's already loaded

---

## Future (Out of Scope for MVP)

- Auto-focus MakeraCam window before capture (bring to front)
- Real-time machine status via Carvera network API
- Cross-session preference learning (SQLite)
- Windows installer / one-click setup script

---

*Last updated: 2026-03-20*
