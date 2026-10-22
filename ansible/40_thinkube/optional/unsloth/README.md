# Unsloth

Unsloth for fine-tuning in Thinkube Notebooks.

`00_install.yaml`:
- builds the custom venv `unsloth` from the `fine-tuning-unsloth` template, through Thinkube Control;
- copies the notebooks of [thinkube-unsloth](https://github.com/thinkube/thinkube-unsloth), at the cluster's branch, to `notebooks/unsloth/`;
- marks the component installed with the ConfigMap `unsloth` in the `unsloth` namespace.

The kernel `unsloth` appears at the next start of a notebook server.

`19_rollback.yaml` deletes the venv, `notebooks/unsloth/` and the namespace.
