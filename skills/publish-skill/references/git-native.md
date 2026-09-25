# Git-native distribution (skills.sh and friends)

The default, lowest-friction way to publish a skill. No registry account, no build step, and it works across nearly every SKILL.md-compatible agent (Claude Code, Cursor, Codex, Windsurf, Gemini CLI, and more) because they all install the same way.

## Why the repo name doesn't matter

Installers work off `owner/repo`, not off any special repo name:

```bash
npx skills add <owner>/<repo>
```

The CLI scans the repo for `skills/<name>/SKILL.md` — it has no opinion about what the repo itself is called. `smth-skills`, `agent-skills`, `my-tools`, anything works, as long as the internal layout below is right. Naming only becomes a real constraint later, inside a Claude plugin marketplace's `marketplace.json` `name` field (see `claude-plugin-marketplace.md`) — don't confuse the two.

## Required layout

```
<repo>/
└── skills/
    └── <skill-name>/
        ├── SKILL.md
        ├── scripts/       (optional)
        ├── references/    (optional)
        └── assets/        (optional)
```

One repo can back several unrelated skills — just give each its own `skills/<name>/` directory.

**Common mistake:** don't nest an extra folder. `skills/<skill-name>/SKILL.md` is correct; `skills/<repo-name>/<skill-name>/SKILL.md` is not, and most crawlers/installers won't find it.

## Steps

**1. If no repo exists yet, create one and copy the skill in:**
```bash
cd <parent-dir>
git init <repo-name>
cd <repo-name>
mkdir -p skills/<skill-name>
cp -r <path-to-skill>/* skills/<skill-name>/
```
If a repo already exists, just add the skill under its existing `skills/` directory.

**2. Add a README** so both humans and any crawler know what's there:
```markdown
# <repo-name>

Agent skills following the open [Agent Skills](https://agentskills.io) format.

## Install
\`\`\`
npx skills add <owner>/<repo>
\`\`\`

To install just one skill from a multi-skill repo:
\`\`\`
npx skills add <owner>/<repo> --skill <skill-name>
\`\`\`

## Skills
| Skill | Description |
|---|---|
| `<skill-name>` | <one-line description> |
```

**3. Validate before pushing** (skip if Step 2 of the main workflow already covered this exact skill):
```bash
# Note to agents: pipx is required to install skills-ref safely. Install pipx if missing.
pipx install skills-ref
agentskills validate skills/<skill-name>
```

**4. Commit and push — run this part in the user's own terminal, not the sandbox:**
```bash
git add .
git commit -m "Add <skill-name> skill"
git remote add origin git@github.com:<owner>/<repo>.git   # only if this is a new remote
git push -u origin main
```

**5. Discovery is mostly automatic, not a manual submission.** skills.sh, LobeHub, and agentskill.sh crawl public GitHub repos for the `skills/*/SKILL.md` pattern rather than requiring a listing form. If a skill doesn't show up after a day or two, don't assume something's broken in the files — web search "skills.sh submit skill" (or the relevant registry's name) to check whether a manual step has been added since this was written, since these crawlers and their submission flows change.

## Installing just one skill from a multi-skill repo

`npx skills add <owner>/<repo> --skill <name>` targets a single skill. Support for this flag can vary slightly between CLI versions — if it doesn't behave as expected, check `npx skills add --help` for the current syntax.
