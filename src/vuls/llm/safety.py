from vuls.llm.schemas import SafetyCheckResult

_HARMFUL_SOFTWARE_TERMS = (
    "ransomware",
    "malware",
    "credential theft",
    "steal browser passwords",
    "steals browser passwords",
    "phishing kit",
    "keylogger",
)


def evaluate_generation_safety(text: str) -> SafetyCheckResult:
    normalized = text.lower()
    for term in _HARMFUL_SOFTWARE_TERMS:
        if term in normalized:
            return SafetyCheckResult(
                allowed=False,
                code="disallowed_harmful_software",
                reason=f"Request includes disallowed harmful software intent: {term}.",
            )

    return SafetyCheckResult(
        allowed=True,
        code="allowed",
        reason="Request is within Vuls product generation scope.",
    )
