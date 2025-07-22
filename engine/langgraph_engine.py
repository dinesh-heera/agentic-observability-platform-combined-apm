from langgraph.graph import StateGraph, END
from mcp_router import route_by_intent
from agents import (
    classify_intent, generate_splunk_query, run_splunk_query,
    handle_apm_usecases, fetch_appd_data, do_rca, create_jira_ticket
)

class ObservabilityState:
    def __init__(self, prompt, context={}, history=[]):
        self.prompt = prompt
        self.context = context
        self.history = history

async def run_engine(user_prompt: str, chat_history: list):
    sg = StateGraph(ObservabilityState)
    sg.add_node("classify", classify_intent)
    sg.add_node("generate_query", generate_splunk_query)
    sg.add_node("run_query", run_splunk_query)
    sg.add_node("splunk_apm_combined", handle_apm_usecases)
    sg.add_node("fetch_appd", fetch_appd_data)
    sg.add_node("rca", do_rca)
    sg.add_node("create_ticket", create_jira_ticket)
    sg.set_entry_point("classify")

    def branching_router(state: ObservabilityState):
        route = route_by_intent(state.context["intent"])
        return {
            "splunk": "generate_query",
            "splunk_apm_combined": "splunk_apm_combined",
            "appdynamics": "fetch_appd"
        }.get(route, "generate_query")

    sg.add_conditional_edges("classify", branching_router, {
        "generate_query": "run_query",
        "splunk_apm_combined": "rca",
        "fetch_appd": "rca"
    })

    sg.add_edge("run_query", "rca")
    sg.add_edge("rca", "create_ticket")
    sg.add_edge("create_ticket", END)

    graph = sg.compile()
    final_state = await graph.invoke(ObservabilityState(prompt=user_prompt, history=chat_history))
    return final_state.context["final_response"]