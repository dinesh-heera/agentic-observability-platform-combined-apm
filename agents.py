# agents.py
from utils.llm import call_llm
import splunklib.client as client
import splunklib.results as results
import asyncio
import requests
from utils.playwright_utils import capture_screenshot
from utils.logger import logger

async def classify_intent(state):
    try:
        chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in state.history])
        prompt = f"Based on this conversation:\n{chat_context}\nClassify the intent of the last user message: {state.prompt}"
        intent = await call_llm(prompt)
        state.context["intent"] = intent.strip().lower()
    except Exception as e:
        logger.error(f"Intent classification error: {e}")
    return state

async def generate_splunk_query(state):
    try:
        query = await call_llm(f"Generate a Splunk SPL to diagnose: {state.prompt}")
        state.context["spl_query"] = query
    except Exception as e:
        logger.error(f"Query generation error: {e}")
    return state

async def run_splunk_query(state, retries=3):
    for attempt in range(retries):
        try:
            service = client.connect(host="localhost", port=8089, username="admin", password="pass")
            job = service.jobs.create(state.context["spl_query"])
            while not job.is_done():
                await asyncio.sleep(2)
            for result in results.ResultsReader(job.results()):
                state.context["splunk_result"] = result
            return state
        except Exception as e:
            logger.warning(f"Splunk query error on attempt {attempt+1}: {e}")
        await asyncio.sleep(2)
    logger.error("Splunk query failed after retries.")
    return state

async def do_rca(state):
    try:
        raw_data = str(state.context.get("splunk_result", "") or
                       state.context.get("apm_health", "") or
                       state.context.get("traceability", "") or
                       state.context.get("appd_metrics", ""))
        rca = await call_llm(f"Do RCA based on this: {raw_data}")
        state.context["rca"] = rca
    except Exception as e:
        logger.error(f"RCA error: {e}")
    return state

async def create_jira_ticket(state, retries=3):
    rca = state.context.get("rca", "No RCA available.")
    for attempt in range(retries):
        try:
            jira_resp = requests.post(
                "https://your-domain.atlassian.net/rest/api/3/issue",
                auth=("email@example.com", "jira_token"),
                json={
                    "fields": {
                        "project": {"key": "OBS"},
                        "summary": "Auto RCA - Observability",
                        "description": rca,
                        "issuetype": {"name": "Bug"}
                    }
                }
            )
            if jira_resp.status_code == 201:
                ticket_url = f"https://your-domain.atlassian.net/browse/{jira_resp.json()['key']}"
                break
            else:
                raise Exception(jira_resp.text)
        except Exception as e:
            logger.warning(f"JIRA ticket error on attempt {attempt+1}: {e}")
        await asyncio.sleep(2)
    else:
        ticket_url = "Jira ticket creation failed"
        logger.error("Jira ticket failed after retries.")

    dashboard_image = state.context.get("dashboard_screenshot_path")
    final_msg = f"🧠 RCA: {rca}\n🎟️ Jira Ticket: {ticket_url}"
    if dashboard_image:
        final_msg += f"\n📸 Dashboard Screenshot saved at: {dashboard_image}"
    state.context["final_response"] = final_msg
    return state

async def handle_apm_usecases(state):
    try:
        prompt = state.prompt.lower()
        if "health" in prompt or "status" in prompt:
            state.context["apm_health"] = "✔️ All services are healthy in Splunk APM."
            screenshot_path = await capture_screenshot()
            if screenshot_path:
                state.context["dashboard_screenshot_paths"] = [screenshot_path]
        elif "trace" in prompt or "traceability" in prompt:
            state.context["traceability"] = "📍 Traces: span-id=abc123, trace-id=xyz456"
        else:
            state.context["apm_response"] = "ℹ️ Generic APM data."
    except Exception as e:
        logger.error(f"APM use case error: {e}")
    return state

async def fetch_appd_data(state):
    try:
        state.context["appd_metrics"] = "AppD: CPU usage high on node XYZ"
    except Exception as e:
        logger.error(f"AppD fetch error: {e}")
    return state
