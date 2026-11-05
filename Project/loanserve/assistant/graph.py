"""Seven stage LangGraph with refusal branches."""

from langgraph.graph import END, START, StateGraph

from loanserve.assistant import nodes
from loanserve.assistant.state import AssistantState


def still_going(state):
    return 'stop' if state['refused'] else 'go'


def build_assistant_graph(checkpointer=None):
    builder = StateGraph(AssistantState)
    for name, function in [('triage', nodes.triage), ('plan', nodes.plan), ('tools', nodes.run_tools),
                           ('draft', nodes.draft), ('approval', nodes.approval),
                           ('critic', nodes.critic), ('respond', nodes.respond)]:
        builder.add_node(name, function)
    builder.add_edge(START, 'triage')
    for source, target in [('triage', 'plan'), ('plan', 'tools'), ('draft', 'approval'), ('approval', 'critic'), ('critic', 'respond')]:
        builder.add_conditional_edges(source, still_going, {'go': target, 'stop': END})
    builder.add_edge('tools', 'draft')
    builder.add_edge('respond', END)
    return builder.compile(checkpointer=checkpointer)
