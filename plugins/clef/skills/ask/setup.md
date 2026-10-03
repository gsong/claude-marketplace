# Clef setup

These steps set up Ollama on an Apple Silicon Mac to serve Clef and Clef-flash. Run them yourself. Claude shows you the steps but never runs them.

## Install and start

1. Install Ollama:

   ```sh
   brew install ollama
   ```

2. Start the server:

   ```sh
   brew services start ollama
   ```

   The service starts at login and restarts if it exits, so you run this once.

3. Pull the two tested builds:

   ```sh
   ollama pull clef:27b
   ollama pull clef-flash:9b
   ```

4. Copy each build to the name Cloudflare uses. The copies pin the tested builds:

   ```sh
   ollama cp clef:27b clef
   ollama cp clef-flash:9b clef-flash
   ```

5. Check that the server is up:

   ```sh
   curl 127.0.0.1:11434/api/version
   ```

   Then run `scripts/check.py`. It sits in the `scripts` directory beside this guide, and it asks both models six questions.

To stop the server, run `brew services stop ollama`.

## Install uv

```sh
brew install uv
```

The skill runs `clef.py` with `uv run`. Every session that uses Clef needs uv on its `PATH`. A container session needs its own uv inside the container.

## Container sessions

A Claude session in a Docker container on the Mac reaches Ollama through `host.docker.internal`.

1. Mount `~/.claude/plugins` into the container at the same path it has on the Mac. Plugin paths then resolve the same inside and outside the container. With `docker run`, the flag is:

   ```sh
   -v "$HOME/.claude/plugins:$HOME/.claude/plugins"
   ```

2. Install uv in the container.
3. Check the route from inside the container:

   ```sh
   curl host.docker.internal:11434/api/version
   ```

   Docker Desktop resolves `host.docker.internal` by default.

## Warnings

- Never run `ollama pull clef` or `ollama pull clef-flash`. A pull overwrites the copy with the library's `latest` build.
- Keep Ollama on its default address, `127.0.0.1:11434`. Never set `OLLAMA_HOST=0.0.0.0`. That setting opens Ollama's full API to the local network.
- Any process or container on the Mac can call Ollama's full API, including pull and delete. If `clef` or `clef-flash` goes missing or answers oddly, rerun steps 3 and 4.
- Ollama.app at 0.35.1 or later also works. Run only one of the two, because both use port 11434.

## Defaults to keep

- Each model loads on its first call and unloads after 5 idle minutes. A call to an unloaded model takes a few seconds longer.
- Both models keep Ollama's stock context window of 16,384 tokens. Setup needs no Modelfile and no `OLLAMA_CONTEXT_LENGTH`.
- After each `brew upgrade ollama`, run `scripts/check.py` again.

## Fixes for exit 3

`clef.py` exits with code 3 when it cannot get an answer from the server. Each cause has one fix:

- **Unreachable:** run `brew services start ollama`, then the `curl` check from step 5.
- **Model missing (HTTP 404):** rerun steps 3 and 4.
- **Timeout:** check `ollama ps` and `/opt/homebrew/var/log/ollama.log`.
