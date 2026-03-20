"""Carvera tool library loader and query engine.

Loads Makera CSV tool library exports from tools/carvera/ and returns
ranked tool recommendations based on minimum radius, material, and operation.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Map material hints to Makera CSV preset names
_MATERIAL_ALIASES: dict[str, list[str]] = {
    "aluminum": ["Aluminum", "Aluminium"],
    "aluminium": ["Aluminum", "Aluminium"],
    "wood": ["Softwood", "Hardwood", "Plywood", "MDF"],
    "softwood": ["Softwood"],
    "hardwood": ["Hardwood"],
    "plastic": ["Acrylic", "PVC", "Delrin", "HDPE", "Nylon", "Plastic"],
    "acrylic": ["Acrylic"],
    "copper": ["Copper"],
    "brass": ["Brass"],
    "pcb": ["PCB", "FR4", "Copper", "Brass"],
    "steel": ["Steel", "Mild Steel", "Stainless"],
    "stainless": ["Stainless", "Steel"],
}

# Map operation hints to tool type substrings
_OPERATION_TOOL_TYPES: dict[str, list[str]] = {
    "roughing": ["flat end mill", "square end mill", "o flute", "upcut"],
    "finishing": ["ball end mill", "flat end mill"],
    "drilling": ["drill", "center drill"],
    "engraving": ["v-bit", "engraving", "chamfer"],
    "profiling": ["flat end mill", "square end mill", "o flute"],
    "pocketing": ["flat end mill", "square end mill", "ball end mill"],
}


@dataclass
class ToolProfile:
    name: str
    tool_type: str
    diameter_mm: float
    corner_radius_mm: float
    flute_length_mm: float
    overall_length_mm: float
    num_flutes: int
    material_preset: str
    spindle_rpm: float
    feed_cutting_mm_min: float
    feed_plunge_mm_min: float
    stepdown_mm: float
    stepover_fraction: float
    vendor: str
    source_file: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.tool_type,
            "diameter_mm": self.diameter_mm,
            "corner_radius_mm": self.corner_radius_mm,
            "flute_length_mm": self.flute_length_mm,
            "overall_length_mm": self.overall_length_mm,
            "num_flutes": self.num_flutes,
            "material_preset": self.material_preset,
            "spindle_rpm": self.spindle_rpm,
            "feed_cutting_mm_min": self.feed_cutting_mm_min,
            "feed_plunge_mm_min": self.feed_plunge_mm_min,
            "stepdown_mm": self.stepdown_mm,
            "stepover_fraction": self.stepover_fraction,
            "vendor": self.vendor,
        }


def _safe_float(val: str, default: float = 0.0) -> float:
    try:
        return float(val) if val.strip() else default
    except (ValueError, AttributeError):
        return default


def _safe_int(val: str, default: int = 0) -> int:
    try:
        return int(float(val)) if val.strip() else default
    except (ValueError, AttributeError):
        return default


def load_tool_library(tools_dir: str | Path) -> list[ToolProfile]:
    """Load all Makera CSV tool profiles from the given directory."""
    tools_dir = Path(tools_dir)
    profiles: list[ToolProfile] = []

    for csv_path in sorted(tools_dir.glob("*.csv")):
        try:
            with csv_path.open(encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        profiles.append(
                            ToolProfile(
                                name=row.get("Description (tool_description)", "").strip(),
                                tool_type=row.get("Type (tool_type)", "").strip().lower(),
                                diameter_mm=_safe_float(row.get("Diameter (tool_diameter)", "")),
                                corner_radius_mm=_safe_float(row.get("Corner Radius (tool_cornerRadius)", "")),
                                flute_length_mm=_safe_float(row.get("Flute Length (tool_fluteLength)", "")),
                                overall_length_mm=_safe_float(row.get("Overall Length (tool_overallLength)", "")),
                                num_flutes=_safe_int(row.get("Number of Flutes (tool_numberOfFlutes)", "")),
                                material_preset=row.get("Preset Name (preset_name)", "").strip(),
                                spindle_rpm=_safe_float(row.get("Spindle Speed (tool_spindleSpeed)", "")),
                                feed_cutting_mm_min=_safe_float(row.get("Cutting Feedrate (tool_feedCutting)", "")),
                                feed_plunge_mm_min=_safe_float(row.get("Plunge Feedrate (tool_feedPlunge)", "")),
                                stepdown_mm=_safe_float(row.get("Stepdown (tool_stepdown)", "")),
                                stepover_fraction=_safe_float(row.get("Stepover (tool_stepover)", "")),
                                vendor=row.get("Vendor (tool_vendor)", "Makera").strip(),
                                source_file=csv_path.name,
                            )
                        )
                    except Exception:
                        continue
        except Exception:
            continue

    return profiles


def query_tools(
    profiles: list[ToolProfile],
    min_radius: Optional[float] = None,
    material: Optional[str] = None,
    operation: Optional[str] = None,
) -> list[dict]:
    """
    Query tool profiles by constraints. Returns up to 20 ranked results.

    Args:
        profiles: Full tool library from load_tool_library()
        min_radius: Minimum internal radius of the part (mm). Only tools
                    whose radius <= this value are returned.
        material: Material hint string (e.g. "aluminum", "wood", "pcb")
        operation: Operation hint string (e.g. "roughing", "finishing")

    Returns:
        List of tool dicts sorted by suitability. When radius-constrained,
        tools closest to the constraint are ranked first.
    """
    results = list(profiles)

    if min_radius is not None:
        results = [t for t in results if (t.diameter_mm / 2) <= min_radius]

    if material:
        allowed_presets = _MATERIAL_ALIASES.get(
            material.lower(), [material.capitalize()]
        )
        results = [
            t for t in results
            if any(p.lower() in t.material_preset.lower() for p in allowed_presets)
        ]

    if operation:
        allowed_types = _OPERATION_TOOL_TYPES.get(operation.lower())
        if allowed_types:
            results = [
                t for t in results
                if any(ot in t.tool_type for ot in allowed_types)
            ]

    # Deduplicate by (name, diameter, type, material_preset)
    seen: set[tuple] = set()
    unique: list[ToolProfile] = []
    for t in results:
        key = (t.name, t.diameter_mm, t.tool_type, t.material_preset)
        if key not in seen:
            seen.add(key)
            unique.append(t)

    if min_radius is not None:
        unique.sort(key=lambda t: min_radius - (t.diameter_mm / 2))
    else:
        unique.sort(key=lambda t: t.diameter_mm)

    return [t.to_dict() for t in unique[:20]]
