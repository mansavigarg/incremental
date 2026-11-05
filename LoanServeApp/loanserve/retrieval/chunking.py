"""Chunk policies at headings and word boundaries, preserving source labels."""

import re

from config.constants import POLICY_CHUNK_CHARACTERS
from loanserve.retrieval.document_loader import load_policy_documents


HEADING_MAXIMUM_CHARACTERS = 100


def looks_like_heading(line):
    line = line.strip()
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", line)
    content = [word for word in words if word.lower() not in {'and', 'or', 'of', 'the', 'for', 'to', 'on', 'a', 'an', 'in'}]
    return bool(line and len(line) <= HEADING_MAXIMUM_CHARACTERS
                and len(words) <= 10 and not line.endswith(('.', ',', ';', ':'))
                and '·' not in line and content
                and all(word[0].isupper() for word in content))


def split_into_sections(text):
    sections = []
    heading, body = "Introduction", []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if looks_like_heading(line):
            if body:
                sections.append((heading, " ".join(body)))
            heading, body = line, []
        else:
            body.append(line)
    if body:
        sections.append((heading, " ".join(body)))
    return sections


def split_without_breaking_words(body, maximum_characters):
    pieces, current = [], []
    length = 0
    for word in body.split():
        extra = len(word) + (1 if current else 0)
        if current and length + extra > maximum_characters:
            pieces.append(" ".join(current))
            current, length = [], 0
        current.append(word)
        length += len(word) + (1 if length else 0)
    if current:
        pieces.append(" ".join(current))
    return pieces


def chunk_documents(documents, maximum_characters=POLICY_CHUNK_CHARACTERS):
    chunks = []
    for document in documents:
        for heading, body in split_into_sections(document["text"]):
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\'"0-9])', body)
            for index in range(len(sentences)):
                window = ' '.join(sentences[index:index + 6])
                for piece in split_without_breaking_words(window, maximum_characters):
                    chunks.append({
                        "chunk_id": f"CH{len(chunks) + 1:04d}",
                        "document_id": document["document_id"],
                        "heading": heading, "text": piece,
                    })
    return chunks


if __name__ == "__main__":
    chunks = chunk_documents(load_policy_documents("data/policy_documents"), POLICY_CHUNK_CHARACTERS)
    print("chunks:", len(chunks), "longest:", max(map(lambda item: len(item["text"]), chunks)))
