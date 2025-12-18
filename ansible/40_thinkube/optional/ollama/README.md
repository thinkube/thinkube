# Ollama - Fast LLM Inference Server

## Description

Ollama provides fast local LLM inference with GPU acceleration.
Achieves ~50 tok/s on DGX Spark vs ~2.3 tok/s with BitsAndBytes quantization.

## Requirements

- Harbor (for mirrored image)
- GPU node (nodeSelector configured in inventory)
- JuiceFS MLflow volume (for accessing fine-tuned GGUF models)

## Playbooks

| Playbook | Description |
|----------|-------------|
| `00_install.yaml` | Orchestrator - runs all installation playbooks |
| `10_deploy.yaml` | Main deployment (StatefulSet, Service, Ingress, PVCs) |
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

```
JuiceFS MLflow Volume (shared storage)
├── .staging/                    ← Fine-tuned GGUF models from notebooks
│   └── {model-name}/
│       └── unsloth.Q4_K_M.gguf
└── artifacts/                   ← MLflow registered models
    └── {experiment_id}/
        └── {run_id}/

JupyterHub Pod mount:  /home/thinkube/thinkube/mlflow
Ollama Pod mount:      /mlflow-models
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

## Installation

Ollama is installed via the thinkube-control UI as an optional component.

Manual installation (not recommended):
```bash
cd ~/thinkube
./scripts/tk_ansible ansible/40_thinkube/optional/ollama/00_install.yaml
```

## Uninstallation

Via thinkube-control UI, or manually:
```bash
cd ~/thinkube
./scripts/tk_ansible ansible/40_thinkube/optional/ollama/19_rollback.yaml
```
