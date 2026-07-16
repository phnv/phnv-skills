# 🤖 Agent Instructions: phnv-skills Codebase

This document is a dedicated reference guide for AI Agents (like Antigravity, Claude Code, or Cursor) collaborating on the `phnv-skills` repository. It defines directory architectures, metadata conventions, target IDE compatibility rules, and workflows for adding or modifying skills.

---

## 📂 Repository Architecture

- `skills/`: The source directory where all reusable skills reside.
  - `skills/<skill-name>/SKILL.md`: The main instruction file containing markdown guidelines and frontmatter.
  - `skills/<skill-name>/references/`: Optional folder storing reference logs, templates, or dependency lists.
- `src/`: The TypeScript source code of the CLI.
  - `src/cli.ts`: Entry point parsing arguments via `commander`.
  - `src/commands/add.ts`: Core copy-and-rename logic executing the installation mapping.
- `skills.json`: A static registry listing bundled skills and their sources.

---

## 🎨 Skill Metadata & Anatomy

Every skill is defined under `skills/<skill-name>/SKILL.md`. To remain compatible with the CLI and target editors, it **must** include a YAML frontmatter block at the very top:

```yaml
---
name: skill-name-matching-folder-name
description: "A comprehensive description of when the agent should activate/use this skill."
disable-model-invocation: false
---
```

### Writing Skill Guidelines:
- **Be Actionable:** Include specific commands, verification checks, and configuration details.
- **Provide Context:** Explain *why* certain boundaries (like WSL environments or lint rules) are enforced.
- **Include Diagnostics:** Write a section explaining how the agent should handle errors when executing instructions in the target environment.

---

## 🔄 Target Assistant & IDE Mappings

The CLI translates the `SKILL.md` template for different developer IDE environments as specified in `src/commands/add.ts`:

1.  **Cursor (`.cursor/rules/`)**:
    - Ext: `.mdc` (e.g. `skills/wsl-development-environment/SKILL.md` is copied as `.cursor/rules/wsl-development-environment/wsl-development-environment.mdc`).
    - Cursor uses `.mdc` files at this path to auto-trigger rules based on match patterns or semantic prompts.
2.  **GitHub Copilot (`.github/`)**:
    - Ext: `.md` (e.g. copied as `.github/wsl-development-environment/wsl-development-environment.md`).
3.  **Claude Code (`.claude/skills/`)**:
    - Ext: Keeps `SKILL.md` structure intact at `.claude/skills/wsl-development-environment/SKILL.md`.
4.  **Antigravity (`.agents/skills/`)**:
    - Ext: Keeps `SKILL.md` structure intact at `.agents/skills/wsl-development-environment/SKILL.md`.

> [!WARNING]
> When updating copy logic or adding new options to `src/commands/add.ts`, ensure that target renaming rules correctly preserve the relative path mappings of associated resource directories (like `references/`) if they are present.

---

## ⚙️ Workflow for Adding/Modifying Skills

When requested to create or update a skill, follow this exact progression:

### 1. Create/Modify the Skill Directory
- Directory: `skills/<skill-name>/`
- File: `skills/<skill-name>/SKILL.md`
- Make sure the frontmatter matches the directory name exactly.

### 2. Update the Registry
- Open `skills.json` at the root of the project.
- Register the new skill entry under the appropriate source object, matching the structure:
  ```json
  {
    "source": "your-source-identifier",
    "skills": [
      "your-new-skill-name"
    ]
  }
  ```

### 3. Build & Test
Compile the TypeScript CLI to verify it builds without errors:
```bash
npm run build
```

Verify your new skill displays properly using the compiled entrypoint:
```bash
node dist/cli.js add <skill-name>
```

---

## 🚫 Critical Constraints for AI Agents

- **Preserve YAML Frontmatter:** Never delete or alter the YAML frontmatter delimiters (`---`) or existing fields when modifying a skill unless explicitly instructed.
- **Linux-First Execution:** Always perform CLI compilation (`npm run build`) and verification runs within the WSL environment (following the rules in the `wsl-development-environment` skill).
- **Update the Registry:** Do not add a skill to `skills/` without also documenting it in `skills.json`.
