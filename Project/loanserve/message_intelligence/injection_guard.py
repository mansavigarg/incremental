"""Conservative patterns for instructions directed at the assistant."""

import re
from pathlib import Path

import joblib
import pandas as pd

from loanserve.message_intelligence.message_classifier import classify_message


INJECTION_PATTERNS = {
    "instruction_override": re.compile(r"(?i)\b(?:ignore|disregard|skip|forget)\s+(?:(?:all|every|your|the|my|any)\s+)*(?:previous|prior|earlier|above)?\s*(?:instructions?|directions?|rules?|prompt)\b"),
    "role_reassignment": re.compile(r"(?i)\b(?:you are now (?:a bank|an? (?:unrestricted|ai|model))|you are no longer (?:a|an)|pretend (?:to be|you are)|act as an? (?:ai|assistant)|from now on you are)\b"),
    "prompt_extraction": re.compile(r"(?i)\b(?:print|show|reveal|repeat|output|tell me)\s+(?:me\s+)?(?:your\s+|the\s+)?(?:system\s+prompt|instructions?|prompt above|rules you were configured|instructions above)\b"),
    "delimiter_smuggling": re.compile(r"(?i)(?:```\s*system|(?:###\s*)?(?:system|developer|assistant)\s*:|<\s*,?\s*system\s*,?\s*>)"),
    "data_exfiltration": re.compile(r"(?i)\b(?:list|give me|send|dump|export|paste)\s+(?:me\s+)?(?:every|all)\s+(?:applicant|customer|account holder|customer records|account holder's).*?(?:name|number|details|records|score|database|here)"),
    "guardrail_suppression": re.compile(r"(?i)\b(?:bypass your filters|remove all restrictions from your answer|answer with no restrictions|reply without any of your usual guidelines|disable your guardrails|without any safety guidelines|no safety guidelines)\b"),
}


def find_injection_markers(message_text):
    if not isinstance(message_text, str):
        return []
    return sorted(name for name, pattern in INJECTION_PATTERNS.items() if pattern.search(message_text))


def is_safe_to_send(message_text):
    return not find_injection_markers(message_text)


def guard_corpus(messages_file_path, classifier_path, output_path):
    messages = pd.read_csv(messages_file_path)
    models = joblib.load(classifier_path)
    rows = []
    for message in messages.itertuples(index=False):
        markers = find_injection_markers(message.message_text)
        labels = {} if markers else classify_message(models, message.message_text)
        rows.append({
            "message_id": message.message_id, "blocked": bool(markers),
            "markers": ", ".join(markers), "category": labels.get("category", ""),
            "urgency": labels.get("urgency", ""),
        })
    result = pd.DataFrame(rows)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination, index=False)
    return result


if __name__ == "__main__":
    rows = guard_corpus("data/adversarial_messages.csv", "artifacts/message_classifier.pkl", "output/injection_report.csv")
    labelled = pd.read_csv("data/adversarial_messages.csv")
    print("messages checked:", len(rows))
    print("attempts caught:", int((rows.blocked & labelled.is_injection.eq(1)).sum()))
    print("safe messages wrongly blocked:", int((rows.blocked & labelled.is_injection.eq(0)).sum()))
