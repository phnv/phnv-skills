# Appendices

These sections provide technical detail for specific situations. Consult them only when the context applies to your work.

## A. VS Code + WSL Integration

**When to use:** You're working with VS Code as the IDE, and the terminal or language server behaves unexpectedly.

The IDE user interface runs on Windows, but the terminal, language server, and extension host all run inside WSL. This split means:

- Generated code and executed commands are Linux-native.
- Workspace settings (`.vscode/settings.json`) are Linux-aware; modify them instead of Windows-global settings when project-specific behavior is needed.
- The Linux `code` CLI is available inside WSL if you need to interact with the editor from the terminal.
- Open documents may use `vscode-remote://wsl+<distro>/...` URIs; do not assume `file://` schemes.
- VS Code's built-in localhost port forwarding works by default; do not assume custom socket locations.

## B. Git Authentication in WSL

**When to use:** You need to push, pull, or clone a repository and authentication fails.

Git runs inside WSL. Authentication is handled via:
1. **Preferred:** Linux SSH agent (`ssh-agent`, `ssh-add`). Check with `ssh-add -l` to list keys.
2. **Fallback:** Windows Git Credential Manager, if already configured in the WSL Git config. Use it through the existing configuration; do not invoke `git-credential-manager.exe` directly or modify credential helpers unless asked.

To verify the current Git configuration:

```bash
git config --show-origin credential.helper
```

Do not modify credential configuration unless explicitly requested.

## C. Docker in WSL

**When to use:** The project uses Docker and you need to build or run containers.

Determine the Docker setup first:
- **Docker Desktop with WSL integration:** The Docker daemon runs on Windows; WSL can access it. Docker commands run inside WSL and communicate with the Windows daemon.
- **Native Linux Docker:** The Docker daemon runs inside WSL. Commands run directly in WSL.

In both cases, use the configured Docker context; do not assume socket paths like `/var/run/docker.sock`. Verify the context:

```bash
docker context ls
docker context show
```

Avoid changing Docker daemon configuration unless explicitly instructed.

## D. Networking in WSL

**When to use:** Your application needs to listen on a port or communicate with another service.

**Binding:** Applications running inside WSL should bind to:
- `127.0.0.1` — localhost only (default for local development)
- `0.0.0.0` — all interfaces (if the project requires external access)

**Port forwarding:** VS Code's built-in localhost forwarding works automatically. Do not assume custom socket locations or modify WSL networking configuration unless asked.

**Windows Firewall:** Do not modify Windows Firewall settings. If communication with a Windows service is needed, use the WSL networking configuration (e.g., `/etc/resolv.conf` on traditional WSL setups) to determine the correct host address; do not assume `localhost` always resolves to Windows.

## E. Package Manager Decisions

**When to use:** You're deciding which tool to use for dependency management.

Respect the project's chosen tool. Order of preference if not specified:
1. **uv** — Fastest Python installer, best for CI/CD and local development
2. **pip** — Standard Python package manager
3. **poetry** — Full dependency resolver and lock file management
4. **conda** — Full environment manager (slowest, but useful for non-Python dependencies)

Never mix package managers (e.g., `pip install` + `poetry add` in the same project) without explicit instruction. Always install into the active virtual environment, never globally.

## F. Testing Execution

**When to use:** The project uses pytest or another test runner.

Prefer the smallest meaningful execution:

```bash
# Specific test file
pytest tests/unit/test_service.py

# Test directory
pytest tests/unit

# Full suite
pytest
```

Avoid running the full suite without necessity. If a single test fails, understand the failure before running the full suite.

## G. Linting and Type Checking

**When to use:** Code quality checks are part of the project workflow.

Common tools run inside WSL:
- `ruff check` — Fast linter
- `ruff format` — Code formatter
- `mypy` — Type checker
- `pytest` — Test runner

All respect the project's `pyproject.toml` or `setup.cfg` configuration. Run them after verifying the virtual environment is active.

## H. Handling Slow Operations on `/mnt/c`

**When to use:** The project is located under `/mnt/c` and operations are very slow.

File-intensive operations (Git clones, dependency installation, large indexing) are significantly slower inside `/mnt/c` than the native Linux filesystem. Mention this trade-off to the user if you observe slowness, and suggest migrating to the native Linux filesystem if the project is large.

## I. Line Endings and Script Generation

**When to use:** You're creating shell scripts, Dockerfiles, Makefiles, or other executable files.

Generate with LF line endings only, never CRLF. This includes:
- Shell scripts (`.sh`)
- Dockerfiles
- Makefiles
- Python scripts destined for Linux execution
- Configuration files that may be parsed by shell (`.bashrc`, `.zshrc`, etc.)

Most text editors inside WSL use LF by default; ensure it's set explicitly if the file editor allows it.

## J. Avoiding Common Anti-Patterns

**When to use:** You're uncertain whether a proposed action is safe or aligned with this skill.

Do not:
- Run PowerShell instead of Bash
- Invoke Windows Python (`python.exe`)
- Write helper scripts solely to execute shell commands
- Create enormously chained shell commands
- Guess interpreter locations without verifying
- Install packages globally outside the virtual environment
- Mix Windows and Linux toolchains in a single command
- Escape shell commands unnecessarily or over-complexly
- Modify unrelated configuration files as a side effect of main work

These patterns are costly to debugging and reduce predictability.
