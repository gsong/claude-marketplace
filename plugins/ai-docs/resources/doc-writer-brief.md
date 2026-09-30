Spawn writer agents as the general-purpose type — writers need Write, which Explore lacks. Each writer:

- Reads the relevant source files before writing
- Writes real content using `file::Symbol` references (not code blocks), with paths relative to `[path-root]` — for `apps/woody/docs-ai/`, write `app/routes.ts::routes`, not `apps/woody/app/routes.ts::routes`
- Keeps it concise — lookup reference, not tutorial
- Marks sections it cannot populate with rich stubs:

  ```markdown
  ## [Section Name]

  <!-- NEEDS CONTENT: Describe [specific thing].
       Start by reading: src/auth/middleware.ts::authMiddleware
       Key questions to answer:
       - How are tokens validated?
       - What's the refresh flow?
       Example format: "Tokens are validated via file::Symbol. Refresh uses..." -->
  ```
