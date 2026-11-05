"""Extractive summaries: choose attended sentences in original order."""

import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from loanserve.message_intelligence.attention import scaled_dot_product_attention
from loanserve.message_intelligence.text_cleaning import clean_message


SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
PLACEHOLDER = re.compile(r"<[^>]+>")


def carries_words(sentence):
    return bool(re.search(r"[a-zA-Z]", PLACEHOLDER.sub("", sentence)))


def split_into_sentences(thread_messages):
    sentences = []
    for message in thread_messages:
        cleaned = clean_message(message)
        for sentence in SENTENCE_END.split(cleaned):
            sentence = sentence.strip()
            if sentence and carries_words(sentence):
                sentences.append(sentence)
    return sentences


def score_sentences(sentences):
    if not sentences:
        return np.array([])
    vectors = TfidfVectorizer().fit_transform(sentences).toarray()
    _, weights = scaled_dot_product_attention(vectors, vectors, vectors)
    return weights.sum(axis=0)


def summarise_thread(thread_messages, keep):
    sentences = split_into_sentences(thread_messages)
    if len(sentences) <= keep:
        return sentences
    scores = score_sentences(sentences)
    chosen = sorted(np.argsort(-scores, kind="stable")[:keep])
    return [sentences[index] for index in chosen]


def summarise_all_threads(threads_file_path, output_path, keep):
    threads = pd.read_csv(threads_file_path).sort_values(["thread_id", "turn"])
    rows = []
    for thread_id, group in threads.groupby("thread_id", sort=True):
        messages = group["message_text"]
        sentences = split_into_sentences(messages)
        rows.append({
            "thread_id": thread_id,
            "application_reference": group["application_reference"].iloc[0],
            "category": group["category"].iloc[0],
            "messages": len(group),
            "sentences": len(sentences),
            "summary": " ".join(summarise_thread(messages, keep)),
        })
    result = pd.DataFrame(rows)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination, index=False)
    return result


if __name__ == "__main__":
    result = summarise_all_threads("data/message_threads.csv", "output/thread_summaries.csv", 3)
    print("threads summarised:", len(result))
