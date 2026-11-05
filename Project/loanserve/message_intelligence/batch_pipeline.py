"""Process recent messages independently so one malformed row cannot stop a batch."""

from pathlib import Path

import joblib
import pandas as pd

from config.constants import MAXIMUM_MESSAGE_CHARACTERS
from loanserve.data_access.database_loader import ApplicationDatabase
from loanserve.message_intelligence.entity_extraction import extract_entities, link_references
from loanserve.message_intelligence.injection_guard import find_injection_markers
from loanserve.message_intelligence.message_classifier import classify_message


RESULT_COLUMNS = ("category", "urgency", "references_found", "references_not_found", "amounts", "dates")


class UnusableMessage(Exception):
    """One customer message cannot be processed."""


def check_message(message_text):
    if not isinstance(message_text, str) or not message_text.strip():
        raise UnusableMessage("empty message")
    if len(message_text) > MAXIMUM_MESSAGE_CHARACTERS:
        raise UnusableMessage(f"longer than {MAXIMUM_MESSAGE_CHARACTERS} characters")
    if "\ufffd" in message_text:
        raise UnusableMessage("unreadable characters")
    markers = find_injection_markers(message_text)
    if markers:
        raise UnusableMessage("possible prompt injection: " + ", ".join(markers))


def process_message(message_text, models, database):
    check_message(message_text)
    labels = classify_message(models, message_text)
    entities = extract_entities(message_text)
    found, not_found = link_references(entities["references"], database)
    return {
        "category": labels["category"], "urgency": labels["urgency"],
        "references_found": " ".join(found), "references_not_found": " ".join(not_found),
        "amounts": " ".join(map(str, entities["amounts"])),
        "dates": " ".join(entities["dates"]),
    }


def process_batch(messages_file_path, classifier_path, database_path, output_path, batch_size):
    messages = pd.read_csv(messages_file_path).tail(batch_size)
    models = joblib.load(classifier_path)
    database = ApplicationDatabase(database_path)
    rows = []
    for message in messages.itertuples(index=False):
        try:
            values = process_message(message.message_text, models, database)
            rows.append({"message_id": message.message_id, "status": "processed", "failure": "", **values})
        except UnusableMessage as error:
            rows.append({"message_id": message.message_id, "status": "failed", "failure": str(error),
                         **dict.fromkeys(RESULT_COLUMNS, "")})
    database.connection.close()
    result = pd.DataFrame(rows, columns=("message_id", "status", "failure", *RESULT_COLUMNS))
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination, index=False)
    return result


if __name__ == "__main__":
    rows = process_batch("data/customer_messages.csv", "artifacts/message_classifier.pkl",
                         "database/loanserve.db", "output/message_pipeline.csv", 2000)
    print(rows.status.value_counts())
