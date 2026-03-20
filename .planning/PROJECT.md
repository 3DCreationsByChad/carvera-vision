# carvera-vision

**GitHub:** https://github.com/3DCreationsByChad/carvera-vision

## What This Is

An MCP server that gives Claude Desktop and Claude Code two AI-native
capabilities for Carvera CNC users:

1. **Screen Vision** — auto-detect and capture the MakeraCam/Carvera software
   window, so Claude can see the current CAM setup, toolpaths, or machine status
2. **STEP Geometry Analysis** — parse STEP files (from any CAD tool) to extract
   bounding box, face types, coordinate systems, and minimum tool radius,
   giving Claude genuine 3D understanding of the part being machined

## Target Users

Carvera Air owners using any CAD tool — Fusion 360, Plasticity, Shapr3D,
or working from downloaded STEP files. No dependency on any specific CAD
software being open.

## Core Value

Claude can see your MakeraCam screen AND understand the 3D geometry of your
part, without requiring any CAD add-in or plugin. Export a STEP file from
your CAD tool, point the server at it, and Claude handles the rest.

## Requirements

### Active
- [x] MCP server with 5 tools: view_makera_window, list_windows, capture_region, analyze_step_file, query_tools
- [x] Cross-platform window capture (Windows/macOS/Linux)
- [x] Lightweight STEP parser (AP214/AP242, no OpenCASCADE)
- [x] Carvera tool library loader from Makera CSV exports
- [x] Query tools by min radius, material, operation

### Out of Scope
- Direct G-code execution or machine control
- Real-time machine status (tool position, job progress)
- CAD modeling features
- Cloud dependencies

## Migration History

This project was restructured from fusion360-cam-assistant, which built a
Fusion 360 add-in extension via AuraFriday's Fusion-360-MCP-Server. That
approach required Fusion 360 to be open with the MCP-Link add-in installed.

The new architecture is fully standalone: the MCP server runs as a Python
process, reads STEP files directly, captures windows via OS APIs, and loads
tool data from CSV files.

## Technical Architecture

```
Claude Desktop / Claude Code
         |  MCP protocol (stdio)
         v
+-----------------------------+
|      carvera-vision         |
|   MCP Server (server.py)    |
+-----------------------------+
| view_makera_window          |
| list_windows                |
| capture_region              |
|   -> window_capture.py      |  <- pygetwindow/AppleScript/wmctrl + mss
| analyze_step_file           |
|   -> step_parser.py         |  <- pure regex, no kernel
| query_tools                 |
|   -> tool_library.py        |  <- CSV loader
+-----------------------------+
         |
   tools/carvera/*.csv
   (Makera tool profiles)
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No CAD kernel dependency | OpenCASCADE adds 200-500MB; bbox + face types via regex is sufficient |
| Stdio MCP transport | Works with both Claude Desktop and Claude Code without network setup |
| CSV tool library | Makera already publishes Fusion 360 CSV exports; no custom format needed |
| Tool-agnostic STEP input | Works with any CAD exporter, no add-in required |
| Cross-platform window detection | pygetwindow (Windows), AppleScript (macOS), wmctrl (Linux) |

---
*Last updated: 2026-03-20 — restructured from fusion360-cam-assistant*
