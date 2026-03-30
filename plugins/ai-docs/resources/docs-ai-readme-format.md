# docs-ai/README.md Format

This defines the canonical format for `docs-ai/README.md`. All skills in this plugin
that generate or validate README.md must follow this format.

## Purpose

README.md is the documentation map — the single entry point that docs-ai-lookup uses to
route questions to the right documentation files. It must be both human-readable and
structured enough for an AI agent to parse reliably.

## Required Structure

### 1. Header

```markdown
# Documentation Map

Start here: [quick-reference.md](./quick-reference.md)
```

The header must link to quick-reference.md as the default starting point.

### 2. Reference Convention

```markdown
## Reference Convention

Code references use `file::Symbol` format (e.g., `app/utils/foo.ts::barFunction`)
instead of line numbers. This keeps references stable as code evolves.
For unnamed code blocks, use `file::NearestSymbol > description`.
```

### 3. Topic Index (By Topic)

The core of the README. Organized as categorized tables with three columns:

```markdown
## By Topic

### [Category Name]

| Topic        | Doc                          | Key Paths                |
| ------------ | ---------------------------- | ------------------------ |
| [Topic name] | [filename.md](./filename.md) | Key directories or files |
```

**Column definitions:**

- **Topic**: Short label describing what this doc covers (1-3 words)
- **Doc**: Link to the markdown file in docs-ai/
- **Key Paths**: Most important file paths or directories related to this topic

**Category guidelines:**

- Group related docs under descriptive category headings (### level)
- Common categories: Core Architecture, Data & State, Features, Code Reference, Infrastructure
- Categories should reflect the project's actual structure, not a generic template
- Each doc file must appear in exactly one category
- Every .md file in docs-ai/ (except README.md and quick-reference.md) must appear in the index

### 4. No Other Sections

README.md should contain only the header, reference convention, and topic index.
Do not add usage instructions, contribution guides, or other content.
The goal is a clean, scannable lookup table.
