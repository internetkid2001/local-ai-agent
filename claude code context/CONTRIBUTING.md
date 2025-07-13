# Contributing to the Local AI Agent

First off, thank you for considering contributing! This document provides guidelines for contributing to this project. Following these guidelines helps to ensure a smooth and effective development process for everyone involved.

## Table of Contents
- [Setting up the Development Environment](#setting-up-the-development-environment)
- [Coding Style](#coding-style)
- [Git Workflow](#git-workflow)
  - [Branching Strategy](#branching-strategy)
  - [Commit Messages](#commit-messages)
- [Running Tests](#running-tests)
- [Submitting Changes](#submitting-changes)

## Setting up the Development Environment

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/local-ai-agent.git
    cd local-ai-agent
    ```

2.  **Create a Python virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    The project's Python dependencies are listed in `docs/requirements_txt.txt`.
    ```bash
    pip install -r docs/requirements_txt.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the root of the project by copying the example template.
    ```bash
    cp .env.example .env
    ```
    Fill in the required values in the `.env` file, such as API keys and configuration paths.

## Coding Style

To maintain consistency across the codebase, please adhere to the following style guidelines:

-   **Formatting**: This project uses `black` for code formatting and `ruff` for linting. Please run these tools before committing your code.
-   **Type Hinting**: All function signatures and class variables should include type hints from Python's `typing` module.
-   **Docstrings**: All modules, classes, and functions should have comprehensive docstrings explaining their purpose, arguments, and return values.
-   **Templates**: Follow the code structure templates outlined in `claude code context/claude-code-templates.md` for new classes and modules.

## Git Workflow

### Branching Strategy

-   **`main`**: This branch contains stable, production-ready code. Direct pushes are forbidden.
-   **`dev-phase-X`**: These branches (`dev-phase-1`, `dev-phase-2`, etc.) correspond to the major development phases. They are the base for feature branches.
-   **`feature/...`**: All new features or bug fixes should be developed on a feature branch. Branch off from the current `dev-phase-X` branch.
    ```bash
    # Example
    git checkout dev-phase-1
    git pull
    git checkout -b feature/new-mcp-tool
    ```

### Commit Messages

Commit messages should be structured and descriptive. Follow the format:

`[PHASE-X] Component: Brief description of changes`

-   **PHASE-X**: The current development phase (e.g., `PHASE-1`).
-   **Component**: The part of the system you're working on (e.g., `MCP Client`, `Task Router`).
-   **Description**: A concise summary of the changes.

**Examples:**
```
[PHASE-1] MCP Client: Add async connection handling with retry logic
[PHASE-2] Docs: Update architecture decisions for screenshot storage
```

## Running Tests

The project uses `pytest` for testing.

-   **Run all unit tests:**
    ```bash
    pytest tests/
    ```

-   **Run integration tests:**
    Integration tests are marked with `@pytest.mark.integration`. To run them specifically:
    ```bash
    pytest -m integration
    ```

-   **Test Coverage**: Please ensure that new code is accompanied by tests, maintaining or increasing the overall test coverage.

## Submitting Changes

1.  Make sure your code lints and all tests pass.
2.  Commit your changes using the specified commit message format.
3.  Push your feature branch to the remote repository.
    ```bash
    git push origin feature/new-mcp-tool
    ```
4.  Open a Pull Request (PR) from your feature branch to the corresponding `dev-phase-X` branch.
5.  In the PR description, provide a clear summary of the changes and link to any relevant issues.
