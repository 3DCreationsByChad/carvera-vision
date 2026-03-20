"""Lightweight STEP file parser (AP214/AP242 ASCII format).

Parses STEP files using pure text/regex — no OpenCASCADE or geometry kernel
required. Extracts the information Claude needs to reason about a part:
bounding box, face type inventory, coordinate systems, and minimum internal
tool radius.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BoundingBox:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float

    @property
    def x_size(self) -> float:
        return self.x_max - self.x_min

    @property
    def y_size(self) -> float:
        return self.y_max - self.y_min

    @property
    def z_size(self) -> float:
        return self.z_max - self.z_min

    def to_dict(self) -> dict:
        return {
            "min": {"x": round(self.x_min, 4), "y": round(self.y_min, 4), "z": round(self.z_min, 4)},
            "max": {"x": round(self.x_max, 4), "y": round(self.y_max, 4), "z": round(self.z_max, 4)},
            "size": {"x": round(self.x_size, 4), "y": round(self.y_size, 4), "z": round(self.z_size, 4)},
        }


@dataclass
class CoordinateSystem:
    label: str  # e.g. "#42"
    origin: tuple[float, float, float]
    axis: Optional[tuple[float, float, float]] = None       # Z-axis direction
    ref_direction: Optional[tuple[float, float, float]] = None  # X-axis direction

    def to_dict(self) -> dict:
        result: dict = {
            "entity": self.label,
            "origin": [round(v, 4) for v in self.origin],
        }
        if self.axis:
            result["z_axis"] = [round(v, 4) for v in self.axis]
        if self.ref_direction:
            result["x_axis"] = [round(v, 4) for v in self.ref_direction]
        return result


@dataclass
class FaceInventory:
    plane: int = 0
    cylindrical_surface: int = 0
    conical_surface: int = 0
    toroidal_surface: int = 0
    b_spline_surface: int = 0

    @property
    def total(self) -> int:
        return (
            self.plane
            + self.cylindrical_surface
            + self.conical_surface
            + self.toroidal_surface
            + self.b_spline_surface
        )

    def to_dict(self) -> dict:
        return {
            "plane": self.plane,
            "cylindrical_surface": self.cylindrical_surface,
            "conical_surface": self.conical_surface,
            "toroidal_surface": self.toroidal_surface,
            "b_spline_surface": self.b_spline_surface,
            "total": self.total,
        }


@dataclass
class StepGeometry:
    part_name: str
    units: str
    bounding_box: Optional[BoundingBox]
    face_inventory: FaceInventory
    coordinate_systems: list[CoordinateSystem]
    min_internal_radius: Optional[float]
    entity_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self, verbose: bool = False) -> dict:
        result: dict = {
            "part_name": self.part_name,
            "units": self.units,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "face_inventory": self.face_inventory.to_dict(),
            "coordinate_systems": [cs.to_dict() for cs in self.coordinate_systems],
            "min_internal_radius": (
                round(self.min_internal_radius, 4)
                if self.min_internal_radius is not None
                else None
            ),
        }
        if verbose:
            result["entity_counts"] = self.entity_counts
        return result


# ── Parsing helpers ────────────────────────────────────────────────────────────

# Match STEP data lines: #N = ENTITY_TYPE(args);
_ENTITY_RE = re.compile(
    r"#(\d+)\s*=\s*([A-Z_0-9]+)\s*\(([^;]*)\)\s*;",
    re.DOTALL,
)
_FLOAT_RE = re.compile(r"[-+]?\d+\.?\d*(?:[Ee][-+]?\d+)?")


def _floats(text: str) -> list[float]:
    """Extract all float values from a STEP argument string."""
    return [float(m) for m in _FLOAT_RE.findall(text)]


def _strings(text: str) -> list[str]:
    """Extract all single-quoted strings from a STEP argument list."""
    return re.findall(r"'([^']*)'", text)


def _refs(text: str) -> list[int]:
    """Extract all entity references (#N) from a STEP argument list."""
    return [int(m) for m in re.findall(r"#(\d+)", text)]


# ── Main parser ────────────────────────────────────────────────────────────────


def parse_step(path: str | Path) -> StepGeometry:
    """
    Parse a STEP AP214/AP242 ASCII file and return a StepGeometry dataclass.

    Reads the DATA section only. Works on files of any size. The STEP format
    is plain ASCII so regex-based extraction is reliable and fast.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")

    # Extract DATA section only (skip HEADER)
    data_match = re.search(
        r"DATA\s*;(.*?)END-DATA\s*;", text, re.DOTALL | re.IGNORECASE
    )
    data_section = data_match.group(1) if data_match else text

    # Build entity map: id -> (type_name, args_string)
    entities: dict[int, tuple[str, str]] = {}
    for m in _ENTITY_RE.finditer(data_section):
        eid = int(m.group(1))
        etype = m.group(2).upper()
        eargs = m.group(3)
        entities[eid] = (etype, eargs)

    # ── Part name ──────────────────────────────────────────────────────────────
    part_name = "unknown"
    for _eid, (etype, eargs) in entities.items():
        if etype == "PRODUCT":
            names = _strings(eargs)
            if names:
                part_name = names[0]
                break

    # ── Units ──────────────────────────────────────────────────────────────────
    units = "mm"
    for _eid, (etype, eargs) in entities.items():
        if etype == "CONVERSION_BASED_UNIT":
            unit_str = " ".join(_strings(eargs)).lower()
            if "inch" in unit_str or '"' in unit_str:
                units = "inches"
            break
        if etype == "SI_UNIT":
            if "MILLI" in eargs and "METRE" in eargs:
                units = "mm"
            elif "METRE" in eargs:
                units = "m"
            break

    # ── Cartesian points → bounding box ────────────────────────────────────────
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for _eid, (etype, eargs) in entities.items():
        if etype == "CARTESIAN_POINT":
            nums = _floats(eargs)
            if len(nums) >= 3:
                xs.append(nums[0])
                ys.append(nums[1])
                zs.append(nums[2])

    bbox: Optional[BoundingBox] = None
    if xs and ys and zs:
        bbox = BoundingBox(
            x_min=min(xs), x_max=max(xs),
            y_min=min(ys), y_max=max(ys),
            z_min=min(zs), z_max=max(zs),
        )

    # ── Face inventory + radii ─────────────────────────────────────────────────
    inv = FaceInventory()
    surface_radii: list[float] = []

    for _eid, (etype, eargs) in entities.items():
        if etype == "PLANE":
            inv.plane += 1
        elif etype == "CYLINDRICAL_SURFACE":
            inv.cylindrical_surface += 1
            nums = _floats(eargs)
            if nums:
                surface_radii.append(nums[-1])
        elif etype == "CONICAL_SURFACE":
            inv.conical_surface += 1
        elif etype == "TOROIDAL_SURFACE":
            inv.toroidal_surface += 1
            nums = _floats(eargs)
            if len(nums) >= 2:
                surface_radii.append(min(nums[-2:]))
        elif etype in (
            "B_SPLINE_SURFACE",
            "B_SPLINE_SURFACE_WITH_KNOTS",
            "RATIONAL_B_SPLINE_SURFACE",
        ):
            inv.b_spline_surface += 1

    for _eid, (etype, eargs) in entities.items():
        if etype == "CIRCLE":
            nums = _floats(eargs)
            if nums:
                surface_radii.append(nums[-1])

    min_internal_radius: Optional[float] = min(surface_radii) if surface_radii else None

    # ── Coordinate systems ─────────────────────────────────────────────────────
    point_map: dict[int, tuple[float, float, float]] = {}
    direction_map: dict[int, tuple[float, float, float]] = {}
    for eid, (etype, eargs) in entities.items():
        if etype == "CARTESIAN_POINT":
            nums = _floats(eargs)
            if len(nums) >= 3:
                point_map[eid] = (nums[0], nums[1], nums[2])
        elif etype == "DIRECTION":
            nums = _floats(eargs)
            if len(nums) >= 3:
                direction_map[eid] = (nums[0], nums[1], nums[2])

    coord_systems: list[CoordinateSystem] = []
    for eid, (etype, eargs) in entities.items():
        if etype == "AXIS2_PLACEMENT_3D":
            refs = _refs(eargs)
            origin = point_map.get(refs[0]) if refs else None
            axis = direction_map.get(refs[1]) if len(refs) > 1 else None
            ref_dir = direction_map.get(refs[2]) if len(refs) > 2 else None
            if origin:
                coord_systems.append(
                    CoordinateSystem(
                        label=f"#{eid}",
                        origin=origin,
                        axis=axis,
                        ref_direction=ref_dir,
                    )
                )

    # ── Entity counts (verbose mode) ───────────────────────────────────────────
    entity_counts: dict[str, int] = {}
    for _eid, (etype, _eargs) in entities.items():
        entity_counts[etype] = entity_counts.get(etype, 0) + 1

    return StepGeometry(
        part_name=part_name,
        units=units,
        bounding_box=bbox,
        face_inventory=inv,
        coordinate_systems=coord_systems,
        min_internal_radius=min_internal_radius,
        entity_counts=entity_counts,
    )
