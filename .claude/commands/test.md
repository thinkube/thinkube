---
description: Run a component's 18_test.yaml validation playbook
---

Run the validation playbook for a thinkube component.

Usage: `/test <component-path>` — e.g. `/test core/keycloak` or `/test core/postgresql`

Steps:
1. Locate the test playbook at `ansible/40_thinkube/<component-path>/18_test.yaml`. If `$ARGUMENTS` is empty, list available test playbooks under `ansible/40_thinkube/` and ask which to run.
2. Execute with:
   ```
   ./scripts/tk_ansible ansible/40_thinkube/$ARGUMENTS/18_test.yaml
   ```
3. Report pass/fail and summarize any failed tasks.

Do NOT run test playbooks against template namespaces (gptoss*, tkt-*) — those are managed through the thinkube-control UI only.
