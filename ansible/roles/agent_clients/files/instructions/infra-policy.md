# Infrastructure policy — no pod-only mutations (Thinkube platform default)

- Any system-level change made to the pod (packages, config, tools,
  links) is applied to its persistent home IN THE SAME ACT: the
  container image for OS packages, the deploy playbook for user-level
  tools and configuration.
- Commit and push that persistent change immediately.
- The pod is a cache, never a source of truth.
