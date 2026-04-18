# Quick Task: FluxQ Project Skill

- Quick ID: `260418-npm`
- Date: `2026-04-18`
- Description: Create an in-repo FluxQ project skill with a bilingual task-oriented workflow and quick reference.

## Scope

Create a repository-native FluxQ skill that:

- lives inside the repo and ships to GitHub with the CLI
- is task-oriented rather than a command encyclopedia
- is bilingual, with English discovery terms and Chinese guidance
- covers the full FluxQ control-plane loop:
  - intent ingress
  - revision trust and compare
  - doctor and benchmark gates
  - delivery bundles
  - IBM readiness boundaries

## Locked Decisions

- Skill type: project-local skill
- Primary mode: task-oriented
- Coverage: full lifecycle workflow
- Language: bilingual (`English + 中文`)
- Packaging: one canonical `.agents/skills/fluxq-cli/` skill plus a small reference file

## Guardrails

- Do not describe Phase 10+ remote submit as if it already exists.
- Keep `SKILL.md` focused on when to use FluxQ and which workflow to choose.
- Move dense command examples into `quick-reference.md` instead of bloating `SKILL.md`.
