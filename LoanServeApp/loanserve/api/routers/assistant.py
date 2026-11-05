"""Authenticated assistant endpoint with administrator-only approval."""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from loanserve.api.schemas import AssistantQuestion, AssistantResponse
from loanserve.assistant.workflow import run_assistant
from loanserve.core.exceptions import InvalidApplicationError

router = APIRouter(prefix='/assistant', tags=['assistant'])


@router.post('/ask', response_model=AssistantResponse)
def ask(submitted: AssistantQuestion, request: Request):
    thread_id = submitted.thread_id or str(uuid4())
    if submitted.approved is not None:
        claims = request.app.state.access_control.read_token(request.headers.get('authorization', ''))
        if claims.get('role') != 'administrator':
            raise HTTPException(403, 'Administrator approval required')
    try:
        state, waiting = run_assistant(submitted.question, thread_id, approved=submitted.approved)
    except InvalidApplicationError as error:
        raise HTTPException(409, str(error)) from error
    return {'thread_id': thread_id, 'answer': state['answer'], 'category': state['category'],
            'confidence': state['confidence'], 'refused': state['refused'],
            'steps': state['steps'], 'narration': [str(message.content) for message in state['messages']],
            'needs_approval': waiting}
