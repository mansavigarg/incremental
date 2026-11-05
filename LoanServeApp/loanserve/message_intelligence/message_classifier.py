"""TF-IDF classifiers whose saved pipelines clean raw messages themselves."""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from config.constants import HOLDOUT_SHARE, RANDOM_SEED
from loanserve.message_intelligence.text_cleaning import clean_message


def build_message_classifier():
    return Pipeline([
        ("vectorise", TfidfVectorizer(preprocessor=clean_message, ngram_range=(1, 2),
                                       min_df=3, sublinear_tf=True)),
        ("classify", LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)),
    ])


def labelled_messages(messages_file_path):
    messages = pd.read_csv(messages_file_path)
    return messages.dropna(subset=["category", "urgency"]).copy()


def train_for_label(messages, label_column):
    fitting, holdout, target, holdout_target = train_test_split(
        messages["message_text"], messages[label_column],
        test_size=HOLDOUT_SHARE, stratify=messages[label_column], random_state=RANDOM_SEED,
    )
    model = build_message_classifier().fit(fitting, target)
    predicted = model.predict(holdout)
    return model, {
        "accuracy": round(float(accuracy_score(holdout_target, predicted)), 4),
        "macro_f1": round(float(f1_score(holdout_target, predicted, average="macro")), 4),
        "vocabulary": len(model.named_steps["vectorise"].vocabulary_),
    }


def classify_message(models, message_text):
    return {name: str(model.predict([message_text])[0]) for name, model in models.items()}


if __name__ == "__main__":
    messages = labelled_messages("data/customer_messages.csv")
    models = {}
    for label in ("category", "urgency"):
        models[label], measured = train_for_label(messages, label)
        print(label, measured)
    destination = Path("artifacts/message_classifier.pkl")
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(models, destination)
    print("saved:", destination)
    print(classify_message(models, "Hi team, my EMI failed TKT-456789. Thanks and regards, Ravi"))
