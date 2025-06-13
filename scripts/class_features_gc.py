import os
import sys
from pathlib import Path

# ensure src is importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

import argparse
from src.data.build_classification_features import build_classification_features


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build classification-ready features for Gold"
    )
    parser.add_argument(
        "--features",
        default=str(Path("data/processed/features_gc.csv")),
        help="Input features CSV",
    )
    parser.add_argument(
        "--out",
        default=str(Path("data/processed/class_features_gc.csv")),
        help="Output CSV path",
    )
    parser.add_argument("--th", type=float, default=0.0, help="Return threshold")
    args = parser.parse_args()

    build_classification_features(args.features, args.out, args.th)


if __name__ == "__main__":
    main()
