"""Score every waiting loan and order the officer's work by risk."""

import json
from pathlib import Path

import pandas as pd

from loanserve.risk_models.baseline_model import load_model, predict_default_probability


def score_waiting_applications(champion, waiting_file_path):
    waiting = pd.read_csv(waiting_file_path)
    return pd.DataFrame({
        "application_id": waiting["application_id"],
        "default_probability": predict_default_probability(champion, waiting).round(6),
        "loan_amount_inr": waiting["loan_amount_inr"],
        "monthly_installment_inr": waiting["monthly_installment_inr"],
        "installment_to_income": waiting["installment_to_income"],
        "credit_band": waiting["credit_band"],
    })


def build_work_queue(champion, waiting_file_path, threshold_path, output_path):
    threshold = json.loads(Path(threshold_path).read_text())["chosen_threshold"]
    queue = score_waiting_applications(champion, waiting_file_path).sort_values(
        "default_probability", ascending=False
    ).reset_index(drop=True)
    queue["decision"] = queue["default_probability"].ge(threshold).map({True: "refer", False: "approve"})
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(destination, index=False)
    return queue


def queue_summary(queue_path):
    queue = pd.read_csv(queue_path)
    referred = queue.loc[queue["decision"].eq("refer")]
    exposure = int(referred["loan_amount_inr"].sum())
    total = queue["loan_amount_inr"].sum()
    return {
        "waiting": int(len(queue)), "referred": int(len(referred)),
        "approved": int(len(queue) - len(referred)),
        "exposure_referred_inr": exposure,
        "share_of_exposure_referred": round(float(exposure / total), 4),
    }


if __name__ == "__main__":
    queue = build_work_queue(
        load_model("artifacts/champion.pkl"),
        "processed_data/loan_applications_predict_enriched.csv",
        "output/threshold_choice.json", "output/work_queue.csv",
    )
    print(queue.head(5).to_string(index=False))
    print(queue_summary("output/work_queue.csv"))
