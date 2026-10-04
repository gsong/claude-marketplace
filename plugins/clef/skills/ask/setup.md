# Clef setup

These steps set up Ollama on an Apple Silicon Mac to serve Clef and Clef-flash. You run them. Claude shows you a step and runs it only when you ask.

## Install and start

1. Install Ollama:

   ```sh
   brew install ollama
   ```

2. Start the server:

   ```sh
   brew services start ollama
   ```

   The service starts at login. It also restarts if it exits. You run this step once.

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

   Then run `scripts/check.py`, which asks both models six questions. It exits 0 when every answer is correct. The script sits in the `scripts` directory beside this guide. After a plugin install, that is `~/.claude/plugins/cache/gsong-marketplace/clef/<version>/skills/ask/scripts/check.py`. Replace `<version>` with the installed plugin version. For a marketplace added from a local folder, the script is in that folder at `plugins/clef/skills/ask/scripts/check.py`.

To stop the server, run `brew services stop ollama`.

## Install uv

```sh
brew install uv
```

The first line of `clef.py` starts the script with uv. Every session that uses Clef needs uv on its `PATH`. A container session needs its own uv inside the container.

## Container sessions

A Claude session in a Docker container on the Mac reaches Ollama through `host.docker.internal`.

1. Mount `~/.claude/plugins` into the container at the same path it has on the Mac. Plugin paths then resolve the same inside and outside the container. With `docker run`, the flag is:

   ```sh
   -v "$HOME/.claude/plugins:$HOME/.claude/plugins"
   ```

   Claude Code reads a marketplace added from a local folder, such as a clone of this repo, from that folder. `claude plugin marketplace list` shows such a marketplace as `Source: Folder (<path>)`. Mount that folder at the same path too:

   ```sh
   -v "<path>:<path>"
   ```

2. Install uv and jq in the container, and put both on the container's `PATH`. The uv installer works in a Linux container:

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   Claude Code runs the hook inside the container. Without jq there, each Clef call asks before it runs. On a Debian or Ubuntu image, run this as root or with `sudo`:

   ```sh
   apt-get update && apt-get install -y jq
   ```

3. Check the route from inside the container:

   ```sh
   curl host.docker.internal:11434/api/version
   ```

   Docker Desktop resolves `host.docker.internal` by default.

4. If you set `CLEF_LOG` to keep a decision log, set it in the container too. Point it at a file in a folder that exists in the container and that the container can write to. `clef.py` never creates that folder. If the folder is missing, the script warns once, answers anyway and logs nothing.

## Warnings

- Update a model only by rerunning steps 3 and 4. Never run `ollama pull clef` or `ollama pull clef-flash`. Each of these pulls overwrites the copy with the library's `latest` build.
- Keep Ollama on its default address, `127.0.0.1:11434`. Never set `OLLAMA_HOST=0.0.0.0`. That setting opens Ollama's full API to the local network.
- Any process or container on the Mac can call Ollama's full API, including pull and delete. If `clef` or `clef-flash` goes missing or gives wrong answers, rerun steps 3 and 4.
- Ollama.app at 0.35.1 or later also works. Run only one of the two, because both use port 11434.

## Defaults to keep

- Each model loads on its first call and unloads after 5 idle minutes. A call to an unloaded model takes a few seconds longer.
- Both models loaded together take about 36 GB of memory. With less free memory, Ollama unloads one model to load the other. The swap takes a few seconds and never changes an answer.
- Both models keep Ollama's default context window of 16,384 tokens. Setup needs no Modelfile, which is Ollama's file for model settings. Setup also needs no `OLLAMA_CONTEXT_LENGTH`.
- Homebrew's service sets `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0`. Together they cut the memory the context window takes. Keep both.
- After each `brew upgrade ollama`, run `scripts/check.py` again.

## Fixes for exit 3

`clef.py` exits with code 3 when it cannot get an answer from the server. Its error line names the server URL and where that URL came from. Each cause has one fix:

- **Wrong `CLEF_URL`:** the error line names `CLEF_URL` as the source. Correct the variable, or unset it so that the script picks the URL.
- **Unreachable:** run `brew services start ollama`, then the `curl` check from step 5.
- **Unreachable from a container only:** the Mac passes step 5, but the container fails its check in [Container sessions](#container-sessions). Use Docker Desktop, which resolves `host.docker.internal` by default. With another Docker runtime, add `--add-host=host.docker.internal:host-gateway` to `docker run`.
- **Model missing (HTTP 404):** rerun steps 3 and 4.
- **Timeout:** check `ollama ps` and `/opt/homebrew/var/log/ollama.log`.
