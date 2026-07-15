---
name: wsl-development-environment
description: "Ensure Linux-first execution when working on projects inside Windows Subsystem for Linux. Use when the user asks you to execute code, commands, or build tools; mention WSL, Windows Subsystem, or remote development; or need to run commands in an unfamiliar environment. Treats the Linux distribution as authoritative: shells, Python, Git, and build tools execute inside WSL, not Windows."
disable-model-invocation: false
---

# WSL Development Environment

When you execute code or commands, the agent must assume **Linux-first** — the working shell, Python interpreter, Git operations, and build tools all run inside the WSL Linux distribution, not on Windows. The IDE user interface may sit on Windows, but the **agent** sits in Linux.

This skill ensures predictable, observable execution by eliminating the most costly class of mistake: the wrong environment, discovered late.

## Before You Execute Any Command

The **verification step** is the foundation. Before running commands, establish three facts:

1. **Working directory**: `pwd`
2. **Python interpreter** (if needed): `which python && python --version`
3. **Virtual environment**: Activated? Run `source .venv/bin/activate` if `.venv` exists, then verify with `which python`

Do not guess the environment. Inspect it once, then act.

Example canonical check:

```bash
pwd                              # Confirm you are in the project root
python --version                 # Confirm you're using the right interpreter
which python                     # Confirm it's the WSL one, not Windows
```

## The Linux-First Rule

Assume:
- **Terminal shell**: Bash or Zsh (inside WSL)
- **Python interpreter**: Lives inside WSL
- **Git**: Executes inside WSL
- **Package manager**: uv, pip, poetry, conda — all inside WSL
- **Working directory**: Always the project root or an explicit subdirectory

Do not assume Windows PowerShell, Command Prompt, Windows Python, Windows paths, or Windows Git. When in doubt, inspect before guessing.

## Execution Policy

Follow this progression:

1. **Verify** — Run the canonical check above. Stop if anything is unclear.
2. **Navigate** — Change to project root if needed: `cd ~/projects/my_project` (use home-relative paths, not `/mnt/c/...`)
3. **Prepare** — Activate the virtual environment if one exists and isn't already active.
4. **Execute** — Run the command as a single, readable step.
5. **Diagnose** — If it fails, reread the error message and verify the environment (1–3 above) before retrying.

Execute commands sequentially and independently — one command per terminal step. Avoid chaining with `&&` or `;` unless the project explicitly uses that pattern.

## When Commands Fail

Environment problems surface as command failures. Before inventing solutions:

1. Read the error carefully.
2. Verify working directory.
3. Verify active interpreter and virtual environment.
4. Check whether the required tool exists: `which <tool>`.
5. Ask the user if ambiguity remains.

Do not immediately generate wrapper scripts, rewrite the command in another language, or install random dependencies. Diagnosis first.

## Python Environment

If a `.venv` directory exists:

```bash
source .venv/bin/activate
which python    # Should point into .venv, not /usr/bin
```

Never:
- install packages globally
- use Windows Python
- bypass the project's virtual environment

Prefer running tools directly (`pytest`, `ruff`, `pip`) instead of using explicit interpreter paths (`python -m pytest`), once the environment is activated.

## Filesystem Locations

Projects should live in the native Linux filesystem:

```bash
~/projects/my_project      # Good
/home/user/projects/       # Good
/mnt/c/Users/...           # Slow; warn the user
```

Heavy operations inside `/mnt/c` (Git clones, dependency installation, large file indexing) are significantly slower. Mention this trade-off to the user if needed.

## Line Endings & Scripts

Generate executable files (shell scripts, Dockerfiles, Makefiles, Python scripts for Linux) with LF line endings, never CRLF.

## Tooling Hierarchy

Prefer Linux-native tools in this order:

1. `uv` — Fast Python package installer
2. `pip` — Standard Python package manager
3. `poetry` — Dependency resolver
4. `conda` — Full environment manager
5. Native utilities: `git`, `pytest`, `ruff`, `grep`, `find`, `sed`, `jq`, `curl`, `tree`

Respect the project's chosen tool; do not mix package managers without explicit instruction.

## Git Operations

Git executes inside WSL. Use the configured authentication method:
- Linux SSH agent (preferred)
- Windows Git Credential Manager (if configured; do not modify unless asked)

Never perform destructive operations without user approval: no `git reset --hard`, `git push --force`, or `git clean -fd` without explicit consent. Always preserve user work.

---

## Reference

**Anti-patterns to avoid:**
- Running PowerShell instead of Bash
- Invoking Windows Python
- Writing helper scripts solely to execute shell commands
- Guessing interpreter locations
- Installing global packages
- Mixing Windows and Linux toolchains
- Modifying unrelated configuration files
- Escaping shell commands unnecessarily

**VS Code + WSL context:**
The IDE user interface runs on Windows, but the terminal, language server, and extension host run inside WSL. Workspace settings (`.vscode/settings.json`) are Linux-aware. Built-in localhost port forwarding is available; do not assume custom socket locations. Git Credential Manager integration works through existing Git configuration.

**Docker context:**
Determine the Docker setup first (Docker Desktop + WSL integration vs. native Linux Docker). Use the configured Docker context; do not assume socket paths. Avoid changing daemon configuration unless explicitly requested.

**Networking in WSL:**
Applications bind to `127.0.0.1` or `0.0.0.0`. Assume VS Code forwards localhost ports. Do not modify Windows Firewall.

---

## Guiding Principles

- **Linux is authoritative.** The environment inside WSL is the source of truth.
- **Verify before acting.** One inspection step saves retries.
- **Keep commands simple.** Direct execution beats generated wrappers.
- **Diagnose environment problems before changing code.** Most failures have environmental roots.
- **Minimize side effects.** Avoid global installs, wrapper scripts, and unrelated edits.
- **Ask rather than guess.** When in doubt about the environment, ask the user.
