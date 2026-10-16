# Thinkube developer add-on

This cluster is used to develop Thinkube itself. `tk_clone_dev` installed
this file; the platform's base instructions (AGENTS.md) still apply, and a
user's cluster does not have this file.

## What this cluster is

- The platform repositories are checked out under `~/thinkube-platform/`
  (`core/`, `docs/`, `fixes/`, `templates/`, `extensions/`, ...), on the
  branch `tk_clone_dev` cloned, which `THINKUBE_BRANCH` names.
- A playbook runs from the `thinkube` checkout as it is:
  `cd ~/thinkube-platform/core/thinkube && ./scripts/tk_ansible <playbook>`.
  A Thinkube Control deploy (`12_deploy_dev.yaml`) copies the repository
  from GitHub at the branch the cluster follows, so a change to Thinkube
  Control is pushed before it is deployed.
- Apps deployed from templates (`~/apps/<app>`) are not part of the
  platform; a push to their Gitea repository is their deploy.
- Components built from a template (`~/components/<name>`: vLLM,
  TensorRT-LLM, text-embeddings) are deployed copies. Their source is the
  template repository named in `thinkube-metadata/optional_components.json`
  (`~/thinkube-platform/templates/tkt-*`). Change the template, push it to
  GitHub, then redeploy the component from it (`redeploy_template`); this
  cluster renders a platform template from the head of its branch. Never
  commit a change to the copy in `~/components/` or its Gitea repository.

## How a platform change travels

1. Commit on `main` of the component's repository and push.
2. Deploy it here and look at it running. Thinkube Control:
   `12_deploy_dev.yaml`; other components: their own playbook. A change
   that was not seen running is not verified.

A development change is finished there. Releasing is a separate process,
started on its own when someone asks for a release: it cherry-picks to
`release-<MAJOR.MINOR>`, raises versions, tags, and adds the fixes entry,
as `thinkube-release/VERSIONING.md` and the README of `thinkube-fixes`
describe. A development change does none of that and does not raise a
`VERSION`; read those two files when a release is asked for.

## Rules learned the hard way

- A version tag raises only the last number. `MAJOR.MINOR` is the
  platform's release (0.1 today), in every repository: the platform's,
  templates, and the user's own. A repository's first tag is `v0.1.0`, the
  next `v0.1.1`, then `v0.1.2`; never `v0.2.0` while the platform is 0.1.
  `metadata.version` in `thinkube.yaml` says the same number as the tag.
- `release-*` is what every new install reads. Never push to it; never
  tag a commit as a fix before it was seen running here.
- `thinkube-control/12_deploy.yaml` drops the component's databases. It
  runs on a first install or after `19_rollback.yaml`, never to update.
  A fix of thinkube-control names `12_deploy_dev.yaml`.
- An instruction file says what a deploy is meant to be, not what exists.
  Check the target exists before a deploy or redeploy an instruction file
  describes; a deploy of a missing app creates an app nobody asked for.
  A new app the person asked for is deployed without asking.
- The public documentation, https://thinkube.org, is GitHub Pages,
  published only by running `pages.yml` of `thinkube.org` by hand from
  `main`: `gh workflow run pages.yml -R thinkube/thinkube.org --ref main`.
  The cluster application `docs` exists only where someone deployed it;
  `search_thinkube_docs` answers `docs_not_deployed` where it does not.
- A field added to `thinkube.yaml` goes into the existing schema and
  reference page in `thinkube.org`; the specification number (v1.0) is
  not bumped for a small addition.
- `thinkube-release/DEFECTS-FOUND.md` records defects that are open. A
  fixed defect is recorded by its commit and its fix entry, not there.
- A platform change is built and tested by the pipeline; the tests a
  repository's CLAUDE.md names run where it says (for thinkube-control
  and thinkube.org: in thinkube-control's backend pod, which mounts the
  home and has the dependencies).
- A model mirror on a fresh install fails at the MLflow step with
  `unknown_user` until the user has opened MLflow once. This is accepted
  and has no fix; Thinkube Control's Models page tells the user and links
  to MLflow. Sign in once (Playwright, as `thinkube`) and submit the
  mirror again. Do not report it or propose a fix.
- Memory of an agent is not a record. What must be kept goes into a
  repository: a rule here, a note in the project's own repository, or
  VERSIONING.md.
- This cluster has one user. A password, token or key that appears in a
  command's output, a log or this conversation is not a problem to report
  and needs no rotation: whoever can read the log can read `~/.env`. Say
  something only when a secret has left the cluster: committed to a
  repository that is pushed, or sent to an outside service.
