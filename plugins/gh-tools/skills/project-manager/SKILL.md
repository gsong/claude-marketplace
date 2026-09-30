---
name: "project-manager"
description: "Generate a .claude/agents/ agent that moves items on a GitHub project board, from the board's URL."
disable-model-invocation: true
compatibility: "Requires the gh CLI (authenticated) with the project scope."
argument-hint: "<project-url>"
---

# GitHub Project Manager

Create a specialized agent for managing GitHub project board operations using a GitHub project URL.

## Process

### 1. Validate Environment

- If current directory is not a git repository: show "This command must be run in a git repository" and stop
- If GitHub CLI (`gh`) is not available or not authenticated: show "GitHub CLI must be installed and authenticated" and stop. Every generated command depends on it; a half-authenticated run writes an agent with empty IDs.
- If no URL in `$ARGUMENTS`: show "Usage: /gh-tools:project-manager <project-url>" and stop

### 2. Parse URL and Fetch Project Details

From `$ARGUMENTS`, extract owner and project number, then fetch the project and its Status field. Run the block below as one Bash call: each Bash call is a fresh shell, so the parse and the fetch must run together for the variables to reach the fetch.

Supported URL formats:

- `https://github.com/orgs/[OWNER]/projects/[NUMBER]` (organization projects)
- `https://github.com/users/[OWNER]/projects/[NUMBER]` (personal projects)

```bash
# Parse owner and project number from URL (handles both orgs/ and users/)
# ERE via -E works on both BSD and GNU sed; # delimiter avoids clashing with URL slashes
PROJECT_URL="$ARGUMENTS"
read -r OWNER PROJECT_NUMBER <<< "$(echo "$PROJECT_URL" |
  sed -E -n 's#^https://github\.com/(orgs|users)/([^/]+)/projects/([0-9]+).*#\2 \3#p')"
if [ -z "$OWNER" ] || [ -z "$PROJECT_NUMBER" ]; then echo "Invalid GitHub project URL format" >&2; exit 1; fi

# Get project details
if ! PROJECT_DATA=$(gh project view "$PROJECT_NUMBER" --owner "$OWNER" --format json) ||
  ! FIELDS_DATA=$(gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json); then
  echo "Cannot access project - check permissions and URL" >&2; exit 1
fi
PROJECT_ID=$(echo "$PROJECT_DATA" | jq -r '.id')
PROJECT_TITLE=$(echo "$PROJECT_DATA" | jq -r '.title')

# Get status field information
STATUS_FIELD=$(echo "$FIELDS_DATA" | jq -r '.[] | select(.name == "Status")')
STATUS_FIELD_ID=$(echo "$STATUS_FIELD" | jq -r '.id')
STATUS_OPTIONS=$(echo "$STATUS_FIELD" | jq -r '.options[] | "- **\(.name):** `\(.id)`"')
STATUS_MAPPINGS=$(echo "$STATUS_FIELD" | jq -r '.options[] | "- \"\(.name | ascii_downcase)\" → `\(.id)`"')

# Print every value: the next Bash call is a fresh shell, so this output is the only record
echo "PROJECT_ID=$PROJECT_ID"
echo "PROJECT_TITLE=$PROJECT_TITLE"
echo "STATUS_FIELD_ID=$STATUS_FIELD_ID"
echo "STATUS_OPTIONS:"; echo "$STATUS_OPTIONS"
echo "STATUS_MAPPINGS:"; echo "$STATUS_MAPPINGS"
```

The block stops with "Invalid GitHub project URL format" if the URL does not parse, and with "Cannot access project - check permissions and URL" if `gh` cannot read the project. Either way, show the message and stop.

Every ID and status option in the generated agent comes from this output; a guessed mapping silently moves issues to the wrong column.

### 3. Generate Agent

1. Create `.claude/agents/` directory if it doesn't exist
2. If `github-project-manager.md` already exists, ask for confirmation before overwriting — the user may have hand-edited it, and the write is destructive
3. Generate the agent file from the template below, substituting the `{placeholder}` values with the data extracted in step 2
4. Write to `.claude/agents/github-project-manager.md`

Done when `.claude/agents/github-project-manager.md` exists, contains no `{placeholder}`, and lists every option of the Status field. Then tell the user how to invoke it.

## Generated Agent Template

`{placeholder}` values come from the variables computed in step 2:

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
