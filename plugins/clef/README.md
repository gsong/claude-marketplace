# clef

Ask Clef, a local decision model, yes/no, pick-one, or rating questions and get a probability with each answer.

Clef and Clef-flash are Cloudflare's decision models. Ollama serves both on an Apple Silicon Mac, so each call costs nothing. Claude hands Clef the small decisions that would otherwise cost Claude's own tokens. Examples are classifying, triaging, checking a condition, and picking an option.

## Skills

None yet. The plugin is a scaffold until its first skill lands.

## Prerequisites

- An Apple Silicon Mac. Ollama runs there, and every Claude session that uses Clef runs on that Mac or in a container on it.
- Homebrew's Ollama, 0.35.1 or later. Ollama.app at the same version also works, but run only one of the two. See [Install and start](skills/ask/setup.md#install-and-start).
- About 27 GB of disk for the two models, `clef:27b` and `clef-flash:9b`. See [Install and start](skills/ask/setup.md#install-and-start).
- Memory: both models loaded together take about 36 GB. With less free memory, Ollama unloads one model to load the other. A swap costs a few seconds and never changes an answer. See [Defaults to keep](skills/ask/setup.md#defaults-to-keep).
- [uv](https://docs.astral.sh/uv/), to run the script. See the [setup guide](skills/ask/setup.md).
- For container sessions: the container mounts `~/.claude/plugins` at its Mac path and can resolve `host.docker.internal`. Docker Desktop resolves it by default. See the [setup guide](skills/ask/setup.md).

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install clef@gsong-marketplace
```

Install the plugin at user level on each Mac that runs the server. Do not enable it in a project's settings. A teammate without the Mac setup would get a skill that always fails.

Update the plugin on the Mac. A container session picks up the update at its next start.
