# npm packaging: skills-npm vs. skillpm

Both distribute a skill through the npm registry, but they solve different problems. Pick based on the question below — don't default to one without checking.

## Which one does the user actually want?

- **The skill only makes sense alongside a library/tool already published on npm**, and should always match whatever version of that library is installed → **skills-npm**. The skill rides inside the existing package.
- **The skill stands alone** — a workflow, a house style, a checklist — with no existing npm package to attach it to, and independent discoverability matters → **skillpm**. The skill *is* the package.
- **Both**, if the user maintains a library and also wants public discoverability: ship via skills-npm inside the library for version-locked consumers, and separately publish a thin skillpm package (or just a plain git repo per `git-native.md`) for people who haven't installed the library yet.

If genuinely unsure, ask: "Is this teaching agents to use a specific package you maintain, or is it a standalone capability?"

## Route A: skills-npm (skill rides inside an existing package)

**1. Add the skill inside the existing package**, at the package-relative path:
```
your-package/
├── package.json
├── src/...
└── skills/
    └── <skill-name>/
        └── SKILL.md
```

**2. Wire in skills-npm as a dev dependency:**
```bash
npm i -D skills-npm
npx skills-npm setup
```
`setup` merges into any existing `prepare` script (appends with `&&`, no-op if already wired) and adds `**/skills/npm-*` to `.gitignore`. From then on, consumers who `npm install` your package get the skill auto-symlinked into their local `skills/` folder without any extra step on their end.

**3. Validate, then publish the package exactly as normal — there's no separate "publish the skill" step:**
```bash
agentskills validate skills/<skill-name>
npm login          # run in the user's own terminal — needs their npm credentials
npm version patch  # or minor/major
npm publish
```
The skill ships with the next version of the package. Bump the version whenever the skill's instructions change meaningfully — treat it the same as a code change, since existing users' agents will pick up new behavior next time they update.

## Route B: skillpm (standalone skill package)

**1. Scaffold:**
```bash
npx skillpm init
```
This generates `skills/<skill-name>/SKILL.md` inside a new package — skillpm's convention wants the skill inside a `skills/` subfolder even for a standalone package. It also accepts older packages using a bare root-level `SKILL.md` (with a migration warning), so that's not a bug if the user encounters it in someone else's package.

**2. Fill in the skill, then validate:**
```bash
agentskills validate skills/<skill-name>
```

**3. Publish — run in the user's own terminal, needs npm auth:**
```bash
npm login
npx skillpm publish
```
This publishes to npmjs.org tagged with the `agent-skill` keyword, which is what surfaces it in the community Agent Skills Registry (searchable, filterable by keyword, sortable by downloads/recency) — no separate submission step required.

**4. Consumers install with:**
```bash
npx skillpm install <package-name>
```

## Versioning note (applies to both routes)

Treat a change to *what the skill instructs the agent to do* like a code change for semver purposes — at least a minor bump — since existing users pick up the new behavior automatically on their next install or update, not just new users.
