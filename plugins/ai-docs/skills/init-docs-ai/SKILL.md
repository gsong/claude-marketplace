---
name: init-docs-ai
description: Use when the user wants to bootstrap or initialize AI-optimized documentation for a project, or set up a docs-ai directory. Also use when the user invokes /init-docs-ai.
---

# Initialize Docs AI

Bootstrap a `docs-ai/` directory structure for Claude Code documentation lookups.

## Goal

Create AI-optimized documentation structure that enables effective Claude Code assistance via the docs-lookup skill.

## Process

### 1. Check Prerequisites

- Verify not already initialized (check for `docs-ai/README.md`)
- If exists, ask user if they want to reinitialize

### 2. Analyze Project Structure

Launch a subagent to analyze the project and recommend documentation structure:

**Subagent should:**

- Read project config files (package.json, go.mod, Cargo.toml, pom.xml, pyproject.toml, etc.)
- Use Glob/Grep to identify patterns in codebase:
  - Frontend frameworks (React components, Vue files, etc.)
  - Backend patterns (API routes, controllers, services)
  - CLI structure (command definitions, argument parsing)
  - State management (Zustand, Redux, Pinia, etc.)
  - Routing systems (React Router, Next.js, Express routes, etc.)
  - Database/ORM usage (Prisma, TypeORM, SQLAlchemy, etc.)
  - Testing patterns (Jest, Vitest, pytest, etc.)
  - Build/deploy configuration
  - Styling approaches (Tailwind, CSS modules, styled-components, etc.)
- Detect monorepo structure (workspaces, multiple packages, pnpm-workspace.yaml, lerna.json)
- Identify tech stack and architectural patterns
- Assess project complexity (simple vs. complex)

**Subagent should output:**

- **Project overview**: Brief description of what the project is (monorepo, hybrid app, simple library, etc.)
- **Tech stack**: Key technologies and frameworks detected
- **Recommended docs**: List of documentation files to create with rationale for each
- **README.md structure**: Suggested task-based categories for the documentation map
- **Special considerations**: Monorepo workspaces, multiple project types, unusual patterns

### 3. Present Recommendations

Show analysis to user with recommendations. Ask for approval/modifications before creating files.

User can:

- Accept all recommendations
- Remove docs they don't want
- Add docs not suggested
- Modify category structure

### 4. Create Directory Structure

```
docs-ai/
├── README.md          (documentation map - always created)
├── quick-reference.md (cheat sheet - always created)
├── architecture.md    (tech stack overview - always created)
└── [approved docs from recommendations]
```

### 5. Create Documentation Files

**Always create these base files:**

- `README.md` - Documentation map with task-based index
- `quick-reference.md` - Placeholder for common tasks/patterns cheat sheet
- `architecture.md` - Placeholder for tech stack, directory structure, key decisions

**Create approved recommendation files** with:

- Section headers (## Format) to populate README.md map
- TODO comments indicating what to fill in
- Brief prompts/examples for what content belongs in each section
- File::Symbol reference examples where appropriate (e.g., `app/utils/foo.ts::barFunction`)

### 6. Update README.md Map

Follow the canonical README.md format. Load the format specification:

!`cat "$(dirname "${CLAUDE_SKILL_DIR}")/../resources/docs-ai-readme-format.md"`

Populate `docs-ai/README.md` following this format exactly:

- Start with header linking to quick-reference.md
- Add the Reference Convention section
- Create the "By Topic" section with categorized tables
- Every created doc file must appear in exactly one category table

## Output

After completion, show:

1. **Analysis summary**: Brief overview of what was detected
2. **Files created**: List with line counts
3. **Next steps**:
   - **Fill in TODO sections** in each doc with actual project information
   - **Run `/ai-docs:review-docs-ai`** to evaluate completeness and refine content
   - **Update README.md** headings as docs evolve

## Execution Notes

- Create all files using Write tool
- Do not create .claude/agents/ or modify .claude/CLAUDE.md — the plugin handles docs-lookup and reminders via its built-in skill and hook
