"""Remove correspondence wrapping while preserving the customer's words."""

import re
from pathlib import Path

import pandas as pd

from config.constants import APPLICATION_REFERENCE_PLACEHOLDER, TICKET_PLACEHOLDER, URL_PLACEHOLDER


URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
APPLICATION_REFERENCE_PATTERN = re.compile(r"\b(?:LA|LP)\d{6}\b", re.IGNORECASE)
TICKET_PATTERN = re.compile(r"\b(?:TKT|REF|SR|CASE)[-#]\d{4,}\b", re.IGNORECASE)
QUOTED_REPLY_PATTERN = re.compile(r"(?im)^\s*(?:On\s+.+?\s+wrote:|-----Original Message-----).*\Z", re.DOTALL)
SIGNATURE_PATTERN = re.compile(r"(?im)^\s*(?:--|Best regards,?|Thanks and regards,?|Sent from my\b.*).*$", re.MULTILINE)
GREETING_PATTERN = re.compile(r"(?i)^\s*(?:good morningg\b[,:!.-]?\s*|good morning(?=regarding)|(?:(?:hi|hello|dear|respected)(?:\s+(?:sir|madam|team))?|good\s+(?:morning|afternoon|evening))(?:\s*[,!:.-]\s*|\s+))")
SIGN_OFF_PATTERN = re.compile(r"(?i)\s*(?:thanks in advance|thanks and regards|thank you|thanks|regards|await(?:i|n)?ng your response)\.?\s*$")


def mask_urls(message_text):
    return URL_PATTERN.sub(URL_PLACEHOLDER, message_text)


def mask_application_references(message_text):
    return APPLICATION_REFERENCE_PATTERN.sub(APPLICATION_REFERENCE_PLACEHOLDER, message_text)


def mask_ticket_references(message_text):
    return TICKET_PATTERN.sub(TICKET_PLACEHOLDER, message_text)


def strip_quoted_reply(message_text):
    return QUOTED_REPLY_PATTERN.sub("", message_text)


def strip_signature(message_text):
    match = SIGNATURE_PATTERN.search(message_text)
    return message_text[:match.start()] if match else message_text


def strip_greeting(message_text):
    return GREETING_PATTERN.sub("", message_text, count=1)


def strip_sign_off(message_text):
    return SIGN_OFF_PATTERN.sub("", message_text)


def clean_message(message_text):
    if not isinstance(message_text, str):
        return ""
    result = strip_quoted_reply(message_text)
    result = strip_signature(result)
    result = strip_sign_off(result)
    result = strip_greeting(result)
    result = mask_urls(result)
    result = mask_application_references(result)
    result = mask_ticket_references(result)
    return " ".join(result.split()).strip().lower()


def clean_corpus(messages_file_path, output_path):
    messages = pd.read_csv(messages_file_path)
    cleaned = messages.copy()
    cleaned["cleaned_text"] = cleaned["message_text"].map(clean_message)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(destination, index=False)
    return len(cleaned)


if __name__ == "__main__":
    print("messages cleaned:", clean_corpus("data/customer_messages.csv", "processed_data/messages_cleaned.csv"))
