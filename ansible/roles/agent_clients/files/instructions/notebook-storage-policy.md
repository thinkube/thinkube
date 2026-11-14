# Notebook storage policy — where a notebook writes (Thinkube platform default)

A notebook server's pod mounts several folders. Some are kept, one is
deleted with the pod, and JupyterHub stops a server after 1 hour without
activity.

- Before choosing where a notebook writes, list the pod's mounts. Write
  only to a folder the platform configured for that kind of data.
- `/home/thinkube/thinkube/notebooks`, `datasets` and `models`: JuiceFS.
  Kept, and the same on every node. Models go under `models`.
- `/home/thinkube/thinkube/mlflow`: the MLflow artifacts. Written by the
  platform's mirror and registry, not by hand.
- `/home/thinkube/training`: the node's own disk, kept across sessions.
  Mounted only when the server starts on a node in training mode, which
  also unloads that node's LLM models. For large files used on one node.
- `/home/thinkube/scratch`: deleted when the pod stops. Never hold the
  only copy of a result there. When it is used to avoid network traffic,
  say before starting that the files are lost when the server stops, and
  move what must be kept to a kept folder in the same act.
