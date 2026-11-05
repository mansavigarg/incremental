"""Small state patches for each decision in the assistant graph."""

from pathlib import Path

import joblib
from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from config.constants import APPLICATION_DATABASE_PATH, CHAMPION_MODEL_PATH, POLICY_STORE_PATH
from loanserve.assistant import agents, tools
from loanserve.message_intelligence.injection_guard import find_injection_markers
from loanserve.message_intelligence.message_classifier import classify_message


def _note(name, message, **changed):
    return {"steps": [name], "messages": [AIMessage(content=message)], **changed}


def triage(state):
    markers = find_injection_markers(state['question'])
    if markers:
        return _note('triage', 'Stopped possible prompt injection.', refused=f"injection: {', '.join(markers)}")
    models = joblib.load('artifacts/message_classifier.pkl')
    labels = classify_message(models, state['question'])
    return _note('triage', f"Classified as {labels['category']} with {labels['urgency']} urgency.", **labels)


def plan(state):
    patch = agents.plan_tools(state)
    return _note('plan', 'Planned a validated tool call.' if 'plan' in patch else 'Could not plan a safe tool call.', **patch)


def run_tools(state):
    results = []
    for item in state['plan']:
        name, arguments = item.get('tool'), item.get('arguments', {})
        try:
            if name == 'calculate_installment':
                result = tools.calculate_installment(arguments)
            elif name == 'lookup_application':
                result = tools.lookup_application(arguments, APPLICATION_DATABASE_PATH)
            elif name == 'predict_default_risk':
                result = tools.predict_default_risk(arguments, CHAMPION_MODEL_PATH)
            elif name == 'search_policy_documents':
                result = tools.search_policy_documents(arguments, POLICY_STORE_PATH)
            else:
                result = {'tool_error': f'Unknown tool: {name}'}
        except Exception as error:
            result = {'tool_error': str(error)}
        results.append(result)
    return _note('tools', f'Executed {len(results)} tool call(s).', tool_results=results)


def draft(state):
    patch = agents.draft_answer(state)
    return _note('draft', 'Drafted an evidence based reply.' if 'draft' in patch else 'Draft could not be verified.', **patch)


def approval(state):
    if not state['needs_approval']:
        return _note('approval', 'No human approval needed.')
    granted = bool(interrupt({'draft': state['draft'], 'question': state['question']}))
    if not granted:
        return _note('approval', 'Human approval denied.', approved=False, refused='Approval denied')
    return _note('approval', 'Human approval granted.', approved=True)


def critic(state):
    for result in state['tool_results']:
        if 'tool_error' in result or ('passages' in result and not result['passages']):
            return _note('critic', 'Tool evidence unavailable.', refused='Tool evidence unavailable')
    patch = agents.check_draft(state)
    return _note('critic', 'Checked draft against evidence.' if not patch else 'Draft failed review.', **patch)


def respond(state):
    patch = agents.write_response(state)
    return _note('respond', patch.get('answer', 'Could not provide a verified answer.'), **patch)
