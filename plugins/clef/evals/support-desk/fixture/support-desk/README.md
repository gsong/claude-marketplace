# Support desk

A small support desk. Customers send tickets by email. The app stores each ticket, labels it with a team, and puts it in that team's queue. Agents work the queues by hand.

About 400 tickets arrive each day. Labeling runs in the request that receives the email webhook.

- `app/webhook.py` receives each ticket.
- `app/labeler.py` asks an LLM which team owns the ticket.
- `app/rules.py` holds the older keyword rules.
- `docs/runbook.md` is the agents' runbook.
