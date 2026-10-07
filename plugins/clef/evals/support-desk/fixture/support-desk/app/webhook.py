"""Receive inbound support email and file it as a ticket."""

from app.labeler import label_team
from app.rules import keyword_team
from app.store import save_ticket


def handle_inbound_email(payload: dict) -> dict:
    ticket = {
        "subject": payload["subject"],
        "body": payload["text"],
        "customer": payload["from"],
    }
    # The keyword rules run first. The LLM labels whatever they miss.
    team = keyword_team(ticket["subject"], ticket["body"])
    if team is None:
        team = label_team(ticket["subject"], ticket["body"])
    ticket["team"] = team
    ticket["status"] = "open"
    save_ticket(ticket)
    return {"ok": True, "team": team}
