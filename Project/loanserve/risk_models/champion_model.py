"""Bounded model search and an operating threshold chosen by business cost."""

import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import GridSearchCV, StratifiedKFold

from config.constants import (
    COST_OF_A_MISSED_DEFAULT_INR, COST_OF_A_REFUSED_GOOD_APPLICANT_INR,
    CROSS_VALIDATION_FOLDS, RANDOM_SEED,
)
from loanserve.risk_models.baseline_model import build_baseline_model, save_model
from loanserve.risk_models.feature_pipeline import split_for_modelling
from loanserve.risk_models.tree_models import build_random_forest


def candidate_grids():
    return {
        "random_forest": (
            build_random_forest(),
            {"classify__max_depth": [8, 9], "classify__min_samples_leaf": [15, 20]},
        ),
        "logistic_baseline": (build_baseline_model(), {"classify__C": [0.1, 1.0]}),
    }


def search_for_the_champion(cleaned_file_path, output_path):
    fitting, _, target, _ = split_for_modelling(cleaned_file_path)
    folds = StratifiedKFold(n_splits=CROSS_VALIDATION_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    candidates = {}
    for name, (model, grid) in candidate_grids().items():
        search = GridSearchCV(model, grid, scoring="roc_auc", cv=folds, n_jobs=1, refit=True)
        search.fit(fitting, target)
        candidates[name] = {
            "model": search.best_estimator_, "settings": search.best_params_,
            "mean_roc_auc": round(float(search.best_score_), 4),
        }
    champion = max(candidates, key=lambda name: candidates[name]["mean_roc_auc"])
    recorded = {
        "champion": champion,
        "candidates": {name: {"settings": result["settings"], "mean_roc_auc": result["mean_roc_auc"]}
                       for name, result in candidates.items()},
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(recorded, indent=2))
    return champion, candidates


def cost_of_a_threshold(default_scores, actual_outcomes, threshold):
    scores = np.asarray(default_scores)
    outcomes = np.asarray(actual_outcomes)
    missed = int(((scores < threshold) & (outcomes == 1)).sum())
    refused_good = int(((scores >= threshold) & (outcomes == 0)).sum())
    return {
        "threshold": round(float(threshold), 2),
        "missed_defaults": missed,
        "refused_good_applicants": refused_good,
        "total_cost_inr": missed * COST_OF_A_MISSED_DEFAULT_INR + refused_good * COST_OF_A_REFUSED_GOOD_APPLICANT_INR,
    }


def choose_threshold_on_cost(champion, cleaned_file_path, output_path):
    _, holdout, _, actual = split_for_modelling(cleaned_file_path)
    scores = champion.predict_proba(holdout)[:, 1]
    swept = [cost_of_a_threshold(scores, actual, step / 100) for step in range(5, 96, 5)]
    winner = min(swept, key=lambda row: row["total_cost_inr"])
    result = {
        "chosen_threshold": winner["threshold"],
        "cost_at_chosen_inr": winner["total_cost_inr"],
        "cost_at_half_inr": cost_of_a_threshold(scores, actual, 0.5)["total_cost_inr"],
        "swept": swept,
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    source = "processed_data/loan_applications_cleaned.csv"
    name, candidates = search_for_the_champion(source, "output/champion_search.json")
    for candidate, detail in candidates.items():
        print(candidate, detail["mean_roc_auc"], detail["settings"])
    champion = candidates[name]["model"]
    print("champion:", name, "saved:", save_model(champion, "artifacts/champion.pkl"))
    print(choose_threshold_on_cost(champion, source, "output/threshold_choice.json"))
