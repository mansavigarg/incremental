"""Four constrained language-model roles in the assistant workflow."""

import json
import re

from config.constants import MINIMUM_ANSWER_CONFIDENCE  # noqa: F401  (used by runner)
from loanserve.message_intelligence.llm_client import ask_model, read_answer
from loanserve.core.exceptions import LanguageModelError

PLANNER_KEYS = ("tool", "arguments", "why")
RESOLVER_KEYS = ("draft", "needs_approval")
CRITIC_KEYS = ("sound", "concern")
RESPONDER_KEYS = ("answer", "confidence")
TOOLS = ("calculate_installment", "lookup_application", "predict_default_risk", "search_policy_documents")

TRUE_WORDS = {"true", "yes", "y", "1", "sound", "approved", "ok"}
NO_CONCERN = {"", "none", "none.", "null", "nil", "n/a", "na", "no", "no concern", "no concerns", "no issues"}
INSTALMENT_TOLERANCE_INR = 0.51  # allows rounding to the nearest rupee

# Literal braces are doubled because these prompts are passed through .format().
PLANNER_PROMPT = (
    "Choose exactly one tool for the customer question. Available tools and exact argument names:\n"
    "calculate_installment: principal_inr (number of rupees), "
    "annual_interest_rate_percent (number, e.g. 9.5), tenure_months (integer).\n"
    "lookup_application: application_id (string).\n"
    "predict_default_risk: application (object with all model input fields).\n"
    "search_policy_documents: question (string), how_many (integer, optional).\n"
    'Reply with JSON only, no markdown: {{"tool": string, "arguments": object, "why": string}}. '
    "Use exactly the argument names above; do not invent aliases such as loan_amount or interest_rate. "
    "Convert lakh to rupees (1 lakh = 100000) and years to months.\n"
    "Question: {question}\nCategory: {category}\nUrgency: {urgency}"
)
RESOLVER_PROMPT = (
    "Using the question and tool results, write a short customer reply. "
    'Reply with JSON only, no markdown: {{"draft": string, "needs_approval": true or false}}. '
    "needs_approval must be a JSON boolean. "
    "Copy every figure from the tool results exactly as given, without rounding. "
    "Cite policy passages using their exact chunk_id in square brackets, e.g. [CH12]. "
    "Answer only with facts stated in the evidence. Do not promise any outcome, exception or "
    "account impact, and do not describe any process, review or next step unless the evidence states it. "
    "Set needs_approval to true only for waivers, overrides, promises or exceptions; otherwise false.\n"
    "Question: {question}\nEvidence: {tool_results}"
)
CRITIC_PROMPT = (
    "Check the draft against the tool results. "
    'Reply with JSON only, no markdown: {{"sound": true or false, "concern": string or null}}. '
    "sound must be a JSON boolean. Set sound to true and concern to null when every figure and "
    "citation in the draft is supported by the evidence; faithful paraphrases count as supported. "
    "Ignore greetings and courtesy phrases that make no factual, policy or numeric claim. "
    "Set sound to false only for unsupported facts, changed figures or invented citations, "
    "and explain why in concern.\n"
    "Draft: {draft}\nEvidence: {tool_results}"
)
RESPONDER_PROMPT = (
    "Rewrite the verified draft clearly for the customer, changing no figure and retaining every citation. "
    "Do not add new numbers, facts, promises or next steps. "
    "Do not paste tool results or evidence JSON into the answer. "
    'Reply with JSON only, no markdown: {{"answer": string, "confidence": number between 0 and 1}}. '
    "Give a low confidence when the evidence only partly supports the answer.\n"
    "Draft: {draft}\nEvidence: {tool_results}"
)


# ---------- helpers ----------

def _call(prompt, keys):
    try:
        return read_answer(ask_model(prompt), keys)
    except (LanguageModelError, ValueError, TypeError, KeyError) as error:
        return {"refused": str(error)}


