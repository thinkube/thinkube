# CI/CD policy — the pipeline is the check (Thinkube platform default)

This IDE is a development environment inside the cluster it deploys
to. The platform's pipeline builds and deploys every repository that
has one, on the real targets: both architectures, the cluster's
registry, identity and services; an app's pipeline also runs its tests.
A build or test run in the IDE checks a copy that differs from what
runs. So the IDE is never where a change is checked.

- To check a change: commit, push, and run the repository's own deploy.
  Then look at the deployed result, or read the build log.
- Do not repeat the pipeline's work in the IDE to check a change: no
  local builds or test runs, no local web server, no browser pointed at
  a local build, and no workarounds to make them run here.
- Tests are code: write them and keep them in the repository. Do not run
  them yourself — not in the IDE, not inside a pod — unless the person
  asks. A repository whose pipeline runs no tests, such as Thinkube
  Control, is checked by deploying it and using what was deployed.
- Each repository's AGENTS.md or CLAUDE.md names its deploy. For an
  app, the push to its Gitea repository is the deploy.
- An instruction file says what a deploy is meant to be, not what
  exists. Before a deploy or a redeploy, check that its target exists on
  this cluster: the app, its namespace, its repository. If it does not,
  stop and say so: a deploy of a missing app creates it.
- Allowed locally: reproducing a failed cluster build step when its log
  does not show the cause. Say so before running it.
- Work that no pipeline does is not a check, and this policy does not
  forbid it: building a package to publish it, writing a lock file,
  generating files the repository keeps. Do it in the IDE, directly. Do
  not move it into a pod or a pipeline to get around this policy.
