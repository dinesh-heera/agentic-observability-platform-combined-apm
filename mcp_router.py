def route_by_intent(intent: str):
    if intent in ["apm_health_check", "traceability"]:
        return "splunk_apm_combined"
    elif intent == "performance_issue":
        return "appdynamics"
    else:
        return "splunk"