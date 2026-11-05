"""Exercise the saved ML models, API, and policy retrieval locally."""

import argparse
import json

import joblib
import pandas as pd
from fastapi.testclient import TestClient

from config.constants import CHAMPION_MODEL_PATH, MODELLING_COLUMNS, POLICY_STORE_PATH
from loanserve.api.server import create_server_application
from loanserve.message_intelligence.message_classifier import classify_message
from loanserve.retrieval.filtered_search import filtered_search
from loanserve.retrieval.grounded_answer import answer_from_passages
from loanserve.retrieval.vector_store import load_embedder, open_policy_store
from loanserve.risk_models.baseline_model import load_model, predict_default_probability


def check_features(live=False):
    with TestClient(create_server_application()) as client:
        health = client.get('/health')
        health.raise_for_status()
        assert health.json()['status'] == 'ok'
        assert client.get('/openapi.json').status_code == 200
    print('FastAPI: health and OpenAPI passed')

    sample = pd.read_csv('data/loan_applications_predict.csv', nrows=1)
    model = load_model(CHAMPION_MODEL_PATH)
    probability = float(predict_default_probability(model, sample.loc[:, MODELLING_COLUMNS])[0])
    assert 0 <= probability <= 1
    print(f'Risk ML: champion predicted probability {probability:.4f}')

    classifier = joblib.load('artifacts/message_classifier.pkl')
    labels = classify_message(classifier, 'My loan instalment was charged twice this month')
    assert labels['category'] and labels['urgency']
    print(f'Message ML: category={labels["category"]}, urgency={labels["urgency"]}')

    questions = json.load(open('data/retrieval_evaluation_set.json', encoding='utf-8'))
    example = next(row for row in questions if row['answerable'])
    collection = open_policy_store(POLICY_STORE_PATH)
    passages = filtered_search(collection, example['question'], load_embedder(), 4)
    assert passages and all(passage['chunk_id'] and passage['text'] for passage in passages)
    print(f'RAG retrieval: {len(passages)} cited policy passages, first={passages[0]["chunk_id"]}')

    if live:
        answer = answer_from_passages(example['question'], passages)
        assert answer['citations']
        print(f'Gemini grounded answer: {answer["answer"]}')
        print(f'Verified citations: {answer["citations"]}')
    else:
        print('Gemini generation: run `bash run.sh check-live` to test a real cited answer')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='also call Gemini and verify its citations')
    check_features(parser.parse_args().live)
