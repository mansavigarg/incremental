"""Shared, checkpointed state for one assistant conversation."""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AssistantState(TypedDict):
    question: str
    category: str
    urgency: str
    plan: list[dict]
    tool_results: list[dict]
    draft: str
    needs_approval: bool
    approved: bool
    answer: str
    confidence: float
    refused: str
    messages: Annotated[list[AnyMessage], add_messages]
    steps: Annotated[list[str], operator.add]


def new_assistant_state(question: str) -> AssistantState:
    return {"question": question, "category": "", "urgency": "", "plan": [],
            "tool_results": [], "draft": "", "needs_approval": False,
            "approved": False, "answer": "", "confidence": 0.0, "refused": "",
            "messages": [], "steps": []}
