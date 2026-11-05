"""Configured Gemini calls with caching and strict JSON reply checks."""

import hashlib
import json
import os
import time
from pathlib import Path

from dotenv import dotenv_values
from google import genai

from config.constants import FREE_TIER_WAIT_SECONDS, LLM_CACHE_PATH, LLM_REQUIRED_KEYS
from loanserve.core.exceptions import LanguageModelError


CACHE_PATH = Path(LLM_CACHE_PATH)
PROMPT_TEMPLATE = (
    "You are a loan servicing analyst. Read this extracted conversation: {summary}\n"
    'Reply as JSON with "summary", "sentiment", and "action". '
    "Sentiment must be neutral, angry, worried, or happy."
)
REMINDER = "\nYour previous reply was unusable. Return only valid JSON with every required key."


def load_settings():
    declared = dotenv_values(Path(__file__).resolve().parents[2] / ".env")
    key = str(os.environ.get("GEMINI_API_KEY", declared.get("GEMINI_API_KEY") or "")).strip()
    model = str(os.environ.get("GEMINI_MODEL", declared.get("GEMINI_MODEL") or "")).strip()
    if not key or not model:
        raise LanguageModelError("Set GEMINI_API_KEY and GEMINI_MODEL in .env")
    return key, model


def cache_key(model_name, prompt):
    return hashlib.sha256(f"{model_name}\0{prompt}".encode()).hexdigest()


def read_cache():
    path = Path(os.getenv('LOANSERVE_LLM_CACHE', str(CACHE_PATH)))
    return json.loads(path.read_text()) if path.exists() else {}


def _request_model(key, model, prompt):
    with genai.Client(api_key=key, http_options=genai.types.HttpOptions(timeout=60000)) as client:
        response = client.models.generate_content(
            model=model, contents=prompt,
            config=genai.types.GenerateContentConfig(temperature=0),
        )
        return response.text or ''


def ask_model(prompt):
    key, model = load_settings()
    cache = read_cache()
    digest = cache_key(model, prompt)
    if digest in cache:
        return cache[digest]
    path = Path(os.getenv('LOANSERVE_LLM_CACHE', str(CACHE_PATH)))
    for attempt in range(3):
        try:
            reply = _request_model(key, model, prompt)
            cache[digest] = reply
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cache, indent=2, sort_keys=True))
            return reply
        except Exception as error:
            if "429" in str(error) and attempt < 2:
                time.sleep(FREE_TIER_WAIT_SECONDS)
                continue
            raise LanguageModelError(str(error)) from error
    raise LanguageModelError("Model request exhausted retries")


def read_answer(reply_text, required_keys=LLM_REQUIRED_KEYS):
    cleaned = reply_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    answer = json.loads(cleaned)
    missing = set(required_keys) - set(answer)
    if missing:
        raise ValueError(f"Missing model reply keys: {sorted(missing)}")
    return answer


def analyse_thread(extractive_summary):
    prompt = PROMPT_TEMPLATE.format(summary=extractive_summary)
    try:
        return read_answer(ask_model(prompt))
    except (ValueError, json.JSONDecodeError):
        try:
            return read_answer(ask_model(prompt + REMINDER))
        except (ValueError, json.JSONDecodeError) as error:
            raise LanguageModelError(f"Unusable model reply: {error}") from error
