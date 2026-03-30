---
name: init-docs-ai
description: Use when the user wants to bootstrap or initialize AI-optimized documentation for a project, set up a docs-ai directory, or create a docs-lookup agent. Also use when the user invokes /init-docs-ai.
---

# Initialize Docs AI

Bootstrap a `docs-ai/` directory structure for Claude Code documentation lookups.

## Goal

Create AI-optimized documentation structure that enables effective Claude Code assistance via a docs-lookup subagent.

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

### 6. Create docs-lookup Agent

Create `.claude/agents/docs-lookup.md` with template:

```markdown
---
name: docs-lookup
description: MANDATORY documentation lookup agent. MUST use BEFORE: (1) any refactoring, (2) UI changes, (3) adding new features, (4) state management changes. Use proactively when uncertain about patterns.
tools: Bash, Glob, Grep, Read, WebFetch, WebSearch
model: sonnet
---

You are a documentation lookup specialist for the [PROJECT_NAME] codebase.

## Your Process

1. **Always Start Here**: Read `docs-ai/README.md` first - it's the documentation map
2. **Topic-Based Lookup**: Based on the question, read 1-2 relevant docs
3. **Supplement with Code Search**: If docs don't answer, use ast-grep/ripgrep
4. **Extract Only What's Needed**: Pull specific, actionable information

## Your Output Format

**Direct Answer**: [Concise how-to with file::Symbol references]

**Key Files**: [Specific files with ::Symbol references]

**Pattern**: [Code pattern to follow with example]

**See Also**: [Related doc sections]

## Critical Rules

- Be concise and actionable
- Always provide file::Symbol references (e.g., `app/utils/foo.ts::barFunction`)
- If docs don't have the answer, search codebase and say so
- Focus on "how to do X" not "what X is"
```

### 7. Update README.md Map

Populate `docs-ai/README.md` with:

- Task-based index using recommended categories
- All documentation section with heading outlines for each doc (like Claude Code's map format):

```markdown
**Core:**

- [architecture.md](./architecture.md) - Tech stack and system design
  - Technology Choices
  - Directory Structure
  - Key Architectural Decisions
```

### 8. Update .claude/CLAUDE.md (Optional)

Ask user if they want to add pre-flight checklist to `.claude/CLAUDE.md`:

```markdown
## ⚠️ PRE-FLIGHT CHECKLIST - READ BEFORE EVERY TASK

Before starting ANY coding task, you MUST explicitly check this list:

- [ ] **Is this a refactoring task?** → **USE docs-lookup**
- [ ] **Is this a UI change?** → **USE docs-lookup**
- [ ] **Is this a new feature?** → **USE docs-lookup**
- [ ] **Is this a state change?** → **USE docs-lookup**
- [ ] **Am I uncertain about patterns?** → **USE docs-lookup**

**If you checked ANY box above:** You MUST invoke the docs-lookup subagent BEFORE writing code.
```

## Output

After completion, show:

1. **Analysis summary**: Brief overview of what was detected
2. **Files created**: List with line counts
3. **Next steps**:
   - **Fill in TODO sections** in each doc with actual project information
   - **Run `/review-docs-ai`** to evaluate completeness and refine content (this will check for missing docs, extraneous docs, and optimize existing ones)
   - **Update README.md** headings as docs evolve
   - **Test docs-lookup agent**: Invoke it with a test question about the project

## Execution Notes

- Create all files using Write tool
- If .claude/ directory doesn't exist, create it
- If .claude/agents/ doesn't exist, create it
- Preserve any existing .claude/CLAUDE.md content when adding checklist
