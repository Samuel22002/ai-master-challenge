"""Package paths for submissions/samuel/solution/scripts/.

The raw CSVs are NOT shipped (Kaggle dataset, MIT licence; see solution/data/README.md).
Point RAVENSTACK_DATA to the folder with the five ravenstack_*.csv files, or place them in
solution/data/ravenstack/.
"""
from __future__ import annotations

import os
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]          # submissions/samuel
ROOT = PKG
OUTPUTS = PKG / "solution" / "outputs"
RAW_DIR = Path(os.environ.get("RAVENSTACK_DATA", PKG / "solution" / "data" / "ravenstack"))
