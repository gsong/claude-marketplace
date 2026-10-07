"""Ticket storage."""

TICKETS: list[dict] = []


def save_ticket(ticket: dict) -> None:
    TICKETS.append(ticket)
