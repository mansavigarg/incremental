"""Decision tree and forest measured on the shared holdout."""

import json
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from config.constants import RANDOM_SEED
from loanserve.risk_models.feature_pipeline import build_feature_pipeline, split_for_modelling
from loanserve.risk_models.baseline_model import save_model


def build_decision_tree():
    return Pipeline([
        ("prepare", build_feature_pipeline()),
        ("classify", DecisionTreeClassifier(max_depth=7, min_samples_leaf=30,
                                            class_weight="balanced", random_state=RANDOM_SEED)),
    ])


def build_random_forest(extra_numeric=(), extra_categorical=()):
    return Pipeline([
        ("prepare", build_feature_pipeline(extra_numeric, extra_categorical)),
        ("classify", RandomForestClassifier(n_estimators=120, max_depth=9,
                                             min_samples_leaf=20, class_weight="balanced",
                                             random_state=RANDOM_SEED, n_jobs=-1)),
    ])


def train_and_score(model, cleaned_file_path):
    fitting, holdout, target, holdout_target = split_for_modelling(cleaned_file_path)
    model.fit(fitting, target)
    return model, round(float(roc_auc_score(holdout_target, model.predict_proba(holdout)[:, 1])), 4)


def feature_importances(fitted_model):
    names = fitted_model.named_steps["prepare"].get_feature_names_out()
    values = fitted_model.named_steps["classify"].feature_importances_
    return pd.DataFrame({"feature": names, "importance": values.round(4)}).sort_values(
        "importance", ascending=False).reset_index(drop=True)


def compare_class_weighting(cleaned_file_path, output_path):
    fitting, holdout, target, holdout_target = split_for_modelling(cleaned_file_path)
    results = {}
    for name, weight in (("balanced", "balanced"), ("none", None)):
        model = build_random_forest()
        model.set_params(classify__class_weight=weight)
        model.fit(fitting, target)
        results[name] = {
            "roc_auc": round(float(roc_auc_score(holdout_target, model.predict_proba(holdout)[:, 1])), 4),
            "defaulters_caught": round(float(recall_score(holdout_target, model.predict(holdout))), 4),
        }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    source = "processed_data/loan_applications_cleaned.csv"
    for name, builder in (("decision_tree", build_decision_tree), ("random_forest", build_random_forest)):
        model, score = train_and_score(builder(), source)
        print(f"{name} holdout ROC-AUC: {score}")
        print(f"saved: {save_model(model, f'artifacts/{name}.pkl')}")
        if name == "random_forest":
            print(feature_importances(model).head(5).to_string(index=False))
    print(compare_class_weighting(source, "output/class_weight_comparison.json"))
