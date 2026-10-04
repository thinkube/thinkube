# Git policy — work preservation (Thinkube platform default)

This workspace runs in a pod: uncommitted work is one rescheduling or
image rebuild away from loss, and the pushed remote is the only backup.

- When a change set is VERIFIED — tests pass, and where applicable it is
  deployed — commit it immediately without asking. Verified work must
  never sit uncommitted.
- Scope every commit: `git add` explicit paths only. NEVER
  `git add -A` / `git add .`.
- Push right after committing, without asking.
- Unverified or work-in-progress changes: do not commit; say what is
  pending instead.
- Destructive git operations (reset --hard, force-push, history
  rewrites) still require an explicit ask.
