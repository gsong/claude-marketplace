# clef

Ask Clef, a local decision model, yes/no, pick-one, or rating questions and get a probability with each answer.

Clef and Clef-flash are Cloudflare's decision models. Ollama serves both on an Apple Silicon Mac, so each call costs nothing. Claude hands Clef the small decisions that would otherwise cost Claude's own tokens. Examples are classifying, triaging, checking a condition, and picking an option.

## Skills

| Skill      | Invoked by                                                                     | Description                                                                                                  |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `clef:ask` | a decision to classify, triage, check, choose or rate; "ask Clef"; `/clef:ask` | Ask Clef yes/no, pick-one or rating questions about a text or JSON state and images, one call or a batch run |

## Hooks

| Event        | Behavior                                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `PreToolUse` | Approves a plain Bash call of the plugin's `clef.py`, so `clef:ask` runs it with no prompt. Silent on any other command. |

The hook approves these calls. A skill's `allowed-tools` rule should do this, but Claude Code 2.1.289 drops that rule in most turns. The rule also made Claude Code ask before it loaded the skill, when Claude picked the skill itself: see [#66](https://github.com/gsong/claude-marketplace/issues/66). So `clef:ask` has no `allowed-tools` line. [#62](https://github.com/gsong/claude-marketplace/issues/62) tracks when the rule can take over from the hook. The hook approves two shapes, a call with a file on stdin and a `printf '%s' '<json>' |` pipe, with flags from a whitelist. `--out` writes a file, so it keeps the prompt. The hook does not limit which files `clef.py` reads, and the script sends what it reads to `CLEF_URL`. Point `CLEF_URL` only at a server you trust. The hook also stays silent for a plugin path with any character outside letters, digits and `-_.@+/`. So a marketplace added from a folder whose path holds a space prompts on each call. `hooks/test_allow_clef.py` lists what passes and what does not.

## Prerequisites

- An Apple Silicon Mac. Ollama runs there, and every Claude session that uses Clef runs on that Mac or in a container on it.
- Homebrew's Ollama, 0.35.1 or later. Ollama.app at the same version also works, but run only one of the two. See [Install and start](skills/ask/setup.md#install-and-start).
- About 27 GB of disk for the two models, `clef:27b` and `clef-flash:9b`. See [Install and start](skills/ask/setup.md#install-and-start).
- Memory: both models loaded together take about 36 GB. With less free memory, Ollama unloads one model to load the other. A swap costs a few seconds and never changes an answer. See [Defaults to keep](skills/ask/setup.md#defaults-to-keep).
- [uv](https://docs.astral.sh/uv/), to run the script. See [Install uv](skills/ask/setup.md#install-uv).
- jq, for the hook. macOS 15 and later ship it. Without jq, each Clef call asks before it runs.
- For container sessions:
  - The container mounts `~/.claude/plugins` at its Mac path. A marketplace added from a local folder needs that folder mounted at its Mac path too.
  - The container has its own uv and jq.
  - The container can resolve `host.docker.internal`. Docker Desktop resolves it by default.

  See [Container sessions](skills/ask/setup.md#container-sessions).

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install clef@gsong-marketplace
```

Install the plugin at user level on each Mac that runs the server. Do not enable it in a project's settings. A teammate without the Mac setup would get a skill that always fails.

Update the plugin on the Mac. A container session picks up the update at its next start.
