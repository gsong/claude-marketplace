# clef

Find where Clef, Cloudflare's decision model, can make a system's repeated decisions, design an experiment for each fit, and build software that calls Clef.

## Skills

| Skill                      | Trigger                                               | Description                                                                                                                                  |
| -------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `/clef:find-opportunities` | "where could Clef fit", "swap this LLM call for Clef" | Survey a repo, directory, file or prose for decision points, run the fit test on each, design an experiment for each fit, and write a record |
| `/clef:build`              | "build this with Clef", "call Clef from this code"    | Design typed questions and write code that calls Clef, locally through Ollama or on Workers AI                                               |

`/clef:find-opportunities` writes its record to `clef-opportunities/<input-name>-<date>.md`. Pass that record back in to resume it.

After each write to a record, a `PostToolUse` hook formats it with prettier. It uses the prettier in `node_modules/.bin` of the directory that holds `clef-opportunities/`, else one on `PATH`. It never installs one. Without prettier or `jq`, the hook does nothing.

`/clef:find-opportunities` plans and writes only. It never runs `ollama` and never calls Clef: Clef first runs in an experiment's offline stage, after the session ends. `/clef:build` writes code that calls Clef, and may run that code to test it.

## Prerequisites

For `/clef:build` only. `/clef:find-opportunities` needs neither.

- [Ollama](https://ollama.com/) with `clef` or `clef-flash` pulled, for local Clef. This is the default.
- Or a Cloudflare account with [Workers AI](https://developers.cloudflare.com/workers-ai/models/clef/), for Clef in the cloud.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install clef@gsong-marketplace
```
