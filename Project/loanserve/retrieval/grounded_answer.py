"""Answer from retrieved passages and reject invented citations."""

import re
from pathlib import Path

import pandas as pd

from loanserve.message_intelligence.llm_client import ask_model
from loanserve.retrieval.vector_store import search_policy


CITATION_PATTERN = re.compile(r"\[(CH\d{4}(?:\s*,\s*CH\d{4})*)\]")
ANSWER_TEMPLATE = (
    "You answer customer questions using only the policy passages below. "
    "If they do not answer, say so plainly. Cite every borrowed sentence with its "
    "[CH0000] label and cite only labels provided here.\n\n{passages}\n\nQuestion: {question}"
)


class UngroundedAnswer(Exception):
    """An answer has no verified retrieved citation."""


def build_prompt(question, chunks):
    passages = "\n\n".join(
        f"[{chunk['chunk_id']}] {chunk.get('document_id', '')} — {chunk.get('heading', '')}\n{chunk['text']}"
        for chunk in chunks
    )
    return ANSWER_TEMPLATE.format(question=question, passages=passages)


def cited_chunk_ids(answer_text):
    return sorted({chunk_id.strip() for group in CITATION_PATTERN.findall(answer_text)
                   for chunk_id in group.split(',')})


def check_citations(answer_text, retrieved):
    cited = cited_chunk_ids(answer_text)
    if not cited:
        raise UngroundedAnswer("Answer cited no policy passages")
    known = {chunk["chunk_id"] for chunk in retrieved}
    invented = set(cited) - known
    if invented:
        raise UngroundedAnswer(f"Unretrieved citations: {sorted(invented)}")
    return cited


def answer_question(question, collection, embedder, how_many):
    retrieved = search_policy(collection, question, embedder, how_many)
    return answer_from_passages(question, retrieved)


def answer_from_passages(question, retrieved):
    """Ask the model using only retrieved text and verify each cited chunk."""
    answer = ask_model(build_prompt(question, retrieved))
    citations = check_citations(answer, retrieved)
    answer = CITATION_PATTERN.sub(
        lambda match: ' '.join(f'[{chunk_id.strip()}]' for chunk_id in match.group(1).split(',')),
        answer,
    )
    return {
        "question": question, "answer": answer, "citations": " ".join(citations),
        "retrieved": " ".join(chunk["chunk_id"] for chunk in retrieved),
    }


def answer_all(questions, collection, embedder, output_path, how_many):
    rows = []
    for question in questions:
        try:
            rows.append({**answer_question(question, collection, embedder, how_many), "refused": ""})
        except UngroundedAnswer as error:
            rows.append({"question": question, "answer": "", "citations": "", "retrieved": "", "refused": str(error)})
    result = pd.DataFrame(rows).fillna("")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination, index=False)
    return result
