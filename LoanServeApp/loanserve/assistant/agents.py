"""Four constrained language-model roles in the assistant workflow."""

import re

from config.constants import MINIMUM_ANSWER_CONFIDENCE
from loanserve.message_intelligence.llm_client import ask_model, read_answer
from loanserve.core.exceptions import LanguageModelError

PLANNER_KEYS = ("tool", "arguments", "why")
RESOLVER_KEYS = ("draft", "needs_approval")
CRITIC_KEYS = ("sound", "concern")
RESPONDER_KEYS = ("answer", "confidence")
TOOLS = ("calculate_installment", "lookup_application", "predict_default_risk", "search_policy_documents")

PLANNER_PROMPT = ("Choose one tool for the customer question. Available tools and exact argument names:\n"
                  "calculate_installment: principal_inr (number of rupees), "
                  "annual_interest_rate_percent (number, e.g. 9.5), tenure_months (integer).\n"
                  "lookup_application: application_id (string).\n"
                  "predict_default_risk: application (object with all model input fields).\n"
                  "search_policy_documents: question (string), how_many (integer, optional).\n"
                  'Reply JSON with "tool", "arguments", "why". Use exactly the argument names above; '
                  'do not invent aliases such as loan_amount or interest_rate. Convert lakh to rupees. '
                  "Question: {question}\nCategory: {category}\nUrgency: {urgency}")
RESOLVER_PROMPT = ('Using question and tool results, reply JSON with "draft" and "needs_approval". '
                   'Cite policy passages using their exact chunk_id. Require approval for waivers, overrides, promises or exceptions. '
                   'Question: {question}\nEvidence: {tool_results}')
CRITIC_PROMPT = ('Check the draft against tool results. Reply JSON with "sound" as a JSON boolean '
                 '(true when supported, false when unsupported) and "concern" as a string or null. '
                 'Reject unsupported facts or citations. Draft: {draft}\nEvidence: {tool_results}')
RESPONDER_PROMPT = ('Rewrite the verified draft clearly, changing no figure and retaining every citation. '
                    'Do not paste tool results or evidence JSON into the customer answer. '
                    'Reply JSON with "answer" and numeric "confidence". Draft: {draft}\nEvidence: {tool_results}')


def _call(prompt, keys):
    try:
        return read_answer(ask_model(prompt), keys)
    except (LanguageModelError, ValueError, TypeError, KeyError) as error:
        return {"refused": str(error)}


def plan_tools(state):
    reply = _call(PLANNER_PROMPT.format(question=state['question'], category=state['category'], urgency=state['urgency']), PLANNER_KEYS)
    if 'refused' in reply:
        return reply
    if reply['tool'] not in TOOLS or not isinstance(reply['arguments'], dict):
        return {'refused': 'Planner selected an unavailable tool or invalid arguments'}
    return {'plan': [reply]}


def _citations(text):
    return set(re.findall(r'\[CH\d+\]', text))


def draft_answer(state):
    reply = _call(RESOLVER_PROMPT.format(question=state['question'], tool_results=state['tool_results']), RESOLVER_KEYS)
    if 'refused' in reply:
        return reply
    allowed = {f"[{passage['chunk_id']}]" for result in state['tool_results'] for passage in result.get('passages', [])}
    if _citations(str(reply['draft'])) - allowed:
        return {'refused': 'Draft invented a policy citation'}
    for result in state['tool_results']:
        if 'monthly_installment_inr' in result:
            number = float(result['monthly_installment_inr'])
            values = [float(value.replace(',', '')) for value in re.findall(r'(?<!\w)\d[\d,]*\.\d+|(?<!\w)\d[\d,]*', str(reply['draft']))]
            if number not in values:
                return {'refused': 'Draft changed the calculated instalment'}
    approval = reply['needs_approval']
    if isinstance(approval, str):
        approval = approval.strip().lower() in ('true', 'yes', 'required')
    return {'draft': str(reply['draft']), 'needs_approval': bool(approval)}


def check_draft(state):
    reply = _call(CRITIC_PROMPT.format(draft=state['draft'], tool_results=state['tool_results']), CRITIC_KEYS)
    if 'refused' in reply:
        return reply
    sound = reply['sound']
    if isinstance(sound, str):
        sound = sound.strip().lower() in ('true', 'yes', 'sound', 'supported')
    return {} if sound is True else {'refused': str(reply['concern'] or 'Draft failed review')}


def write_response(state):
    reply = _call(RESPONDER_PROMPT.format(draft=state['draft'], tool_results=state['tool_results']), RESPONDER_KEYS)
    if 'refused' in reply:
        return reply
    try:
        confidence = float(reply['confidence'])
    except (ValueError, TypeError):
        return {'refused': 'Invalid answer confidence'}
    old_numbers = re.findall(r'(?<!\w)\d[\d,.]*(?!\w)', state['draft'])
    new_numbers = re.findall(r'(?<!\w)\d[\d,.]*(?!\w)', str(reply['answer']))
    if set(old_numbers) != set(new_numbers):
        return {'refused': 'Responder changed a figure'}
    if _citations(state['draft']) - _citations(str(reply['answer'])):
        return {'refused': 'Responder removed a policy citation'}
    return {'answer': str(reply['answer']), 'confidence': confidence}
