# clef

Find where Clef, Cloudflare's decision model, can make a system's repeated decisions, and design an experiment for each fit.

## Skills

| Skill                      | Trigger                                               | Description                                                                                                                                  |
| -------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `/clef:find-opportunities` | "where could Clef fit", "swap this LLM call for Clef" | Survey a repo, directory, file or prose for decision points, run the fit test on each, design an experiment for each fit, and write a record |

The skill writes its record to `clef-opportunities/<input-name>-<date>.md`. Pass that record back in to resume it.

The skill plans and writes only. It never runs `ollama` and never calls Clef. Clef first runs in an experiment's offline stage, after the session ends.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install clef@gsong-marketplace
```
