---
description: Syntax-check and lint Ansible playbooks
---

Validate Ansible playbooks for syntax and style issues.

Target: `$ARGUMENTS` (a playbook path or directory; defaults to `ansible/40_thinkube/` if empty).

Steps:
1. Run syntax check:
   ```
   ansible-playbook --syntax-check <target>
   ```
2. If `ansible-lint` is available, run it on the target and report findings. If not installed, skip and note that.
3. If `yamllint` is available, run it and report findings.
4. Summarize: number of files checked, errors vs warnings, and the most important issues to fix first.

Focus on actionable issues — ignore cosmetic warnings unless they indicate real problems.
