Resolving docs produces **two** values. Every skill needs both:

- `[docs-dir]` — the directory holding the docs and their `README.md`.
- `[path-root]` — the directory that `Key Paths` in that README are relative to. Get it by stripping the recognized directory name from `[docs-dir]` — the whole name, not one level: `docs-ai/`, `docs/ai/`, and `.claude/docs/` all leave the same `[path-root]`. Taking the parent instead works only for `docs-ai/` and silently points inside the docs tree for the other two.

`[path-root]` matters because Key Paths are written relative to the code they describe, not to wherever the command happens to run. In a monorepo, `apps/woody/docs-ai/README.md` lists `app/routes.ts`, and the real file is `apps/woody/app/routes.ts`. Join before you Glob or pass a path to git: `[path-root]/[key-path]`. Skipping the join is silent, not loud — `git rev-list --count [sha]..HEAD -- app/routes.ts` returns `0` for a path that never existed, which reads as "fresh" when you have actually checked nothing.

## 1. Discover candidate docs directories

The recognized directory names, in preference order:

1. `docs-ai/`
2. `docs/ai/`
3. `.claude/docs/`

Look for them in two places:

- **At the working directory** — `docs-ai/`, `docs/ai/`, `.claude/docs/`.
- **Inside workspace packages**, so monorepos resolve. Read the workspace globs from `pnpm-workspace.yaml`, the `workspaces` field in `package.json`, `lerna.json`, `nx.json`, `go.work`, or `[workspace].members` in `Cargo.toml`, and check each matching directory for the three names. With no workspace manifest, fall back to globbing two levels deep (`*/docs-ai`, `*/*/docs-ai`, and the same for the other two names). Exclude `node_modules/`, `vendor/`, `.venv/`, `dist/`, `build/`, and `.git/`.

Each hit is a candidate with its own `[docs-dir]` and `[path-root]`.

## 2. Select among candidates

- **No candidates** — output: "No docs directory found. Run `/gs:ai-docs:init` to bootstrap documentation." Do not guess at undocumented locations.
- **One candidate** — use it.
- **Several candidates** — pick by what the task is actually about, in this order:
  1. A workspace named in the question or argument (`woody`, `asset-manager`).
  2. The `[path-root]` that contains the files being changed or asked about — for `gs:ai-docs:update`, the paths from the git diff.
  3. The working directory itself, if a candidate sits at it.

  Read-only skills (`lookup`, `check`) may cover several candidates when the task genuinely spans them; say which ones you used. Skills that write (`update`, `audit`, `init`) must settle on one — ask the user when steps 1–3 leave it ambiguous, because writing to the wrong docs tree is worse than a question.

Report the choice as `[docs-dir]` (path root `[path-root]`) so the user can see a mis-resolution immediately. Several candidates in a monorepo is the normal, correct layout — do not warn about it. Warn only when candidates sit at the *same* path root, e.g. both `docs-ai/` and `docs/ai/` in one package: "Multiple docs directories at [path-root]: [list]. Using [chosen]. Consider consolidating to a single location."
