import pandas as pd
from pathlib import Path
import argparse


def build_classification_features(in_csv: str, out_csv: str, th: float = 0.0) -> pd.DataFrame:
    """Add binary classification target column to a features CSV."""
    df = pd.read_csv(in_csv)
    if 'return_1w' in df.columns:
        ret_col = 'return_1w'
    elif 'return' in df.columns:
        ret_col = 'return'
    else:
        raise ValueError("Input CSV must contain 'return_1w' or 'return' column")

    df['target_dir'] = (df[ret_col] > th).astype(int)
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Create classification targets")
    parser.add_argument('--in', dest='in_csv', required=True, help='Input features CSV')
    parser.add_argument('--out', dest='out_csv', default='data/processed/class_features.csv', help='Output CSV with target')
    parser.add_argument('--th', type=float, default=0.0, help='Return threshold')
    args = parser.parse_args()
    build_classification_features(args.in_csv, args.out_csv, args.th)


if __name__ == '__main__':
    main()
