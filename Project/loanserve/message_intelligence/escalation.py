"""Combine urgency, sentiment and verified exposure into review decisions."""

from pathlib import Path

from joblib import load as load_model
import pandas as pd

from config.constants import LARGE_EXPOSURE_INR, UNHAPPY_SENTIMENTS, VERY_LARGE_EXPOSURE_INR
from loanserve.data_access.database_loader import ApplicationDatabase
from loanserve.message_intelligence.llm_client import analyse_thread
from loanserve.message_intelligence.message_classifier import classify_message


SENTIMENT_NOT_ASKED = "not_asked"


def exposure_for(application_reference, database):
    record = database.find_application(application_reference)
    return int(record["loan_amount_inr"]) if record is not None else 0


def escalation_reasons(urgency, sentiment, exposure_inr):
    reasons = []
    if urgency == "high":
        reasons.append("high urgency")
    if sentiment in UNHAPPY_SENTIMENTS:
        reasons.append(f"customer sounds {sentiment}")
    if exposure_inr >= LARGE_EXPOSURE_INR:
        reasons.append("large exposure")
    return reasons


def must_be_seen_by_a_person(reasons, exposure_inr):
    return exposure_inr >= VERY_LARGE_EXPOSURE_INR or len(reasons) >= 2


def build_escalation_report(summaries_path, classifier_path, database_path, output_path, limit=None):
    summaries = pd.read_csv(summaries_path)
    if limit is not None:
        summaries = summaries.head(limit)
    models = load_model(classifier_path)
    database = ApplicationDatabase(database_path)
    rows = []
    for thread in summaries.itertuples(index=False):
        urgency = classify_message(models, thread.summary)["urgency"]
        exposure = exposure_for(thread.application_reference, database)
        sentiment = SENTIMENT_NOT_ASKED
        settled = escalation_reasons(urgency, sentiment, exposure)
        if len(settled) == 1 and exposure < VERY_LARGE_EXPOSURE_INR:
            from loanserve.message_intelligence import llm_client
            sentiment = llm_client.analyse_thread(thread.summary)["sentiment"]
        reasons = escalation_reasons(urgency, sentiment, exposure)
        rows.append({
            "thread_id": thread.thread_id, "application_reference": thread.application_reference,
            "category": thread.category, "urgency": urgency, "sentiment": sentiment,
            "exposure_inr": exposure, "escalate": must_be_seen_by_a_person(reasons, exposure),
            "reasons": "; ".join(reasons),
        })
    database.connection.close()
    result = pd.DataFrame(rows)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination, index=False)
    return result


if __name__ == '__main__':
    report = build_escalation_report(
        'output/thread_summaries.csv', 'artifacts/message_classifier.pkl',
        'database/loanserve.db', 'output/escalation_report.csv', limit=30,
    )
    print('conversations reviewed:', len(report), 'escalations:', int(report['escalate'].sum()))
