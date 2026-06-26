# comsol-mcp-server-setup

Portable recipe for upgrading any host AI agent's `comsol-mcp-automation` skill so it can drive COMSOL Multiphysics end-to-end (geometry → physics → mesh → solve → results) through the open-source **wjc9011 COMSOL MCP server** (~80+ MCP tools).

## What this skill is

A meta-skill: it doesn't run COMSOL itself. It teaches an agent how to install the MCP server, register it in the host's MCP config, fix the local environment probe, and rewrite the existing skill's runtime-mode decision tree so the MCP server becomes Priority 1.

After applying this skill, the agent can build COMSOL models from natural-language prompts via tool calls instead of writing Java/MPh by hand.

## When the agent should run it

- The user already has a `comsol-mcp-automation` skill that only knows MPh / Java export / batch.
- COMSOL Multiphysics is installed (5.x or 6.x).
- The host agent supports stdio MCP servers and has a JSON config file for them (Claude Code's `~/.claude.json`, opencode's `opencode.json`, etc.).

## Files

- `SKILL.md` — full step-by-step procedure (Quick Start, Prerequisites, 6 steps, Rollback, Known pitfalls).
- `references/probe-patch.md` — exact code blocks to add/replace in the probe so it discovers COMSOL's bundled JRE and detects the MCP server registration.
- `references/skill-edits.md` — exact diffs to apply to the existing `comsol-mcp-automation/SKILL.md` and `references/runtime-modes.md`, plus the full text of the new `references/mcp-server.md` file.
- `references/tool-catalogue.md` — the 80+ MCP tools grouped by category, for the agent to reference when planning a build.

## Portability notes

- All paths in `SKILL.md` are placeholders (`<COMSOL_ROOT>`, `<target-dir>`, `<absolute path to comsol-mcp executable>`). The agent fills them in from the probe output.
- Linux/macOS work; the JRE path differs (`<root>/java/<arch>/jre`).
- The repo is ~491 MB — `git clone --depth 1 --single-branch --branch main` is mandatory, not optional.

## Upstream

- MCP server: <https://github.com/wjc9011/COMSOL_Multiphysics_MCP>
- Companion skills assumed to exist alongside: `comsol-mcp-automation`, `comsol-electrochem-fluid`.
