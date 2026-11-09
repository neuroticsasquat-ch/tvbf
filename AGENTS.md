# AGENTS.md

The guide for agents working in this repo is [`.claude/CLAUDE.md`](.claude/CLAUDE.md). Read it
first. It covers the `tvbf` monorepo as a whole (layout, git rules, the Taskfile, specs and
Linear) and the backend at the root. Its load-bearing detail is split into
[`.claude/docs/`](.claude/docs/), and each of those files says when you must read it.

This file used to hold its own copy of that guide, which fell behind. Since NEU-2259 it only points
there, so the guide has one copy.

## Frontend

The SPA lives under `frontend/`. Its guide is [`.claude/docs/frontend.md`](.claude/docs/frontend.md).
Read it in full before the first edit under `frontend/`. It was the frontend repo's own
`.claude/CLAUDE.md` (and the `AGENTS.md` copied from it) before the two repos merged.

The shared vocabulary for both halves is [`CONTEXT.md`](CONTEXT.md); the frontend's terms are in
its *Brand* section. Specs for both halves are in [`docs/specs/`](docs/specs/).
