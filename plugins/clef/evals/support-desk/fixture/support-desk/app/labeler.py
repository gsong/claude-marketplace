"""Ask an LLM which team owns a support ticket."""

import os

from openai import OpenAI

TEAMS = ["billing", "accounts", "shipping", "technical"]

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def label_team(subject: str, body: str) -> str:
    prompt = (
        "You route support tickets. Reply with exactly one word from this list: "
        + ", ".join(TEAMS)
        + ", or 'other' if none fits.\n\n"
        + f"Subject: {subject}\n\n{body}"
    )
    reply = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        timeout=2.0,
    )
    label = reply.choices[0].message.content.strip().lower()
    return label if label in TEAMS else "other"
