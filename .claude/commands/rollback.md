---
description: Run a component's 19_rollback.yaml for a clean reset
---

Cleanly tear down a thinkube component so it can be redeployed from scratch.

Usage: `/rollback <component-path>` — e.g. `/rollback core/keycloak`

Steps:
1. Confirm with the user before proceeding — rollback is destructive (drops databases, terminates connections, deletes namespaces).
2. Locate `ansible/40_thinkube/<component-path>/19_rollback.yaml`. If missing, tell the user and stop.
3. Run:
   ```
   ./scripts/tk_ansible ansible/40_thinkube/$ARGUMENTS/19_rollback.yaml
   ```
4. Report the result. Do NOT auto-run `10_deploy.yaml` afterwards — let the user decide.

Never run rollback against template namespaces (gptoss*, tkt-*, template-*).
