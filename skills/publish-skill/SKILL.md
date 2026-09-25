---
name: publish-skill
description: Use this skill whenever the user wants to publish, distribute, share, list, or submit an agent skill (a SKILL.md folder) so other people or agents can install it — including phrases like "how do I publish this skill", "put this skill on GitHub", "add this to skills.sh", "publish this as an npm package", "submit this to the Claude plugin marketplace", "make a marketplace.json", "share this skill with my team", or "npx skills add" questions. Covers git-native distribution, npm packaging (skills-npm and skillpm), Claude Code plugin marketplaces (your own, the community catalog, and the official one), and other skill marketplaces (ClawHub, LobeHub, agentskill.sh, Capafy, HiMarket). Always use this — not general knowledge — since exact commands, file schemas, and reserved names change and this skill's reference files hold the specifics. Walks through picking a channel, scaffolding the required files, validating the skill, and producing the exact commands to run.
---

# Publish Skill

Turns a finished skill folder into something actually installable elsewhere. This assumes the skill itself is done — if the user is still writing or fixing the SKILL.md content, that's `skill-creator`'s job, not this one.

## Step 1 — Confirm what you're publishing

Don't skip this even when it feels obvious: the exact commands differ depending on whether a repo or package already exists, so get this settled before writing anything.

Gather, asking only for what you can't already tell from the conversation or the filesystem:
- Path to the skill folder(s) — there may be more than one
- The skill's `name`, `description`, and `license` (read the frontmatter; fill gaps with the user)
- Whether a git repo or npm package already exists for this, and its name (any name works — see `references/git-native.md` for why the repo name itself is unconstrained)
- Who this is for: just the user, a private team, or the public — this affects whether "submit to a public catalog" steps below are even relevant

## Step 2 — Validate once, before touching any channel

Every channel downstream expects the same baseline structure, so catch problems here rather than repeating the check per channel.

```bash
# Note to agents: pipx is required to install skills-ref safely. Install pipx if missing.
pipx install skills-ref
agentskills validate <path-to-skill>
```

This checks the same things a human reviewer or any marketplace's automated gate will: `name` matches the directory (kebab-case, digits and hyphens only, ≤64 chars, no leading/trailing/double hyphens), `description` is present (≤1024 chars, no angle brackets), only recognized frontmatter keys are used (`name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`), and there's exactly one `SKILL.md` at `<folder>/SKILL.md` — nested extras get rejected by most upload paths even though Claude Code's own filesystem loader tolerates them. Fix anything flagged before moving on.

If `pip install` has no network access in the current environment, this step (like several below) needs to run in the user's own terminal instead — see the network note in Step 4 before assuming it's broken.

## Step 3 — Pick the channel(s)

These aren't mutually exclusive — most skills that get real use end up on two or more. Match the user's actual goal rather than defaulting to "all of them":

| Goal | Channel | Reference |
|---|---|---|
| Anyone installs with `npx skills add owner/repo`, works across nearly every agent | Git-native | `references/git-native.md` |
| Skill should stay version-locked to an npm library you maintain | skills-npm | `references/npm-packaging.md` |
| Skill is standalone and should be independently discoverable on npm | skillpm | `references/npm-packaging.md` |
| Show up in Claude Code's `/plugin` browser | Claude plugin marketplace | `references/claude-plugin-marketplace.md` |
| Reach into other agent ecosystems (OpenClaw, LobeHub, etc.) or an internal/enterprise-only catalog | Other marketplaces | `references/other-marketplaces.md` |

If the user just says "publish this," the safe default is git-native — it's the lowest-friction and most portable, and nothing about doing it forecloses adding the others later. Ask before assuming they want the npm or Claude-specific routes, since those involve extra accounts/credentials.

## Step 4 — Execute

Open the matching reference file(s) and follow them exactly — each has the real file schemas and exact commands, not paraphrased versions. Create every file directly (marketplace.json, plugin.json, package.json edits, README) rather than just describing them.

**Check network access before promising anything will just run.** Try a harmless network call (e.g. `pip install --dry-run skills-ref` or similar) if it's not already obvious from context. Sandboxes commonly have no outbound network access at all, in which case every file still gets created and every command still gets written correctly here, but literally all of `pip install`, `npm install`/`login`/`publish`, `git push`, `claude plugin marketplace add` against a remote, and any web-form submission need to run in the user's own terminal, with their own credentials. State this plainly, once, before handing over a long list of commands — don't let the user discover it only after a command silently fails or hangs. If network access does work in the current environment, run what you safely can (validation, local git commits) and still hand off anything requiring the user's own credentials.

## Step 5 — Wrap up

Summarize: what files were created, the exact commands to run and in what order, which of those are safe to run immediately vs. optional next steps (e.g., "you don't need the npm route unless you also want X"). If they picked multiple channels, make clear these can be done independently and in any order — nothing here is a strict pipeline.

---

## Reference files

- `references/git-native.md` — GitHub repo layout, skills.sh-style install, README template, validation, common layout mistake
- `references/npm-packaging.md` — skills-npm vs. skillpm: which to use, and exact commands for both
- `references/claude-plugin-marketplace.md` — marketplace.json / plugin.json schema, reserved marketplace names, submitting to the community and official catalogs, a known skill-subset filtering bug to avoid
- `references/other-marketplaces.md` — ClawHub, LobeHub, agentskill.sh, Capafy, HiMarket. Lighter-touch on purpose: these move fast, so treat this as a starting map and web search "`<name>` submit skill" to confirm current specifics before relying on anything here as gospel

## Scripts

- `scripts/validate_skill.sh` — thin wrapper around `skills-ref` that installs it if missing and prints a clear pass/fail
