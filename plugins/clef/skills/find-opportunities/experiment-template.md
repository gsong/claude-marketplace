# Experiment template

Copy everything below the line into the record's Experiment template section, verbatim. A planner then needs only the record, not the skill.

---

These rules hold for every experiment in this record. Each decision point's Experiment block gives only its own values.

- **Unit.** One experiment per decision point that fits. One labeled set, with a label on each item for each surviving question. Each question gets its own metrics, threshold and pass or fail.
- **Baselines.** Clef and both baselines run on the same items. Today's behavior is the fallback. A strong LLM is a reference ceiling only. It gets the same state and question text and must return one of the same options. When today's behavior is a person working a manual queue, the person's decisions are often the labels too. Then report agreement with the person and time saved.
- **Labeled set.** At least 100 items, at random from real recent items. Top up any option or level with fewer than 10 items, and mark the top-ups. The F7 source labels them. Claude may draft labels, but a person checks every one.
- **Stages.** Each stage must pass before the next starts. The user may stop after any stage.
  1. Offline: `clef`, `clef-flash` and both baselines run on the labeled set.
  2. Shadow mode: Clef answers at the real call site but only logs. A fresh labeled sample of the log is the held-out test. This stage also measures latency under real load.
  3. Act: Clef's answer takes effect above the threshold.
- **Metrics,** per question, for Clef and both baselines:
  - accuracy against the labels; for `score`, also the mean distance in levels
  - accuracy by Clef's top probability: below 0.65, 0.65–0.8, 0.8–0.9, 0.9 and up
  - coverage at the threshold (the share of items Clef answers), and accuracy on those items
  - the measured tokens and money of the call Clef replaces (R9); for the cloud, add the Workers AI price
  - median and 95th-percentile latency per item, on the target machine
- **Threshold (F9).** Per question: the lowest top probability where Clef ties or beats the fallback on the items it answers. Gate on `probabilities`, never on `confidence` or the margin (R8).
- **Pass bar.** Written into the record before any run. Offline: Clef ties or beats the fallback on the items it answers, and coverage meets a minimum the user sets. Manual queue: agreement with the person meets a minimum set in advance. Shadow mode: the held-out sample stays within 5 points of the offline accuracy. The strong LLM is not part of the bar.
- **Disputes.** The labels are the truth. One case gets a recheck: Clef and the strong LLM agree, but not with the label. The F7 labeler checks that item again, blind to which system said what. The record lists every changed label and shows results before and after. Claude never decides a dispute (R5).
- **Model (F8).** `clef-flash` wins when it passes on every question, since it is smaller and faster. Otherwise `clef` wins. Keep both results.
- **Latency.** Offline measures both models on the target machine against the budget in the record. A pass turns "pending a latency measurement" into "fits, local". An over-budget result is a flag, not a "no fit". The user decides at the act stage whether it matters. Latency never moves a decision point to the cloud.
- **Stability.** Offline also runs each question alone. If that changes more than 5% of a question's answers, mark the question unstable.
- **Option order.** No local check: Ollama sorts `choice` options by option ID, so the experiment and production see the same order. A cloud fit runs one check: the same request with the options in two orders, compared by probabilities. Reordering keys does nothing on Ollama, so rename option IDs to change the order. More than 5% changed answers marks the question unstable.
- **Multi-label recasts.** Label full label sets, and report the exact-set match rate.
- **Act stage.** Above the threshold, Clef's answer replaces the fallback. Below it, the fallback runs as today. The fallback stays wired in, so going back is one switch. A person labels a small sample of acted items, such as 20 a month. A drop below the bar switches back. An unstable question cannot reach the act stage until it is rewritten and passes again.
- **Setup sources.** Running Clef locally takes these:
  - [Ollama's Clef page](https://ollama.com/library/clef)
  - [Cloudflare's Clef docs](https://developers.cloudflare.com/workers-ai/models/clef/)
  - the [old setup guide](https://github.com/gsong/claude-marketplace/blob/6abcd57a36bb3d122258d0a4c183600c2c3bd968/plugins/clef/skills/ask/setup.md), for facts published nowhere else: pin the builds with `ollama cp`, never `ollama pull clef`; keep Ollama on 127.0.0.1; plan for about 36 GB of memory
