---
name: github-project-manager
description: Use when the user wants to create a specialized agent for managing a GitHub project board, or when the user invokes /github-project-manager with a project URL.
---

# GitHub Project Manager

Create a specialized agent for managing GitHub project board operations using a GitHub project URL.

**Usage:** `/github-project-manager <project-url>`

**Example:** `/github-project-manager https://github.com/orgs/sahajsoft/projects/112`

## Core Requirements

- Extract project information from the provided GitHub project URL
- Use GitHub CLI to fetch project details automatically
- Generate a project-specific agent for GitHub project board management
- Create the agent in the project's .claude/agents/ directory
- Ensure the agent has all required GitHub CLI commands pre-configured

## Process

### 1. Validate Environment

- Check if current directory is a git repository
- Verify GitHub CLI (`gh`) is available and authenticated
- If no URL in `$ARGUMENTS`: show "Usage: /github-project-manager <project-url>" and stop

### 2. Parse URL and Extract Project Info

From `$ARGUMENTS`, extract owner and project number.

Supported URL formats:

- `https://github.com/orgs/[OWNER]/projects/[NUMBER]` (organization projects)
- `https://github.com/users/[OWNER]/projects/[NUMBER]` (personal projects)

```bash
# Parse owner and project number from URL (handles both orgs/ and users/)
PROJECT_URL="$ARGUMENTS"
OWNER=$(echo "$PROJECT_URL" | sed -n 's|https://github.com/\(orgs\|users\)/\([^/]*\)/projects/.*|\2|p')
PROJECT_NUMBER=$(echo "$PROJECT_URL" | sed -n 's|.*/projects/\([0-9]*\).*|\1|p')
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
2. If `github-project-manager.md` already exists, ask for confirmation before overwriting
3. Generate the agent file with extracted project IDs, status mappings, and pre-configured commands
4. Write to `.claude/agents/github-project-manager.md`
5. Confirm creation and provide usage instructions

## Important Guidelines

### Always:

- Verify GitHub CLI is available before proceeding
- Parse the project URL to extract owner and project number
- Use GitHub CLI to fetch all project information automatically
- Generate proper status mappings from GitHub API data
- Create the .claude/agents/ directory if it doesn't exist
- Provide clear next steps after agent creation

### Never:

- Proceed without a valid project URL argument
- Create the agent without validating the environment
- Proceed if GitHub CLI authentication fails
- Overwrite existing github-project-manager.md without confirmation
- Make assumptions about project structure or status names

## Error Handling

- If no URL provided: "Usage: /github-project-manager <project-url>"
- If invalid URL format: "Invalid GitHub project URL format"
- If not in a git repository: "This command must be run in a git repository"
- If `gh` CLI not available: "GitHub CLI must be installed and authenticated"
- If project not accessible: "Cannot access project - check permissions and URL"
- If .claude directory doesn't exist: Create it automatically
- If github-project-manager.md exists: Ask for confirmation before overwriting

## Example Generated Agent

The command will generate an agent similar to:

```yaml
---
name: github-project-manager
description: Manage GitHub project board operations for moving issues between status columns
tools: Bash
---

You are a specialized agent for managing GitHub project board operations for the [Project Title] project.

## Project Details

- **Project URL:** [actual project URL from $ARGUMENTS]
- **Project ID:** `[actual-project-id]`
- **Status Field ID:** `[actual-status-field-id]`

## Available Status Options

[Auto-generated from actual project status options]

## Core Functions

[Pre-configured commands using actual project IDs]
```
