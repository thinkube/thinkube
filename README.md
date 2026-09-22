# Thinkube

Your own platform for the entire AI lifecycle.

Thinkube is a platform for one developer, on machines you own, that takes an
AI project from an idea to a running product: a model served on your GPU, an
app that calls it, notebooks to fine-tune it, and a report on every change.
You operate it by talking to Claude Code.

The base is [Thinkube Kubernetes](https://thinkube.github.io/thinkube.org/thinkube-docs/kubernetes/index.html):
unmodified upstream Kubernetes on your machines, installed with kubeadm, with
identity, storage, registry, database, certificates and GPUs installed and
connected, driven from Claude Code.

## Documentation

- [What Thinkube is](https://thinkube.github.io/thinkube.org/thinkube-docs/start-here/what-is-thinkube.html)
- [Install Thinkube](https://thinkube.github.io/thinkube.org/thinkube-docs/install/overview.html)
- [Playbooks](https://thinkube.github.io/thinkube.org/thinkube-docs/index.html#playbooks)
- [Components catalog](https://thinkube.github.io/thinkube.org/thinkube-docs/reference/components.html)

## This repository

The Ansible playbooks that install Thinkube. The
[Thinkube installer](https://github.com/thinkube/thinkube-installer) clones
this repository and runs them; they are not run by hand. There is one folder
per component in [`ansible/40_thinkube/`](ansible/40_thinkube/README.md).

## Commitments

1. Code released under Apache-2.0 will not be relicensed.
2. No capability will be removed from the open platform in order to sell it
   back.

## Contributing and support

Contributions are welcome. Support is best effort.

## License

Apache License 2.0. See [LICENSE](LICENSE).

Copyright Alejandro Martínez Corriá and the Thinkube contributors.
