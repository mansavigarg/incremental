"""Read references, money and dates from raw customer messages."""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from loanserve.data_access.database_loader import ApplicationDatabase
from loanserve.message_intelligence.text_cleaning import APPLICATION_REFERENCE_PATTERN


AMOUNT_PATTERN = re.compile(r"(?i)(?:\b(?:Rs\.?|INR)\s*|₹\s*)(\d[\d,]*(?:\.\d{1,2})?)")
DATE_PATTERN = re.compile(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b")


def extract_references(message_text):
    if not isinstance(message_text, str):
        return []
    return sorted({match.upper() for match in APPLICATION_REFERENCE_PATTERN.findall(message_text)})


def extract_amounts(message_text):
    if not isinstance(message_text, str):
        return []
    return [float(value.replace(",", "")) for value in AMOUNT_PATTERN.findall(message_text)]


def extract_dates(message_text):
    if not isinstance(message_text, str):
        return []
    dates = []
    for match in DATE_PATTERN.findall(message_text):
        parts = re.split(r"[-/]", match)
        year = int(parts[2]) + (2000 if len(parts[2]) == 2 else 0)
        try:
            dates.append(datetime(year, int(parts[1]), int(parts[0])).date().isoformat())
        except ValueError:
            continue
    return dates


def extract_entities(message_text):
    return {
        "references": extract_references(message_text),
        "amounts": extract_amounts(message_text),
        "dates": extract_dates(message_text),
    }


def link_references(references, database):
    found, not_found = [], []
    for reference in references:
        (found if database.find_application(reference) is not None else not_found).append(reference)
    return found, not_found


def extract_corpus(messages_file_path, database_path, output_path):
    messages = pd.read_csv(messages_file_path)
    database = ApplicationDatabase(database_path)
    rows = []
    for message in messages.itertuples(index=False):
        entities = extract_entities(message.message_text)
        if not any(entities.values()):
            continue
        found, not_found = link_references(entities["references"], database)
        rows.append({
            "message_id": message.message_id,
            "references_found": " ".join(found),
            "references_not_found": " ".join(not_found),
            "amounts": " ".join(map(str, entities["amounts"])),
            "dates": " ".join(entities["dates"]),
        })
    database.connection.close()
    result = pd.DataFrame(rows, columns=["message_id", "references_found", "references_not_found", "amounts", "dates"])
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination, index=False)
    return result


if __name__ == "__main__":
    rows = extract_corpus("data/customer_messages.csv", "database/loanserve.db", "output/message_entities.csv")
    print("messages carrying an entity:", len(rows))
