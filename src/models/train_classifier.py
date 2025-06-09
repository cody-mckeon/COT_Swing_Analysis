import argparse
import pandas as pd
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import clone
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from pathlib import Path


def train_and_evaluate(features_csv: str, model_out: str) -> None:
    """Train classifiers using a features CSV produced by the classification builder."""
    df = pd.read_csv(features_csv)
    if "target_dir" not in df.columns:
        raise ValueError("features CSV must contain 'target_dir' column")

    y = df["target_dir"]
    X_numeric = df.drop(
        columns=[
            "target_dir",
            "market_name",
            "contract_code",
            "week",
            "report_date",
        ],
        errors="ignore",
    )

    numeric_cols = X_numeric.select_dtypes(include="number").columns.tolist()
    cat_cols = ["market_name"] if "market_name" in df.columns else []
    X = pd.concat([X_numeric[numeric_cols], df[cat_cols]], axis=1)

    n_splits = 5 if len(X) > 6 else max(2, len(X) - 1)
    tscv = TimeSeriesSplit(n_splits=n_splits)

    classifiers = {
        'LogisticRegression': LogisticRegression(max_iter=1000),
        'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42)
    }

    summary = {}

    for name, clf in classifiers.items():
        metrics = {'accuracy': [], 'precision': [], 'recall': [], 'f1': []}
        fold = 1
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            transformers = [('num', StandardScaler(), numeric_cols)]
            if cat_cols:
                transformers.append(
                    (
                        'cat',
                        OneHotEncoder(handle_unknown='ignore'),
                        cat_cols,
                    )
                )
            preprocess = ColumnTransformer(transformers)

            pipe = Pipeline([
                ('preprocess', preprocess),
                ('clf', clone(clf)),
            ])

            pipe.fit(X_train, y_train)
            preds = pipe.predict(X_test)

            metrics['accuracy'].append(accuracy_score(y_test, preds))
            metrics['precision'].append(precision_score(y_test, preds, zero_division=0))
            metrics['recall'].append(recall_score(y_test, preds, zero_division=0))
            metrics['f1'].append(f1_score(y_test, preds, zero_division=0))

            print(f"{name} Fold {fold}: "
                  f"acc={metrics['accuracy'][-1]:.3f} "
                  f"precision={metrics['precision'][-1]:.3f} "
                  f"recall={metrics['recall'][-1]:.3f} "
                  f"F1={metrics['f1'][-1]:.3f}")
            fold += 1

        mean_metrics = {k: sum(v)/len(v) for k, v in metrics.items()}
        print(f"{name} Mean: "
              f"acc={mean_metrics['accuracy']:.3f} "
              f"precision={mean_metrics['precision']:.3f} "
              f"recall={mean_metrics['recall']:.3f} "
              f"F1={mean_metrics['f1']:.3f}")
        summary[name] = (mean_metrics['f1'], clf)

    # select best model by mean F1
    best_name, (best_f1, best_clf) = max(summary.items(), key=lambda x: x[1][0])

    transformers = [('num', StandardScaler(), numeric_cols)]
    if cat_cols:
        transformers.append(
            (
                'cat',
                OneHotEncoder(handle_unknown='ignore'),
                cat_cols,
            )
        )
    final_preprocess = ColumnTransformer(transformers)

    final_pipe = Pipeline([
        ('preprocess', final_preprocess),
        ('clf', best_clf),
    ])

    final_pipe.fit(X, y)

    Path(model_out).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipe, model_out)
    print(f"Best model: {best_name} with mean F1={best_f1:.3f}")
    print(f"Model saved to {model_out}")


def main():
    parser = argparse.ArgumentParser(description="Train classifiers on feature set")
    parser.add_argument('--features', default='data/processed/class_features.csv',
                        help='Path to classification features CSV')
    parser.add_argument('--model-out', default='models/best_model.pkl',
                        help='Path to save the best model pickle')
    args = parser.parse_args()
    train_and_evaluate(args.features, args.model_out)


if __name__ == "__main__":
    main()
