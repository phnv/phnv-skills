# phnv-skills

[![skills.sh](https://skills.sh/b/phnv/phnv-skills)](https://skills.sh/phnv/phnv-skills)

A collection of reusable AI agent skills. The CLI auto-detects which AI assistant ecosystem your project uses (Cursor, Copilot, Claude Code, or Antigravity) and copies the skill into the correct location and format.

---

## 🚀 Installation

Install skills from this repository using the [skills CLI](https://skills.sh):

```bash
npx skills add phnv/phnv-skills
```

This installs **all** skills from the repo. To install a single skill by name:

```bash
npx skills add phnv/phnv-skills --skill wsl-development-environment
```

### Global install (Antigravity / Gemini)

To install a skill globally into `~/.gemini/config/skills` so every project can use it, pass the `--global` (`-g`) flag to the project's own CLI:

```bash
npx phnv-skills add wsl-development-environment --global
```

---

## ⚙️ How It Works (Auto-Detection Mappings)

When a skill is installed into a project, the CLI scans the current directory for known trigger folders. It copies the skill to every matching destination and adjusts the file format accordingly:

| Agent Assistant | Trigger Directory | Installation Destination | Main File |
| :--- | :--- | :--- | :--- |
| **Cursor** | `.cursor/` | `.cursor/rules/<skill-name>/` | `<skill-name>.mdc` |
| **GitHub Copilot** | `.github/` | `.github/<skill-name>/` | `<skill-name>.md` |
| **Claude Code** | `.claude/` | `.claude/skills/<skill-name>/` | `SKILL.md` |
| **Antigravity** | `.agents/` | `.agents/skills/<skill-name>/` | `SKILL.md` |
| **Fallback** | *(none found)* | `.agents/skills/<skill-name>/` | `SKILL.md` |

> [!NOTE]
> If multiple triggers are detected, the skill is copied to **all** matching assistant directories in one run.

---

## 📚 Skill Catalog

Skills available in this repository:

*   **`wsl-development-environment`** — Establishes a Linux-first execution rule, environment verification sequences, and proper toolchain usage policies when writing code or running terminal commands inside Windows Subsystem for Linux (WSL).

Browse & install this skill on **[skills.sh/phnv/phnv-skills](https://skills.sh/phnv/phnv-skills)**.

---