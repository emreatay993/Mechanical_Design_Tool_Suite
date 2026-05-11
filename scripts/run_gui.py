"""Launch the prototype bolt calculation GUI from a source checkout."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path = [path for path in sys.path if path != str(SRC)]
sys.path.insert(0, str(SRC))

from bolt_calculation_tool.gui import main


if __name__ == "__main__":
    main()
