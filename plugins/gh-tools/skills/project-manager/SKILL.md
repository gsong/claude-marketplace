---
name: gs:gh-tools:project-manager
description: Use when the user wants to generate a specialized agent for managing a GitHub project board — e.g. "set up an agent for my project board", "move issues between columns", "manage my GitHub project" — or when the user invokes /gs:gh-tools:project-manager with a project URL.
---

# GitHub Project Manager

Create a specialized agent for managing GitHub project board operations using a GitHub project URL.

**Usage:** `/gs:gh-tools:project-manager <project-url>`

**Example:** `/gs:gh-tools:project-manager https://github.com/orgs/sahajsoft/projects/112`

## Core Requirements

- Extract project information from the provided GitHub project URL
- Use GitHub CLI to fetch project details automatically
- Generate a project-specific agent for GitHub project board management
- Create the agent in the project's .claude/agents/ directory
- Ensure the agent has all required GitHub CLI commands pre-configured

## Process

### 1. Validate Environment

- If current directory is not a git repository: show "This command must be run in a git repository" and stop
- If GitHub CLI (`gh`) is not available or not authenticated: show "GitHub CLI must be installed and authenticated" and stop
- If no URL in `$ARGUMENTS`: show "Usage: /gs:gh-tools:project-manager <project-url>" and stop

### 2. Parse URL and Extract Project Info

From `$ARGUMENTS`, extract owner and project number.

Supported URL formats:

- `https://github.com/orgs/[OWNER]/projects/[NUMBER]` (organization projects)
- `https://github.com/users/[OWNER]/projects/[NUMBER]` (personal projects)

```bash
# Parse owner and project number from URL (handles both orgs/ and users/)
# ERE via -E works on both BSD and GNU sed; # delimiter avoids clashing with URL slashes
PROJECT_URL="$ARGUMENTS"
read -r OWNER PROJECT_NUMBER <<< "$(echo "$PROJECT_URL" |
  sed -E -n 's#^https://github\.com/(orgs|users)/([^/]+)/projects/([0-9]+).*#\2 \3#p')"
```

If either value is empty, show "Invalid GitHub project URL format" and stop.

### 3. Fetch Project Details via GitHub CLI

```bash
# Get project details
PROJECT_DATA=$(gh project view "$PROJECT_NUMBER" --owner "$OWNER" --format json)
PROJECT_ID=$(echo "$PROJECT_DATA" | jq -r '.id')
PROJECT_TITLE=$(echo "$PROJECT_DATA" | jq -r '.title')

# Get status field information
FIELDS_DATA=$(gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json)
STATUS_FIELD=$(echo "$FIELDS_DATA" | jq -r '.[] | select(.name == "Status")')
STATUS_FIELD_ID=$(echo "$STATUS_FIELD" | jq -r '.id')
STATUS_OPTIONS=$(echo "$STATUS_FIELD" | jq -r '.options[] | "- **\(.name):** `\(.id)`"')
STATUS_MAPPINGS=$(echo "$STATUS_FIELD" | jq -r '.options[] | "- \"\(.name | ascii_downcase)\" → `\(.id)`"')
```

### 4. Generate Agent

1. Create `.claude/agents/` directory if it doesn't exist
2. If `github-project-manager.md` already exists, ask for confirmation before overwriting — the user may have hand-edited it, and the write is destructive
3. Generate the agent file from the template below, substituting the `{placeholder}` values with the data extracted in steps 2-3
4. Write to `.claude/agents/github-project-manager.md`
5. Confirm creation and provide usage instructions

## Important Guidelines

Beyond the numbered Process steps, hold to these non-obvious constraints:

- **Stop if `gh` auth fails** — every generated command depends on it; a half-authenticated run produces an agent with empty IDs.
- **Never guess project structure or status names** — derive every ID and status option from the GitHub API data, since a wrong mapping silently moves issues to the wrong column.

## Error Handling

- If project not accessible: "Cannot access project - check permissions and URL"

## Generated Agent Template

`{placeholder}` values come from the variables computed in steps 2-3:

````markdown
---
name: github-project-manager
description: Manage GitHub project board operations for moving issues between status columns
tools: Bash
---

You are a specialized agent for managing GitHub project board operations for the {PROJECT_TITLE} project.

## Project Details

- **Project URL:** {PROJECT_URL}
- **Owner:** `{OWNER}`
- **Project Number:** `{PROJECT_NUMBER}`
- **Project ID:** `{PROJECT_ID}`
- **Status Field ID:** `{STATUS_FIELD_ID}`

## Available Status Options

{STATUS_OPTIONS}

## Status Mappings

Map the user's natural-language status to a single-select option ID:

{STATUS_MAPPINGS}

## Core Functions

### List items on the board

```bash
gh project item-list {PROJECT_NUMBER} --owner {OWNER} --format json
```

Use this to find an item's `id` and its current status.

### Move an item to a status column

```bash
gh project item-edit --id <item-id> --project-id {PROJECT_ID} \
  --field-id {STATUS_FIELD_ID} --single-select-option-id <option-id>
```

`<item-id>` comes from the item-list output; `<option-id>` comes from the status mappings above.
````
