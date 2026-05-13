"""Display styling defaults for the CAD 1D tolerance viewer."""

from __future__ import annotations

from collections.abc import Sequence


ENGINEERING_PART_PALETTE: tuple[tuple[int, int, int], ...] = (
    (66, 84, 150),  # muted blue top plates and covers
    (165, 109, 61),  # bronze/copper brackets and supports
    (217, 196, 116),  # warm yellow wheel-like rotating parts
    (38, 42, 43),  # dark rubber or shadowed support parts
    (69, 143, 146),  # teal bushings and bearing inserts
    (111, 124, 140),  # neutral steel shafts and pins
    (96, 78, 60),  # dark bronze secondary supports
    (135, 131, 105),  # muted machined alloy
)

_COLOR_HINTS: tuple[tuple[tuple[str, ...], tuple[int, int, int]], ...] = (
    (("top", "plate", "cover"), ENGINEERING_PART_PALETTE[0]),
    (("support", "bracket", "fork"), ENGINEERING_PART_PALETTE[1]),
    (("wheel", "roller"), ENGINEERING_PART_PALETTE[2]),
    (("tire", "rubber"), ENGINEERING_PART_PALETTE[3]),
    (("bushing", "bearing", "insert"), ENGINEERING_PART_PALETTE[4]),
    (("axle", "shaft", "pin"), ENGINEERING_PART_PALETTE[5]),
)


def display_color_for_part(name: str, one_based_index: int) -> tuple[int, int, int]:
    """Return a stable display color for imported CAD body metadata."""

    name_lower = name.casefold()
    for tokens, color in _COLOR_HINTS:
        if any(token in name_lower for token in tokens):
            return color
    palette_index = (max(one_based_index, 1) - 1) % len(ENGINEERING_PART_PALETTE)
    return ENGINEERING_PART_PALETTE[palette_index]


def normalize_rgb_triplet(values: Sequence[float | int]) -> tuple[int, int, int]:
    """Coerce RGB bytes, clamping invalid channel values to 0..255."""

    red, green, blue = values[:3]
    return (_rgb_channel(red), _rgb_channel(green), _rgb_channel(blue))


def rgb_bytes_to_unit(values: Sequence[float | int]) -> tuple[float, float, float]:
    """Convert RGB byte channels to OCCT-compatible 0..1 float channels."""

    red, green, blue = normalize_rgb_triplet(values)
    return (red / 255.0, green / 255.0, blue / 255.0)


def _rgb_channel(value: float | int) -> int:
    return max(0, min(255, int(round(float(value)))))
