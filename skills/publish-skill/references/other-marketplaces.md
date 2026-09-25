# Other skill marketplaces (lighter reference)

These are either more specialized, lower-maturity, or move faster than the channels covered in depth elsewhere in this skill. Treat this file as a starting map, not a source of truth — before actually publishing to one of these, web search "`<name>` submit skill" or check the site's own current docs, since submission mechanics and CLIs here change faster than the git/npm/Claude-plugin routes.

## ClawHub — official marketplace for OpenClaw

OpenClaw agents pull skills from five sources; ClawHub is the official one, alongside a crypto/DeFi-specific store, skills.sh, plain GitHub repos, and bundled skills. All follow the same open AgentSkills format, so a skill already set up per `git-native.md` is generally installable through ClawHub or by pointing OpenClaw directly at the GitHub URL, unmodified. Typical install: `clawhub install <skill>`.

## LobeHub Skills

A larger, more productized directory (well over 100K skills indexed at last check). Install with:
```
npx @lobehub/market-cli skills install <id> --agent <agent-name>
```
Listing appears to be driven by crawling public repos the same way as skills.sh — a correctly-laid-out `skills/<name>/SKILL.md` in a public repo is generally sufficient, with no extra packaging step beyond what `git-native.md` already covers.

## agentskill.sh

Another fast-discovery directory (claims 100K+ skills, 20+ supported agent tools). Same underlying model as skills.sh and LobeHub — a public repo with the standard layout gets crawled and indexed rather than requiring a manual submission.

## Capafy — a genuinely different model: skill-as-a-service

Not a plain "install this file" marketplace. A Capafy listing runs the skill as a hosted agent-service; the end user consumes the *output* (e.g., "screen this resume," "make a viral video") without ever holding the skill file. Only worth setting up if the actual goal is monetization or a no-install end-user experience — otherwise it's a detour from general distribution. Check Capafy's own docs for the current publishing flow, since uploading a skill vs. connecting a repo and setting pricing is a genuinely different shape from every other channel in this skill.

## HiMarket — enterprise/internal skill marketplace

Aimed at organizations, not the public. An admin creates a "Skill product" in an admin console, uploads a ZIP-format skill package, and manages its lifecycle (draft → under review → online → offline) before publishing it to an internal developer portal, from which Agent Workers pull the package via CLI. Relevant specifically when the goal is **internal, access-controlled** distribution inside a company. For that use case, weigh this against just standing up a private GitHub repo per `git-native.md` — the private-repo route is simpler, free, and usually sufficient unless there's already organizational buy-in for a platform like this.

## A general caution about install counts and leaderboards on any of these

Publishing is easy across this whole ecosystem, which means "trending" or "most installed" lists can be dominated by a handful of prolific publishers rather than reflecting quality — one analysis found 10 of 88 sources accounting for over half of all listed skills in a sample. If the user is choosing what to *install* from one of these sites rather than publish to it, read the actual SKILL.md before trusting a ranking.