def _as_bool(value):
    """Interpret model output safely: bool('false') is True in Python, so never use bool() directly."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in TRUE_WORDS


def _citations(text):
    return set(re.findall(r"\[CH\d+\]", str(text)))


def _numbers(text):
    """Extract numbers as floats: '16,016.17' -> 16016.17, '36.' -> 36.0."""
    values = set()
    for raw in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", str(text)):
        try:
            values.add(round(float(raw.replace(",", "")), 2))
        except ValueError:
            continue
    return values


def _contains_figure(text, figure, tolerance=0.01):
    return any(abs(value - figure) <= tolerance for value in _numbers(text))


def _instalments(tool_results):
    return [float(result["monthly_installment_inr"])
            for result in tool_results if "monthly_installment_inr" in result]


# ---------- roles ----------

def plan_tools(state):
    reply = _call(PLANNER_PROMPT.format(question=state["question"], category=state["category"],
                                        urgency=state["urgency"]), PLANNER_KEYS)
    if "refused" in reply:
        return reply
    arguments = reply["arguments"]
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {"refused": "Planner returned arguments that are not valid JSON"}
    if reply["tool"] not in TOOLS or not isinstance(arguments, dict):
        return {"refused": "Planner selected an unavailable tool or invalid arguments"}
    return {"plan": [{"tool": reply["tool"], "arguments": arguments, "why": str(reply.get("why", ""))}]}


def draft_answer(state):
    reply = _call(RESOLVER_PROMPT.format(question=state["question"], tool_results=state["tool_results"]),
                  RESOLVER_KEYS)
    if "refused" in reply:
        return reply
    draft = str(reply["draft"]).strip()
    if not draft:
        return {"refused": "Draft was empty"}

    allowed = {f"[{passage['chunk_id']}]"
               for result in state["tool_results"] for passage in result.get("passages", [])}
    if _citations(draft) - allowed:
        return {"refused": "Draft invented a policy citation"}

    for figure in _instalments(state["tool_results"]):
        if not _contains_figure(draft, figure, INSTALMENT_TOLERANCE_INR):
            return {"refused": "Draft changed the calculated instalment"}

    return {"draft": draft, "needs_approval": _as_bool(reply["needs_approval"])}


def check_draft(state):
    reply = _call(CRITIC_PROMPT.format(draft=state["draft"], tool_results=state["tool_results"]), CRITIC_KEYS)
    if "refused" in reply:
        return reply
    concern = str(reply.get("concern") or "").strip()
    # Accept when the critic says sound, or when it gives no real concern (e.g. sound="false", concern="None.").
    if _as_bool(reply["sound"]) or concern.lower() in NO_CONCERN:
        return {}
    return {"refused": concern}


def write_response(state):
    reply = _call(RESPONDER_PROMPT.format(draft=state["draft"], tool_results=state["tool_results"]),
                  RESPONDER_KEYS)
    if "refused" in reply:
        return reply
    answer = str(reply["answer"]).strip()
    if not answer:
        return {"refused": "Responder returned an empty answer"}

    # Confidence must be a real number before the runner compares it with the threshold.
    try:
        confidence = float(str(reply["confidence"]).strip().rstrip("%"))
    except (ValueError, TypeError):
        return {"refused": "Invalid answer confidence"}
    if confidence > 1:  # model replied as a percentage, e.g. 92
        confidence /= 100
    confidence = max(0.0, min(1.0, confidence))

    # No new figures may appear, and the calculated instalment must survive the rewrite.
    if _numbers(answer) - _numbers(state["draft"]):
        return {"refused": "Responder changed a figure"}
    for figure in _instalments(state["tool_results"]):
        if not _contains_figure(answer, figure, INSTALMENT_TOLERANCE_INR):
            return {"refused": "Responder removed the calculated instalment"}

    if _citations(state["draft"]) - _citations(answer):
        return {"refused": "Responder removed a policy citation"}

    return {"answer": answer, "confidence": confidence}