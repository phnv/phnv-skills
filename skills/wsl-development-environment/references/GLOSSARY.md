# Glossary

## Linux-First

The foundational principle: assume the shell, Python interpreter, Git, and all build tools execute inside the WSL Linux distribution, not on Windows. It is the **source of truth** for the environment. Eliminates the most costly mistake class — discovering the wrong environment was used after commands have already run.

## WSL (Windows Subsystem for Linux)

A compatibility layer that runs a native Linux kernel inside Windows, letting you run Linux distributions, shell commands, and binaries without a virtual machine. For this skill, treat the Linux side as the execution environment.

## Verification Step

A three-part check performed before any command execution:
- Working directory (`pwd`)
- Python interpreter (`which python && python --version`)
- Virtual environment status (activated or not)

Cheap to do once, expensive to skip.

## Virtual Environment

An isolated Python environment (`.venv`, created by `python -m venv` or `uv venv`) that contains project-specific packages and an isolated Python interpreter. Must be activated before running Python commands or package managers in the project.

## Activation (Virtual Environment)

Running `source .venv/bin/activate` to enable the isolated Python interpreter and package manager. After activation, `python`, `pip`, and other tools refer to the virtual environment's versions, not system-wide ones.

## Source of Truth

The Linux distribution running inside WSL is the authoritative environment for all shell, Python, and Git operations. Windows PowerShell, Command Prompt, and Windows Python are **not** the source of truth for this project.

## Canonical Check

The minimal set of commands that establish the environment state without ambiguity:

```bash
pwd
python --version
which python
```

If any of these produces unexpected output, environment issues must be diagnosed before proceeding.

## Native Linux Filesystem

Paths inside the Linux distribution (`/home/user/project`, `~/projects`), not Windows paths (`/mnt/c/Users/...`). Operations on native Linux filesystem are significantly faster and more reliable.

## Sprawl (in WSL context)

Unnecessary detail that obscures the core Linux-first principle. Avoided by keeping commands simple, avoiding chained shell expressions, and disclosing reference material behind context pointers.

## Duplication

Repeating the same environmental rule or verification step multiple times without consolidation. The main skill consolidates all environment verification into a single **verification step**.

## Premature Completion

Ending a step (e.g., "verify environment") before it's genuinely done. Mitigated by a clear **completion criterion**: all three parts of the canonical check must pass before moving to the next step.
