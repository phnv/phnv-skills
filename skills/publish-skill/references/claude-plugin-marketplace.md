# Claude Code plugin marketplace

A Claude Code "plugin" is a superset of a skill — it can bundle skills, subagents, hooks, commands, and MCP server config together, and a plugin is what actually shows up in the `/plugin` browser. A skill with nothing else going on can still be wrapped as a one-skill plugin purely to get this distribution channel; that's a normal, common case, not a hack.

## Two files, two different jobs — don't conflate them

- **`.claude-plugin/marketplace.json`** — the *catalog*. Lists one or more plugins and where to find each one's source.
- **`<plugin-root>/.claude-plugin/plugin.json`** — the *manifest* for one plugin. The plugin's actual content — a `skills/` folder, agents, hooks, commands, MCP config — lives at the plugin root next to this file, not inside `.claude-plugin/` itself.

## Minimal marketplace.json

```json
{
  "name": "<your-marketplace-name>",
  "owner": { "name": "<you-or-org>", "email": "<contact-email>" },
  "plugins": [
    {
      "name": "<plugin-name>",
      "source": "./",
      "version": "1.0.0",
      "description": "<one line, what it does>",
      "category": "productivity",
      "keywords": ["<keyword1>", "<keyword2>"]
    }
  ]
}
```

`source` can be `"./"` (this same repo/root), a relative path like `"./plugins/<name>"` when one repo hosts several plugins, or `{ "source": "github", "repo": "org/name" }` to point at a different repo entirely.

## Minimal plugin.json

```json
{
  "name": "<plugin-name>",
  "version": "1.0.0",
  "description": "<one line>",
  "skills": ["<skill-name>"]
}
```
The `skills` field here lists custom skill directories for *this plugin* — omit it entirely to just use the plugin's default `skills/` folder; only set it when you need something other than that default.

## Naming: the git repo name is unrestricted — the marketplace `name` field isn't

This is easy to conflate with repo naming, but it's a different rule entirely: the JSON `name` field inside `marketplace.json` is what Claude.ai's marketplace sync checks, not the GitHub repo name. Real projects have kept reserved-sounding repo names (e.g. a repo literally called `agent-skills`) and only had to change the *value inside the manifest*. Anthropic currently rejects these `name` values in marketplace.json:

```
agent-skills
claude-code-marketplace
claude-code-plugins
claude-plugins-official
anthropic-marketplace
anthropic-plugins
knowledge-work-plugins
life-sciences
```

Pick something specific to the user instead — e.g. `<username>-agent-skills` or `<org>-plugins`. This list can grow; if a chosen name gets rejected at publish/sync time for no obvious reason, treat "it's on the reserved list now" as the first hypothesis.

## A known bug worth designing around: shared-source skill filtering

If `marketplace.json` declares multiple plugin entries that all use `source: "./"` and rely on each entry's `skills` array to give each plugin a different subset of a shared `skills/` directory, that filtering currently does not work as documented — every installed plugin from a shared source ends up loading *all* skills under that source, not just its declared subset, even though each plugin's namespace looks correct. If distinct skill sets per plugin actually matter, give each plugin its own subdirectory as the `source` instead of trying to filter one shared directory — don't rely on the `skills` array to do that job today.

## Publishing your own marketplace (no approval needed for this part)

**1.** Create or update `marketplace.json` and `plugin.json` manually based on the schemas above.
*Agent scaffolding instructions:*
- Sanitize inputs: ensure valid email formats and enforce length limits (descriptions ≤ 1024 chars, no code injection).
- Verify the chosen marketplace `name` is not in the reserved list above.
- If the files already exist, intelligently merge the new plugin instead of overwriting.

**2. Validate and smoke-test locally:**
```bash
claude plugin validate .
claude --plugin-dir .
```
Confirm the skill(s) resolve under the expected `<plugin-name>:<skill-name>` namespace.

**3. Push — the user's own terminal, their own credentials:**
```bash
git add . && git commit -m "Add plugin marketplace" && git push
```

**4. Anyone (including the user, to test) adds and installs it with:**
```
/plugin marketplace add <owner>/<repo>
/plugin install <plugin-name>@<marketplace-name>
```
This alone is a complete, working, private-or-public distribution channel — no Anthropic review required. It's fine as the permanent home for an internal team, or as the source you point at when submitting to the wider catalogs below.

## Getting into the public community catalog

Submit via the form at `clau.de/plugin-directory-submission` (also reachable from claude.ai's plugin settings). What happens after submitting:
- Automated security scanning runs against the repo.
- On approval, the plugin is pinned to a specific commit SHA inside Anthropic's `claude-plugins-community` catalog; CI advances that pin automatically as new commits land on the source repo.
- The public catalog syncs nightly from the review pipeline — there's normally a lag between approval and the plugin actually appearing. Search the community catalog by name to confirm it's live rather than assuming approval = immediately visible.

## The official marketplace is separate and not something you apply your way into

`claude-plugins-official` is curated directly by Anthropic, at Anthropic's discretion. There's no formal application process, and getting approved into the community catalog does not lead to or guarantee inclusion here. Don't tell a user their plugin will "graduate" to official status — it isn't a pipeline stage, it's a distinct, separately-curated list.
