"""Save/load helpers for next-version tolerance projects."""

from __future__ import annotations

import json
from pathlib import Path

from .tolerance_models import ToleranceProject


PROJECT_SUFFIX = ".tolproj"


def save_project(project: ToleranceProject, path: str | Path) -> Path:
    output_path = Path(path)
    if output_path.suffix.lower() != PROJECT_SUFFIX:
        output_path = output_path.with_suffix(PROJECT_SUFFIX)
    output_path.write_text(
        json.dumps(project.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def load_project(path: str | Path) -> ToleranceProject:
    input_path = Path(path)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Tolerance project file must contain a JSON object.")
    return ToleranceProject.from_dict(data)
