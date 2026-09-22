# Ollama - Fast LLM Inference Server

## Description

Ollama provides fast local LLM inference with GPU acceleration.
Achieves ~50 tok/s on DGX Spark vs ~2.3 tok/s with BitsAndBytes quantization.

## Installation

Ollama is an optional component. It is installed and removed from the
Optional Components page in thinkube-control, not on its own. The page runs
`00_install.yaml` to install, `18_test.yaml` to test and `19_rollback.yaml`
to remove it. It requires Harbor.

## Requirements

- Harbor (for mirrored image)
- GPU node. The LLM Gateway sets the nodeSelector and GPU requests on each pod when it creates it.
- JuiceFS MLflow volume (for accessing fine-tuned GGUF models). JupyterHub creates the shared `jupyterhub-mlflow-root` PV.

## Playbooks

| Playbook | Description |
|----------|-------------|
| `00_install.yaml` | Orchestrator - runs all installation playbooks |
| `10_deploy.yaml` | Main deployment: Deployment with `replicas: 0`, Service, HTTPRoute, PV and PVC `ollama-mlflow-pvc`. The LLM Gateway creates the pods at runtime. |
| `17_configure_discovery.yaml` | Service discovery ConfigMap (CRITICAL for env vars in JupyterHub) |
| `18_test.yaml` | Validation tests |
| `19_rollback.yaml` | Cleanup and uninstall |

## Environment Variables Provided

After installation, the following environment variables are injected into JupyterHub pods:

| Variable | Value | Description |
|----------|-------|-------------|
| `OLLAMA_URL` | `http://ollama.ollama.svc.cluster.local:11434` | Base Ollama API URL |
| `OLLAMA_API_URL` | `http://ollama.ollama.svc.cluster.local:11434/v1` | OpenAI-compatible API endpoint |

## Model Storage Architecture

Ollama uses a **single JuiceFS volume** for both MLflow model artifacts and its own
blob storage (`OLLAMA_MODELS=/mlflow-models/.ollama/models`). Because both paths are
on the same filesystem, `ollama create` hard-links GGUFs from MLflow instead of
copying them — zero model duplication.

```
JuiceFS MLflow Volume (single mount at /mlflow-models)
├── .ollama/models/              ← Ollama blob storage (hard-linked from artifacts)
│   ├── blobs/
│   └── manifests/
├── .staging/                    ← Fine-tuned GGUF models from notebooks
│   └── {model-name}/
│       └── unsloth.Q4_K_M.gguf
└── artifacts/                   ← MLflow registered models
    └── {experiment_id}/
        └── {run_id}/

JupyterHub Pod mount:  /home/thinkube/thinkube/mlflow
Ollama Pod mount:      /mlflow-models
Ollama blobs:          /mlflow-models/.ollama/models (same filesystem → hard links)
```

## Usage in Notebooks

### Loading a fine-tuned model:

```python
import requests

OLLAMA_BASE = "http://ollama.ollama.svc.cluster.local:11434"

# Import GGUF into Ollama
modelfile = """
FROM /mlflow-models/.staging/gpt-oss-catalan-math/unsloth.Q4_K_M.gguf
PARAMETER stop "<|end|>"
PARAMETER stop "<|endoftext|>"
"""

resp = requests.post(f"{OLLAMA_BASE}/api/create", json={
    "name": "gpt-oss-catalan-math",
    "modelfile": modelfile
}, stream=True)
```

### GPU Memory Management:

```python
# Unload model from GPU memory (keeps on disk)
requests.post(f"{OLLAMA_BASE}/api/generate", json={
    "model": "gpt-oss-catalan-math",
    "keep_alive": 0
})

# List loaded models
requests.get(f"{OLLAMA_BASE}/api/ps")
```
