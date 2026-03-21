"""
Carvera Vision MCP Server.

Five tools:
  view_makera_window  — auto-detect and capture the MakeraCam/Carvera window
  list_windows        — list all open windows (debug / fallback)
  capture_region      — capture an arbitrary screen region by coordinates
  analyze_step_file   — parse a STEP file and return structured geometry data
  query_tools         — query the Carvera tool library by radius/material/op
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .step_parser import parse_step
from .tool_library import load_tool_library, query_tools as _query_tools
from .window_capture import (
    WindowInfo,
    capture_window,
    find_makera_window,
    list_all_windows,
)

# ── Tool library (loaded once at startup) ──────────────────────────────────────
_TOOLS_DIR = Path(__file__).parent.parent.parent / "tools" / "carvera"
_tool_profiles: list = []


def _ensure_tools_loaded() -> None:
    global _tool_profiles
    if not _tool_profiles and _TOOLS_DIR.exists():
        _tool_profiles = load_tool_library(_TOOLS_DIR)


# ── Server ─────────────────────────────────────────────────────────────────────
app = Server("carvera-vision")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="view_makera_window",
            description=(
                "Captures a screenshot of the MakeraCam or Carvera CAM software window. "
                "Use this whenever the user asks about their current toolpath, "
                "material settings, feeds & speeds, stock setup, or any other "
                "configuration visible in MakeraCam. Returns the window as an image "
                "so you can see exactly what they see."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scale": {
                        "type": "number",
                        "description": (
                            "Image scale factor. Default 1.0 (full resolution). "
                            "Use 0.5 for large 4K displays to reduce token usage "
                            "while keeping the UI readable."
                        ),
                        "default": 1.0,
                        "minimum": 0.25,
                        "maximum": 1.0,
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="list_windows",
            description=(
                "Lists all currently open window titles on the system. "
                "Useful for debugging if view_makera_window cannot find the window, "
                "or to confirm MakeraCam is running."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="capture_region",
            description=(
                "Captures an arbitrary region of the screen by pixel coordinates. "
                "Use this as a fallback if view_makera_window cannot auto-detect the window, "
                "or to zoom in on a specific area such as the feeds panel, tool library, "
                "or stock dimensions dialog."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "left": {"type": "integer", "description": "Left edge in screen pixels."},
                    "top": {"type": "integer", "description": "Top edge in screen pixels."},
                    "width": {"type": "integer", "description": "Width in pixels."},
                    "height": {"type": "integer", "description": "Height in pixels."},
                    "scale": {
                        "type": "number",
                        "description": "Scale factor (0.25–1.0). Default 1.0.",
                        "default": 1.0,
                        "minimum": 0.25,
                        "maximum": 1.0,
                    },
                },
                "required": ["left", "top", "width", "height"],
            },
        ),
        types.Tool(
            name="analyze_step_file",
            description=(
                "Parse a STEP file (.step or .stp) and return structured geometry intelligence: "
                "bounding box, part dimensions, face type inventory, coordinate systems "
                "(potential WCS datums), estimated minimum internal radius, and tool "
                "recommendations. Works with STEP files from Fusion 360, Plasticity, "
                "Shapr3D, or any other CAD tool — no CAD software needs to be open."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the STEP file (.step or .stp)",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Include raw entity type counts in output (default false)",
                        "default": False,
                    },
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="query_tools",
            description=(
                "Query the Carvera tool library for suitable tools. Filter by minimum "
                "radius constraint (from analyze_step_file), material, and operation type. "
                "Returns a ranked list of matching tools with feeds and speeds."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "min_radius": {
                        "type": "number",
                        "description": "Minimum internal feature radius (mm) — only tools that fit are returned",
                    },
                    "material": {
                        "type": "string",
                        "description": "Material hint: aluminum, wood, plastic, copper, brass, pcb, steel",
                    },
                    "operation": {
                        "type": "string",
                        "description": "Operation hint: roughing, finishing, drilling, engraving, profiling, pocketing",
                    },
                },
                "required": [],
            },
        ),
    ]


# ── Tool dispatch ──────────────────────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
    if name == "view_makera_window":
        return await _tool_view_makera(arguments)
    elif name == "list_windows":
        return await _tool_list_windows()
    elif name == "capture_region":
        return await _tool_capture_region(arguments)
    elif name == "analyze_step_file":
        return await _tool_analyze_step(arguments)
    elif name == "query_tools":
        return await _tool_query_tools(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


# ── Vision tools ───────────────────────────────────────────────────────────────

async def _tool_view_makera(args: dict[str, Any]) -> list[types.ContentBlock]:
    scale = float(args.get("scale", 1.0))
    window = find_makera_window()

    if window is None:
        windows = list_all_windows()
        window_list = (
            "\n".join(f"  \u2022 {t}" for t in windows[:30])
            if windows
            else "  (no windows found)"
        )
        return [
            types.TextContent(
                type="text",
                text=(
                    "MakeraCam window not found. Make sure MakeraCam (or the Carvera "
                    "software) is open and not minimised.\n\n"
                    f"Currently visible windows:\n{window_list}\n\n"
                    "If MakeraCam is listed above under a different name, add the title "
                    "substring to MAKERA_WINDOW_ALIASES in "
                    "src/carvera_vision/window_capture.py."
                ),
            )
        ]

    b64, width, height = capture_window(window, scale=scale)
    return [
        types.TextContent(
            type="text",
            text=(
                f'Captured MakeraCam window: "{window.title}" '
                f"({width}\u00d7{height}px, scale={scale})"
            ),
        ),
        types.ImageContent(type="image", data=b64, mimeType="image/png"),
    ]


async def _tool_list_windows() -> list[types.ContentBlock]:
    windows = list_all_windows()
    if not windows:
        return [
            types.TextContent(
                type="text",
                text="No open windows detected. This may be a permissions issue.",
            )
        ]
    joined = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(windows))
    return [
        types.TextContent(
            type="text",
            text=f"Open windows ({len(windows)} total):\n{joined}",
        )
    ]


async def _tool_capture_region(args: dict[str, Any]) -> list[types.ContentBlock]:
    left = int(args["left"])
    top = int(args["top"])
    width = int(args["width"])
    height = int(args["height"])
    scale = float(args.get("scale", 1.0))

    if width <= 0 or height <= 0:
        return [
            types.TextContent(
                type="text",
                text="Invalid region: width and height must be positive.",
            )
        ]

    window = WindowInfo(
        title="manual region", left=left, top=top, width=width, height=height
    )
    b64, out_w, out_h = capture_window(window, scale=scale)
    return [
        types.TextContent(
            type="text",
            text=f"Captured region ({left},{top}) {width}\u00d7{height}px \u2192 output {out_w}\u00d7{out_h}px",
        ),
        types.ImageContent(type="image", data=b64, mimeType="image/png"),
    ]


# ── STEP + tool library ────────────────────────────────────────────────────────

async def _tool_analyze_step(args: dict[str, Any]) -> list[types.ContentBlock]:
    file_path = args.get("file_path", "")
    verbose = bool(args.get("verbose", False))

    path = Path(file_path)
    if not path.exists():
        return [types.TextContent(type="text", text=f"File not found: {file_path}")]
    if path.suffix.lower() not in (".step", ".stp"):
        return [
            types.TextContent(
                type="text",
                text=f"Expected a .step or .stp file, got: {path.suffix}",
            )
        ]

    try:
        geom = parse_step(path)
    except Exception as e:
        return [types.TextContent(type="text", text=f"Failed to parse STEP file: {e}")]

    result = geom.to_dict(verbose=verbose)

    if geom.bounding_box:
        bb = geom.bounding_box
        result["dimensions_summary"] = (
            f"{bb.x_size:.2f} \u00d7 {bb.y_size:.2f} \u00d7 {bb.z_size:.2f} {geom.units}"
        )

    _ensure_tools_loaded()
    if _tool_profiles and geom.min_internal_radius is not None:
        recs = _query_tools(_tool_profiles, min_radius=geom.min_internal_radius)
        seen_names: set[str] = set()
        unique_recs = []
        for t in recs:
            if t["name"] not in seen_names:
                seen_names.add(t["name"])
                unique_recs.append(t)
                if len(unique_recs) == 5:
                    break
        result["recommended_tools"] = unique_recs

    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


async def _tool_query_tools(args: dict[str, Any]) -> list[types.ContentBlock]:
    _ensure_tools_loaded()

    if not _tool_profiles:
        return [
            types.TextContent(
                type="text",
                text=(
                    f"Tool library not found at {_TOOLS_DIR}.\n"
                    "Make sure the Makera CSV files are present in tools/carvera/."
                ),
            )
        ]

    min_radius_raw = args.get("min_radius")
    material: Optional[str] = args.get("material")
    operation: Optional[str] = args.get("operation")
    min_radius = float(min_radius_raw) if min_radius_raw is not None else None

    results = _query_tools(
        _tool_profiles,
        min_radius=min_radius,
        material=material,
        operation=operation,
    )

    if not results:
        return [
            types.TextContent(
                type="text",
                text="No tools matched the given constraints. Try relaxing the filters.",
            )
        ]

    output = {
        "query": {"min_radius_mm": min_radius, "material": material, "operation": operation},
        "results_count": len(results),
        "tools": results,
    }
    return [types.TextContent(type="text", text=json.dumps(output, indent=2))]


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    asyncio.run(_run())


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    main()
