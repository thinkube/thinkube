# CI/CD policy — the pipeline is the check (Thinkube platform default)

This IDE is a development environment inside the cluster it deploys
to. The platform's pipeline builds, tests and deploys every repository
on the real targets: both architectures, the cluster's registry,
identity and services. A build or server in the IDE checks a copy that
differs from what runs, so it is never the check.

- Never build, serve or browser-test a Thinkube repository locally: no
  local npm installs or builds, no local web server, no browser pointed
  at a local build.
- To check a change: commit, push, and run the repository's own deploy.
  Then look at the deployed result, or read the build log.
- Each repository's AGENTS.md or CLAUDE.md names its deploy. For an
  app, the push to its Gitea repository is the deploy.
- Allowed locally: the tests a repository's AGENTS.md, CLAUDE.md or
  README asks for, and reproducing a failed cluster build step when its
  log does not show the cause. Say which of the two it is before running
  it.
