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

### 1. Validate Environment and Parse URL

First, verify the project setup:

- Check if current directory is a git repository
- Verify GitHub CLI (`gh`) is available and authenticated
- Parse the project URL to extract owner and project number
- Ensure .claude/agents/ directory exists or can be created

### 2. Extract Project Information from URL

From the URL `$1`, extract:

- Organization/owner name
- Project number

URL format: `https://github.com/orgs/[OWNER]/projects/[NUMBER]`

### 3. Fetch Project Details via GitHub CLI

Use GitHub CLI to automatically retrieve:

```bash
# Get project details
gh project view [PROJECT_NUMBER] --owner [OWNER] --format json

# Get project fields (to find status field)
gh project field-list [PROJECT_NUMBER] --owner [OWNER] --format json
```

### 4. Parse Project Information

Extract the required information from GitHub CLI responses:

```bash
# Parse owner and project number from URL
PROJECT_URL="$1"
OWNER=$(echo "$PROJECT_URL" | sed -n 's|https://github.com/orgs/\([^/]*\)/projects/.*|\1|p')
PROJECT_NUMBER=$(echo "$PROJECT_URL" | sed -n 's|.*/projects/\([0-9]*\).*|\1|p')

# Get project ID and details
PROJECT_DATA=$(gh project view "$PROJECT_NUMBER" --owner "$OWNER" --format json)
PROJECT_ID=$(echo "$PROJECT_DATA" | jq -r '.id')
PROJECT_TITLE=$(echo "$PROJECT_DATA" | jq -r '.title')

# Get status field information
FIELDS_DATA=$(gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json)
STATUS_FIELD=$(echo "$FIELDS_DATA" | jq -r '.[] | select(.name == "Status")')
STATUS_FIELD_ID=$(echo "$STATUS_FIELD" | jq -r '.id')

# Get status options
STATUS_OPTIONS=$(echo "$STATUS_FIELD" | jq -r '.options[] | "- **\(.name):** `\(.id)`"')
STATUS_MAPPINGS=$(echo "$STATUS_FIELD" | jq -r '.options[] | "- \"\(.name | ascii_downcase)\" → `\(.id)`"')
```

### 5. Create Agent Configuration

Generate a github-project-manager.md file in .claude/agents/ with the extracted information:

The agent will include:

- Project-specific IDs and configuration
- Pre-configured GitHub CLI commands
- Status mappings from the actual project
- Ready-to-use functions for issue management

### 6. Implementation Steps

1. Parse the project URL argument (`$1`)
2. Validate the current directory is a git repository
3. Verify GitHub CLI is available and authenticated
4. Extract owner and project number from URL
5. Fetch project details using GitHub CLI
6. Parse project ID, status field ID, and status options
7. Create .claude/agents/ directory if it doesn't exist
8. Generate the agent configuration with fetched details
9. Write the file to .claude/agents/github-project-manager.md
10. Confirm creation and provide usage instructions

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

- **Project URL:** https://github.com/orgs/[owner]/projects/[number]
- **Project ID:** `[actual-project-id]`
- **Status Field ID:** `[actual-status-field-id]`

## Available Status Options

[Auto-generated from actual project status options]

## Core Functions

[Pre-configured commands using actual project IDs]
```
