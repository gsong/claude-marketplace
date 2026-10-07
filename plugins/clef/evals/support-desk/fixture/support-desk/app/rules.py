"""Keyword rules that label a ticket before the LLM sees it."""

import re


def keyword_team(subject: str, body: str) -> str | None:
    text = f"{subject} {body}".lower()
    if re.search(r"\b(invoice|charge|charged|refund|receipt)\b", text):
        return "billing"
    elif re.search(r"\b(password|login|log in|2fa|locked out)\b", text):
        return "accounts"
    elif re.search(r"\b(tracking|delivery|parcel|courier)\b", text):
        return "shipping"
    elif "error" in text or "crash" in text:
        return "technical"
    return None
