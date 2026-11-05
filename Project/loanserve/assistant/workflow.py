"""Persist and resume graph executions by thread identifier."""

import os
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from config.constants import CHECKPOINT_DATABASE_PATH, LOW_CONFIDENCE_REFUSAL, MINIMUM_ANSWER_CONFIDENCE
from loanserve.assistant.graph import build_assistant_graph
from loanserve.assistant.state import new_assistant_state
from loanserve.core.exceptions import InvalidApplicationError


def run_assistant(question, thread_id, approved=None, checkpoint_path=None):
    location = Path(checkpoint_path or os.getenv('LOANSERVE_CHECKPOINTS', CHECKPOINT_DATABASE_PATH))
    location.parent.mkdir(parents=True, exist_ok=True)
    config = {'configurable': {'thread_id': thread_id}}
    with SqliteSaver.from_conn_string(str(location)) as saver:
        graph = build_assistant_graph(saver)
        if approved is None:
            state = graph.invoke(new_assistant_state(question), config)
        else:
            snapshot = graph.get_state(config)
            if not snapshot.next or 'approval' not in snapshot.next:
                raise InvalidApplicationError('No pending approval for this thread')
            state = graph.invoke(Command(resume=approved), config)
        waiting = bool(state.get('__interrupt__'))
        if not waiting and (state.get('refused') or state.get('confidence', 0) < MINIMUM_ANSWER_CONFIDENCE):
            state['answer'] = LOW_CONFIDENCE_REFUSAL
            if state.get('steps') and state['steps'][-1] == 'respond' and state.get('messages'):
                state['messages'][-1].content = LOW_CONFIDENCE_REFUSAL
        return state, waiting
