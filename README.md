# phnv-skills

The CLI automatically detects which AI assistant ecosystem your project uses (Cursor, Copilot, Claude, or Antigravity) and configures the skill output to match that assistant's native format.

---

## 🚀 Installation

Install the package globally using npm:

```bash
npm install -g phnv-skills
```

Or execute it directly using `npx`:

```bash
npx phnv-skills --help
```

---

## ⚙️ How It Works (Auto-Detection Mappings)

When running `phnv-skills add <skill-name>`, the CLI checks the current directory for specific files or folders (Triggers). It installs the skill into the appropriate directory and adjusts the file format according to the table below:

| Agent Assistant | Trigger Directory | Installation Destination | Main File Output |
| :--- | :--- | :--- | :--- |
| **Cursor** | `.cursor/` | `.cursor/rules/<skill-name>/` | `<skill-name>.mdc` |
| **GitHub Copilot** | `.github/` | `.github/<skill-name>/` | `<skill-name>.md` |
| **Claude Code** | `.claude/` | `.claude/skills/<skill-name>/` | `SKILL.md` |
| **Antigravity** | `.agents/` | `.agents/skills/<skill-name>/` | `SKILL.md` |
| **Fallback** | *(No triggers found)* | `.agents/skills/<skill-name>/` | `SKILL.md` |

> [!NOTE]
> If multiple triggers are found, `phnv-skills` will copy the skill to all detected assistant folders in the directory.

---

## 📚 Skill Catalog

Current available skills in the library:

*   **`wsl-development-environment`**: Establishes a Linux-first execution rule, environment verification sequences, and proper toolchain usage policies when writing code or running terminal commands inside Windows Subsystem for Linux (WSL).

---