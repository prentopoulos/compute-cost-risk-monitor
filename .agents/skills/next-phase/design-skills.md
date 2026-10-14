# Design skills

Read this when a phase builds or changes something people look at: the Streamlit dashboard, a
public demo page, the walkthrough's screens or a chart. None of these skills is vendored into
the repo; each is installed once per PC (below).

## Context first

Before choosing a skill, read the audience in PROJECT.md §1, the `dashboard` spec, the theme in
`src/compute_cost_risk_monitor/.streamlit/config.toml`, and any `.impeccable/` folder or
DESIGN.md the project has. Pin the look the owner asked for; reviewers critique its execution
and do not redirect it.

The constitution outranks every design skill. A look borrowed from trading screens must not
make published list prices read as a market:

- no tickers, bid/ask, flashing price changes or "live" badges;
- every figure keeps its data label, group key and snapshot time;
- red and green mark a scenario's direction, never a price move.

## Which skill

| Skill | Use it for | Limits here |
|---|---|---|
| impeccable (`impeccable:impeccable`, plugin) | Shaping, critiquing, auditing and polishing product UI, dashboards included. It owns the critique method. | None beyond the constitution |
| ui-ux-pro-max (`ui-ux-pro-max:ui-ux-pro-max`, plugin) | Lookups: palettes, font pairings, chart types, UX and accessibility guidelines | It has no Streamlit stack; use its stack-neutral advice |
| dataviz (built in) | Charts, stat tiles and palette validation, before writing chart code | None |
| tasteskill (`design-taste-frontend`, user skill) | Public-facing pages: a demo landing page or a methodology page | Not for the dashboard: the skill says it is not for dashboards or app screens |
| 21st.dev (`21st` MCP plugin, or the `21st-*` CLI skills) | Inspiration and React/Tailwind sketches | The app is Streamlit, so a sketch is a spec to rebuild, never pasted code. AI generation uses 21st credits; on a paid plan that is paid quota, so the ⛔ spend gate applies until the owner approves it. Prompts carry synthetic figures only, never live Azure numbers (PROJECT.md §6: no redistribution) |
| design-eval (user skill) | A scored review (impeccable plus taste) before a UI PR is marked ready | For the dashboard, run it without the taste reviewer and say so |
| Figma skills (plugin) | Architecture diagrams and any mock | Load them before any Figma tool |

A skill recommendation does not justify adding its framework to the application. Changing the
dashboard's stack is an owner decision recorded in PROJECT.md §4.

## Install on a new PC

- impeccable: `/plugin marketplace add pbakaus/impeccable`, then
  `/plugin install impeccable@impeccable`.
- ui-ux-pro-max: `/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill`, then
  `/plugin install ui-ux-pro-max@ui-ux-pro-max-skill`.
- tasteskill (MIT): copy `skills/taste-skill/` and the root `LICENSE` from
  [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) to
  `~/.claude/skills/design-taste-frontend/`. Installed on 2026-10-13 from commit `a60a36d`
  (SKILL.md SHA-256 `ee847084…3043`). Its scripts need Node 22+ and Chrome or Edge, and fetch
  pictures from open collections.
- 21st.dev MCP (ISC): `/plugin marketplace add 21st-dev/magic-mcp`, then
  `/plugin install 21st@21st-dev`. It connects to `https://21st.dev/api/mcp` with the key in the
  `API_KEY_21ST` environment variable, from https://21st.dev/settings/api-keys. Set it in the
  user environment, never in this repo. The CLI skills come from
  `npx @21st-dev/cli install-skill`. Installed on this PC on 2026-10-13, with the key in the user
  environment. The account is free tier (`get_usage`): AI generation off, 0 credits, free
  searches, and 2 free component code copies a day.
