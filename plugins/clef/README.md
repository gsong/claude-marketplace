# clef

Build software with Clef, Cloudflare's decision model, run locally through Ollama or on Workers AI.

## Skills

| Skill         | Trigger                                            | Description                                                                                    |
| ------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `/clef:build` | "build this with Clef", "call Clef from this code" | Design typed questions and write code that calls Clef, locally through Ollama or on Workers AI |

## Prerequisites

- [Ollama](https://ollama.com/) with `clef` or `clef-flash` pulled, for local Clef. This is the default.
- Or a Cloudflare account with [Workers AI](https://developers.cloudflare.com/workers-ai/models/clef/), for Clef in the cloud.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install clef@gsong-marketplace
```
