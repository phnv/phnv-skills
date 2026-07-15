# 🧠 phnv-skills

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

## 🛠️ Usage

### Add a Skill to your Project
Navigate to your project directory and run:

```bash
phnv-skills add <skill-name>
```

The CLI will scan the current directory for agent triggers and copy the skill instructions to the correct destination folder (renaming files appropriately for the target agent).

### Install a Skill Globally
To make a skill available across all your Antigravity workspaces:

```bash
phnv-skills add <skill-name> --global
```
*This installs the skill instructions to `~/.gemini/config/skills/<skill-name>`.*

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

## ✍️ Contributing a New Skill

1. Fork and clone the repository.
2. Create a new directory under `skills/` (e.g., `skills/my-awesome-skill/`).
3. Add a `SKILL.md` inside that directory. The file **must** start with YAML frontmatter:
   ```yaml
   ---
   name: my-awesome-skill
   description: "A short summary explaining when the agent should invoke this skill."
   disable-model-invocation: false
   ---
   ```
4. Build the CLI package using:
   ```bash
   npm run build
   ```
5. Register your skill in the root `skills.json` catalog.
6. Submit a Pull Request!
