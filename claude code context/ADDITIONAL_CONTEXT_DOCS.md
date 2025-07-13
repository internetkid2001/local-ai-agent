# Supplemental Context Documents

This file contains fleshed-out versions of additional context documents that provide deeper technical and operational insight into the project. It covers Architecture Decision Records, Data Flow Diagrams, the Security Model, and the concept for a Live Context Report.

---

## 1. Architecture Decision Records (ADRs)

**Purpose**: To document significant architectural decisions, their rationale, and their consequences. This creates a historical log that guides future development and prevents re-litigation of settled design choices.

**Proposed Location**: `docs/adr/`

### ADR Template (`docs/adr/TEMPLATE.md`)

```markdown
# ADR-XXX: [Title of Decision]

- **Status**: Proposed / Accepted / Deprecated / Superseded
- **Date**: YYYY-MM-DD
- **Deciders**: [List of people involved in the decision]

## Context and Problem Statement

Describe the context and problem that this decision addresses. What is the issue we're trying to solve? What are the constraints and requirements?

## Decision Drivers

- [Driver 1] (e.g., Performance, Security, Maintainability)
- [Driver 2]

## Considered Options

1.  **[Option 1]**
    - Description of the option.
    - Pros: [List of advantages]
    - Cons: [List of disadvantages]

2.  **[Option 2]**
    - Description of the option.
    - Pros: [List of advantages]
    - Cons: [List of disadvantages]

## Decision Outcome

Chosen option: **[Option X]**, because [justification].

### Positive Consequences

- [Benefit 1]
- [Benefit 2]

### Negative Consequences

- [Drawback or trade-off 1]
- [Drawback or trade-off 2]

## Implementation Plan

- [High-level plan for implementing the decision]

## Links

- [Link to related documents, issues, or PRs]
```

---

## 2. Data Flow Diagrams

**Purpose**: To provide clear, visual representations of how data moves through the system for key processes. This helps in understanding component interactions and debugging issues.

**Proposed Location**: `docs/DATA_FLOW_DIAGRAMS.md`

### Example Data Flow: Complex Coding Task

This diagram illustrates the flow when a user asks the agent to perform a complex coding task.

```mermaid
graph TD
    A[User Request: "Refactor this module"] --> B{Task Router};
    B -->|Complexity: High| C[Context Manager];
    C -->|1. Gathers code from files| D(Advanced AI Bridge);
    C -->|2. Gathers screenshot of IDE| D;
    D -->|Sends packaged context| E[Claude Code API];
    E -->|Returns code with edits| D;
    D --> F{Filesystem MCP Server};
    F -->|Applies changes to file| G([local_project/module.py]);
    F --> H[Agent];
    H --> I[User Response: "I have refactored the module."];
```

---

## 3. Security Model

**Purpose**: To centralize the project's security philosophy, policies, and implementation details. For an agent with system access, this is a critical document.

**Proposed Location**: `docs/SECURITY_MODEL.md`

### Core Principles

1.  **Principle of Least Privilege**: The agent and its sub-components should only have the permissions absolutely necessary to perform a task.
2.  **Defense in Depth**: Multiple layers of security controls are in place, so if one fails, others can still protect the system.
3.  **Secure by Default**: The default configuration should be the most secure one. Risky features must be explicitly enabled by the user.
4.  **Human in the Loop**: For any potentially destructive or irreversible action, user confirmation is required.

### Security Layers

1.  **Sandboxing (Execution Layer)**:
    - All code execution via the `SystemControl` MCP server will be handled by a wrapper around **Open Interpreter**. This provides a battle-tested sandboxing environment.
    - File system operations will be restricted to user-defined paths in the configuration (`allowed_paths`). Access to sensitive system directories (`/etc`, `~/.ssh`) is strictly forbidden.

2.  **Validation (Input Layer)**:
    - All natural language commands that translate to file paths or shell commands will be sanitized to prevent injection attacks (e.g., a command like "delete file `foo; rm -rf /`").
    - The agent will use a deny-list of dangerous commands (`rm -rf`, `mkfs`, etc.) and will refuse to execute them without a special override.

3.  **Permissions (Application Layer)**:
    - The agent will have a simple, internal role-based access control (RBAC) system.
    - **Roles**: `viewer` (can read files, view screen), `editor` (can modify files), `executor` (can run code), `admin` (full access).
    - For the future multi-user web application, each user will be assigned a role that dictates what actions they can ask the agent to perform.

4.  **Confirmation (User Layer)**:
    - A list of `REQUIRE_CONFIRMATION` actions is defined in the configuration.
    - When a task involves one of these actions (e.g., `file_delete`, `execute_command`), the agent must stop and ask the user for explicit approval before proceeding.

---

## 4. Live Context Report Script

**Purpose**: To provide the AI with an up-to-the-minute snapshot of the project's state at the beginning of a development session. This bridges the gap between static documentation and the live codebase.

**Proposed Location**: `scripts/generate_context_report.sh`

### Script Implementation

```bash
#!/bin/bash

# This script generates a live context report for the AI.
# It should be run from the root of the project.

OUTPUT_FILE="LIVE_CONTEXT.md"

# --- Header ---
echo "# Live Project Context Report" > $OUTPUT_FILE
echo "Generated: $(date)" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

# --- Git Status ---
echo "## 1. Git Status" >> $OUTPUT_FILE
echo "```"
(git status) >> $OUTPUT_FILE
echo "```"

# --- Recent Commits ---
echo "## 2. Recent Commits" >> $OUTPUT_FILE
echo "```"
(git log -n 5 --pretty=format:'%h - %s (%cr)') >> $OUTPUT_FILE
echo "```"

# --- Project Structure ---
echo "## 3. Project Structure (src)" >> $OUTPUT_FILE
echo "```"
(tree -L 3 src) >> $OUTPUT_FILE
echo "```"

# --- TODOs and FIXMEs ---
echo "## 4. Action Items in Code" >> $OUTPUT_FILE
echo "```"
(grep -r -E "TODO|FIXME" src/ || echo "No TODOs or FIXMEs found.") >> $OUTPUT_FILE
echo "```"

# --- Test Coverage (Placeholder) ---
echo "## 5. Test Coverage" >> $OUTPUT_FILE
echo "```"
(echo "(Placeholder: Run 'pytest --cov=src' and paste results here)") >> $OUTPUT_FILE
echo "```"


echo "Report generated at $OUTPUT_FILE"

```
