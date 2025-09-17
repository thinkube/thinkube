# JupyterHub Implementation Plan - GPU Flexibility & Custom Images

## Overview

This plan focuses exclusively on implementing JupyterHub enhancements to enable GPU flexibility and custom AI/ML images. This is the most complex component with the least available examples.

## Core Challenge

Current JupyterHub is locked to control plane node due to shared-code mounting. We need to:
1. Enable notebooks to run on ANY GPU node
2. Create custom images for different AI workloads (fine-tuning, agents, etc.)
3. Allow dynamic image selection
4. Maintain notebook persistence across nodes

## Phase 1: Storage Architecture Change (Days 1-2)

### 1.1 Create SeaweedFS Volume for Notebooks

```bash
# First, verify SeaweedFS is working
kubectl get pods -n seaweedfs
kubectl get pv | grep seaweedfs
```

```yaml
# File: ansible/40_thinkube/optional/jupyterhub/manifests/01-seaweedfs-volumes.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: jupyter-notebooks-pv
  labels:
    app: jupyterhub
    type: notebooks
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteMany  # Critical - allows access from multiple nodes
  persistentVolumeReclaimPolicy: Retain
  storageClassName: seaweedfs-storage
  csi:
    driver: seaweedfs-csi
    volumeHandle: jupyter-notebooks
    fsType: ext4
    volumeAttributes:
      collection: "jupyter"
      replication: "001"  # Single replica for home use
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: jupyter-notebooks-pvc
  namespace: jupyterhub
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: seaweedfs-storage
  resources:
    requests:
      storage: 100Gi
  selector:
    matchLabels:
      app: jupyterhub
      type: notebooks
```

### 1.2 Test SeaweedFS Access

```yaml
# File: ansible/40_thinkube/optional/jupyterhub/18-test-seaweedfs.yaml
---
- name: Test SeaweedFS notebook storage
  hosts: microk8s_control_plane
  gather_facts: true

  tasks:
    - name: Create test pod on different nodes
      kubernetes.core.k8s:
        state: present
        definition:
          apiVersion: v1
          kind: Pod
          metadata:
            name: "seaweedfs-test-{{ item }}"
            namespace: jupyterhub
          spec:
            nodeSelector:
              kubernetes.io/hostname: "{{ item }}"
            containers:
            - name: test
              image: busybox
              command: ['sh', '-c', 'echo "Test from {{ item }}" > /notebooks/test-{{ item }}.txt && sleep 3600']
              volumeMounts:
              - name: notebooks
                mountPath: /notebooks
            volumes:
            - name: notebooks
              persistentVolumeClaim:
                claimName: jupyter-notebooks-pvc
      loop: "{{ groups['microk8s'] }}"

    - name: Verify files are accessible from all nodes
      kubernetes.core.k8s_exec:
        namespace: jupyterhub
        pod: "seaweedfs-test-{{ item }}"
        command: ls -la /notebooks/
      loop: "{{ groups['microk8s'] }}"
      register: file_list

    - name: Display results
      debug:
        msg: "Files on {{ item.item }}: {{ item.stdout }}"
      loop: "{{ file_list.results }}"
```

## Phase 2: JupyterHub Configuration Update (Days 3-4)

### 2.1 Update Helm Values for Storage

```yaml
# File: ansible/40_thinkube/optional/jupyterhub/templates/jupyterhub-values.yaml.j2
hub:
  config:
    JupyterHub:
      # Single-user optimization
      authenticator_class: nullauthenticator.NullAuthenticator
      admin_users:
        - {{ admin_username }}

singleuser:
  # Remove old hostPath mounts
  storage:
    type: none  # We'll manually configure volumes

  extraVolumes:
    # SeaweedFS for persistent notebooks
    - name: notebooks-persistent
      persistentVolumeClaim:
        claimName: jupyter-notebooks-pvc

    # Local scratch for fast I/O (per-pod temporary)
    - name: scratch
      emptyDir:
        sizeLimit: 50Gi

    # Optional: Read-only reference to shared-code (only works on control plane)
    - name: shared-code-ref
      hostPath:
        path: {{ code_source_path }}
        type: DirectoryOrCreate

  extraVolumeMounts:
    # Primary notebook storage (SeaweedFS)
    - name: notebooks-persistent
      mountPath: /home/jovyan/notebooks

    # Fast local scratch space
    - name: scratch
      mountPath: /home/jovyan/scratch

    # Reference mount (will fail gracefully on non-control nodes)
    - name: shared-code-ref
      mountPath: /home/jovyan/shared-code-reference
      readOnly: true
      mountPropagation: HostToContainer

  # Remove all node restrictions
  nodeSelector: {}
  extraNodeAffinity: {}

  # Enable GPU support by default
  extraEnv:
    - name: NVIDIA_VISIBLE_DEVICES
      value: "all"
    - name: NVIDIA_DRIVER_CAPABILITIES
      value: "compute,utility"
```

### 2.2 Dynamic Profile Generation

```yaml
# Continuation of jupyterhub-values.yaml.j2
hub:
  extraConfig:
    01-profile-generator: |
      import subprocess
      import json
      import os

      def get_gpu_nodes():
          """Get list of nodes with GPUs"""
          try:
              result = subprocess.run(
                  ['kubectl', 'get', 'nodes', '-l', 'nvidia.com/gpu=true', '-o', 'json'],
                  capture_output=True, text=True, timeout=5
              )
              if result.returncode == 0:
                  nodes_data = json.loads(result.stdout)
                  gpu_nodes = []
                  for node in nodes_data.get('items', []):
                      name = node['metadata']['name']
                      gpu_count = node['status'].get('capacity', {}).get('nvidia.com/gpu', '0')
                      gpu_nodes.append({'name': name, 'gpus': gpu_count})
                  return gpu_nodes
          except Exception as e:
              print(f"Error getting GPU nodes: {e}")
          return []

      def get_custom_images():
          """Get available custom images from Harbor"""
          # This would query Harbor API or thinkube-control
          # For now, return static list
          return [
              {'name': 'jupyter-ml-cpu', 'tag': 'latest', 'gpu': False},
              {'name': 'jupyter-ml-gpu', 'tag': 'latest', 'gpu': True},
              {'name': 'jupyter-fine-tuning', 'tag': 'latest', 'gpu': True},
              {'name': 'jupyter-agent-dev', 'tag': 'latest', 'gpu': False}
          ]

      # Generate profiles dynamically
      c.KubeSpawner.profile_list = []

      # CPU profiles (can run anywhere)
      c.KubeSpawner.profile_list.append({
          'display_name': '📚 Standard Environment (CPU)',
          'description': 'JupyterLab with standard data science packages',
          'default': True,
          'kubespawner_override': {
              'image': '{{ harbor_registry }}/library/jupyter-ml-cpu:latest',
              'cpu_limit': 4,
              'cpu_guarantee': 1,
              'mem_limit': '8G',
              'mem_guarantee': '2G'
          }
      })

      # GPU auto-select profile
      c.KubeSpawner.profile_list.append({
          'display_name': '🚀 GPU Environment (Auto-select)',
          'description': 'Automatically finds available GPU',
          'kubespawner_override': {
              'image': '{{ harbor_registry }}/library/jupyter-ml-gpu:latest',
              'node_selector': {'nvidia.com/gpu': 'true'},
              'extra_resource_limits': {'nvidia.com/gpu': '1'},
              'extra_resource_guarantees': {'nvidia.com/gpu': '1'},
              'cpu_limit': 8,
              'mem_limit': '16G'
          }
      })

      # Fine-tuning profile
      c.KubeSpawner.profile_list.append({
          'display_name': '🔧 Fine-tuning (Unsloth + QLoRA)',
          'description': 'Optimized for LLM fine-tuning with 4-bit quantization',
          'kubespawner_override': {
              'image': '{{ harbor_registry }}/library/jupyter-fine-tuning:latest',
              'node_selector': {'nvidia.com/gpu': 'true'},
              'extra_resource_limits': {'nvidia.com/gpu': '1'},
              'extra_resource_guarantees': {'nvidia.com/gpu': '1'},
              'cpu_limit': 8,
              'mem_limit': '32G',
              'mem_guarantee': '8G'
          }
      })

      # Agent development profile
      c.KubeSpawner.profile_list.append({
          'display_name': '🤖 Agent Development (LangChain)',
          'description': 'LangChain, CrewAI, and agent tools',
          'kubespawner_override': {
              'image': '{{ harbor_registry }}/library/jupyter-agent-dev:latest',
              'cpu_limit': 4,
              'mem_limit': '8G'
          }
      })

      # Add specific GPU node profiles
      gpu_nodes = get_gpu_nodes()
      for node in gpu_nodes:
          c.KubeSpawner.profile_list.append({
              'display_name': f"💻 GPU on {node['name']} ({node['gpus']} GPUs)",
              'description': f"Run specifically on {node['name']}",
              'kubespawner_override': {
                  'image': '{{ harbor_registry }}/library/jupyter-ml-gpu:latest',
                  'node_selector': {'kubernetes.io/hostname': node['name']},
                  'extra_resource_limits': {'nvidia.com/gpu': '1'},
                  'cpu_limit': 8,
                  'mem_limit': '16G'
              }
          })
```

## Phase 3: Custom Image Creation (Days 5-7)

### 3.1 Base CPU Image

```dockerfile
# File: ansible/40_thinkube/core/harbor/base-images/jupyter-ml-cpu.Dockerfile.j2
FROM {{ harbor_registry }}/library/python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install JupyterLab and extensions
RUN pip install --no-cache-dir \
    jupyterlab==4.0.9 \
    ipywidgets==8.1.1 \
    jupyterlab-git==0.50.0 \
    jupyterlab-lsp==5.0.1 \
    python-lsp-server[all]==1.9.0

# Install data science packages
RUN pip install --no-cache-dir \
    numpy==1.26.2 \
    pandas==2.1.4 \
    matplotlib==3.8.2 \
    seaborn==0.13.0 \
    scikit-learn==1.3.2 \
    plotly==5.18.0

# Install ML/AI packages
RUN pip install --no-cache-dir \
    transformers==4.36.2 \
    datasets==2.16.1 \
    tokenizers==0.15.0 \
    sentence-transformers==2.2.2

# Install utility packages
RUN pip install --no-cache-dir \
    python-dotenv==1.0.0 \
    requests==2.31.0 \
    boto3==1.34.0 \
    mlflow==2.9.2 \
    litellm==1.0.0

# Create jovyan user (JupyterHub convention)
RUN useradd -m -s /bin/bash -u 1000 jovyan

# Setup Jupyter configuration
USER jovyan
WORKDIR /home/jovyan

# Create directory structure
RUN mkdir -p /home/jovyan/notebooks \
    && mkdir -p /home/jovyan/scratch \
    && mkdir -p /home/jovyan/.jupyter

EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser"]
```

### 3.2 GPU-Enabled Base Image

```dockerfile
# File: ansible/40_thinkube/core/harbor/base-images/jupyter-ml-gpu.Dockerfile.j2
FROM {{ harbor_registry }}/library/cuda:12.6.0-runtime-ubuntu22.04

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set python3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install JupyterLab
RUN pip install --no-cache-dir --break-system-packages \
    jupyterlab==4.0.9 \
    ipywidgets==8.1.1 \
    jupyterlab-nvdashboard==0.9.0

# Install PyTorch with CUDA support
RUN pip install --no-cache-dir --break-system-packages \
    torch==2.1.2 \
    torchvision==0.16.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cu121

# Install ML packages
RUN pip install --no-cache-dir --break-system-packages \
    transformers==4.36.2 \
    accelerate==0.25.0 \
    datasets==2.16.1 \
    bitsandbytes==0.41.3 \
    scipy==1.11.4 \
    sentencepiece==0.1.99

# Install monitoring and utils
RUN pip install --no-cache-dir --break-system-packages \
    mlflow==2.9.2 \
    tensorboard==2.15.1 \
    wandb==0.16.2 \
    nvitop==1.3.2 \
    litellm==1.0.0

# Create jovyan user
RUN useradd -m -s /bin/bash -u 1000 jovyan

USER jovyan
WORKDIR /home/jovyan

# Verify GPU access
RUN python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser"]
```

### 3.3 Fine-tuning Specialized Image

```dockerfile
# File: ansible/40_thinkube/core/harbor/base-images/jupyter-fine-tuning.Dockerfile.j2
FROM {{ harbor_registry }}/library/jupyter-ml-gpu:latest

USER root

# Install Unsloth and dependencies
RUN pip install --no-cache-dir --break-system-packages \
    "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" \
    trl==0.7.7 \
    peft==0.7.1 \
    loralib==0.1.2 \
    einops==0.7.0 \
    xformers==0.0.23 \
    ninja==1.11.1.1

# Install additional fine-tuning tools
RUN pip install --no-cache-dir --break-system-packages \
    deepspeed==0.12.6 \
    flash-attn==2.5.0 \
    triton==2.1.0

# Copy example notebooks
COPY --chown=jovyan:jovyan notebooks/fine-tuning /home/jovyan/examples/fine-tuning

USER jovyan

# Create fine-tuning specific directories
RUN mkdir -p /home/jovyan/notebooks/fine-tuning \
    && mkdir -p /home/jovyan/notebooks/models \
    && mkdir -p /home/jovyan/notebooks/datasets
```

### 3.4 Agent Development Image

```dockerfile
# File: ansible/40_thinkube/core/harbor/base-images/jupyter-agent-dev.Dockerfile.j2
FROM {{ harbor_registry }}/library/jupyter-ml-cpu:latest

USER root

# Install agent frameworks
RUN pip install --no-cache-dir \
    langchain==0.1.0 \
    langchain-community==0.1.0 \
    langchain-openai==0.0.5 \
    langgraph==0.0.20 \
    langserve==0.0.41

# Install multi-agent frameworks
RUN pip install --no-cache-dir \
    crewai==0.1.0 \
    autogen==0.2.0

# Install vector stores and tools
RUN pip install --no-cache-dir \
    chromadb==0.4.22 \
    qdrant-client==1.7.0 \
    faiss-cpu==1.7.4 \
    semantic-router==0.0.20

# Install additional tools
RUN pip install --no-cache-dir \
    duckduckgo-search==4.1.0 \
    wikipedia-api==0.6.0 \
    arxiv==2.1.0 \
    tavily-python==0.3.0

# Copy example notebooks
COPY --chown=jovyan:jovyan notebooks/agents /home/jovyan/examples/agents

USER jovyan

# Create agent development directories
RUN mkdir -p /home/jovyan/notebooks/agents \
    && mkdir -p /home/jovyan/notebooks/tools \
    && mkdir -p /home/jovyan/notebooks/prompts
```

## Phase 4: Image Build Pipeline (Days 8-9)

### 4.1 Build Script

```yaml
# File: ansible/40_thinkube/optional/jupyterhub/10-build-images.yaml
---
- name: Build and Push JupyterHub Custom Images
  hosts: microk8s_control_plane
  gather_facts: true

  vars:
    images_to_build:
      - name: jupyter-ml-cpu
        dockerfile: jupyter-ml-cpu.Dockerfile.j2
        context: ./base-images
        gpu_required: false
      - name: jupyter-ml-gpu
        dockerfile: jupyter-ml-gpu.Dockerfile.j2
        context: ./base-images
        gpu_required: true
      - name: jupyter-fine-tuning
        dockerfile: jupyter-fine-tuning.Dockerfile.j2
        context: ./base-images
        gpu_required: true
      - name: jupyter-agent-dev
        dockerfile: jupyter-agent-dev.Dockerfile.j2
        context: ./base-images
        gpu_required: false

  tasks:
    - name: Create build directory
      file:
        path: /tmp/jupyter-builds
        state: directory

    - name: Template Dockerfiles
      template:
        src: "../../core/harbor/base-images/{{ item.dockerfile }}"
        dest: "/tmp/jupyter-builds/{{ item.name }}.Dockerfile"
      loop: "{{ images_to_build }}"

    - name: Copy notebook examples
      copy:
        src: "notebooks/"
        dest: "/tmp/jupyter-builds/notebooks/"

    - name: Build images with Podman
      shell: |
        cd /tmp/jupyter-builds
        podman build \
          -f {{ item.name }}.Dockerfile \
          -t {{ harbor_registry }}/library/{{ item.name }}:latest \
          .
      loop: "{{ images_to_build }}"
      register: build_results

    - name: Login to Harbor
      shell: |
        echo "$HARBOR_ROBOT_TOKEN" | podman login \
          --username {{ harbor_robot_user }} \
          --password-stdin \
          {{ harbor_registry }}

    - name: Push images to Harbor
      shell: |
        podman push {{ harbor_registry }}/library/{{ item.name }}:latest
      loop: "{{ images_to_build }}"

    - name: Tag images in Harbor metadata
      uri:
        url: "https://{{ harbor_registry }}/api/v2.0/projects/library/repositories/{{ item.name }}/artifacts/latest/labels"
        method: POST
        headers:
          Authorization: "Basic {{ (harbor_robot_user + ':' + harbor_robot_token) | b64encode }}"
        body_format: json
        body:
          labels:
            - jupyter_compatible: true
            - gpu_required: "{{ item.gpu_required }}"
      loop: "{{ images_to_build }}"
```

### 4.2 Example Notebooks

```python
# File: notebooks/fine-tuning/01-unsloth-quickstart.ipynb
"""
Quick Start Guide for Fine-tuning with Unsloth
"""

# Cell 1: Setup
import os
from unsloth import FastLanguageModel
import torch

# Verify GPU
print(f"GPU Available: {torch.cuda.is_available()}")
print(f"GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

# Cell 2: Load Model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/llama-3-8b-bnb-4bit",
    max_seq_length=2048,
    dtype=None,
    load_in_4bit=True,
)

print(f"Model loaded successfully!")
print(f"Model size: {model.get_memory_footprint() / 1e9:.2f} GB")

# Cell 3: Prepare for Training
model = FastLanguageModel.get_peft_model(
    model,
    r=16,  # LoRA rank
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                   "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing=True,
    random_state=3407,
)

# Cell 4: Load Dataset
from datasets import load_dataset

dataset = load_dataset("yahma/alpaca-cleaned", split="train[:1000]")
print(f"Dataset loaded: {len(dataset)} examples")

# Cell 5: Training Setup
from transformers import TrainingArguments
from trl import SFTTrainer

training_args = TrainingArguments(
    output_dir="/home/jovyan/scratch/outputs",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    warmup_steps=10,
    max_steps=100,
    logging_steps=10,
    save_steps=50,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    optim="adamw_8bit",
    seed=3407,
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=2048,
    args=training_args,
)

# Cell 6: Train
trainer.train()

# Cell 7: Save Model
model.save_pretrained("/home/jovyan/notebooks/models/llama3-fine-tuned")
tokenizer.save_pretrained("/home/jovyan/notebooks/models/llama3-fine-tuned")
print("Model saved to notebooks/models/llama3-fine-tuned")
```

## Phase 5: Deployment and Testing (Days 10-12)

### 5.1 Deploy Updated JupyterHub

```yaml
# File: ansible/40_thinkube/optional/jupyterhub/12-deploy-enhanced.yaml
---
- name: Deploy Enhanced JupyterHub with GPU Flexibility
  hosts: microk8s_control_plane
  gather_facts: true

  tasks:
    - name: Apply SeaweedFS volumes
      kubernetes.core.k8s:
        state: present
        src: manifests/01-seaweedfs-volumes.yaml

    - name: Update Helm values
      template:
        src: templates/jupyterhub-values.yaml.j2
        dest: /tmp/jupyterhub-values.yaml

    - name: Upgrade JupyterHub deployment
      kubernetes.core.helm:
        name: jupyterhub
        namespace: jupyterhub
        chart_ref: jupyterhub/jupyterhub
        values_files:
          - /tmp/jupyterhub-values.yaml
        state: present
        update_repo_cache: true
```

### 5.2 Testing Playbook

```yaml
# File: ansible/40_thinkube/optional/jupyterhub/18-test-enhanced.yaml
---
- name: Test Enhanced JupyterHub
  hosts: microk8s_control_plane
  gather_facts: true

  tasks:
    - name: Test notebook persistence
      block:
        - name: Create test notebook on node1
          kubernetes.core.k8s_exec:
            namespace: jupyterhub
            pod: "{{ jupyterhub_pod_node1 }}"
            command: |
              python -c "
              import json
              with open('/home/jovyan/notebooks/test.ipynb', 'w') as f:
                  json.dump({'cells': [], 'metadata': {}, 'nbformat': 4}, f)
              "

        - name: Verify notebook exists on node2
          kubernetes.core.k8s_exec:
            namespace: jupyterhub
            pod: "{{ jupyterhub_pod_node2 }}"
            command: ls -la /home/jovyan/notebooks/test.ipynb

    - name: Test GPU access
      kubernetes.core.k8s_exec:
        namespace: jupyterhub
        pod: "{{ jupyterhub_gpu_pod }}"
        command: python -c "import torch; print(torch.cuda.is_available())"
      register: gpu_test

    - name: Verify GPU is available
      assert:
        that:
          - "'True' in gpu_test.stdout"
        fail_msg: "GPU not available in JupyterHub pod"

    - name: Test custom images
      kubernetes.core.k8s:
        state: present
        definition:
          apiVersion: v1
          kind: Pod
          metadata:
            name: "test-{{ item }}"
            namespace: jupyterhub
          spec:
            containers:
            - name: test
              image: "{{ harbor_registry }}/library/{{ item }}:latest"
              command: ['python', '-c', 'import jupyterlab; print(jupyterlab.__version__)']
      loop:
        - jupyter-ml-cpu
        - jupyter-ml-gpu
        - jupyter-fine-tuning
        - jupyter-agent-dev
```

## Troubleshooting Guide

### Common Issues and Solutions

1. **SeaweedFS Mount Fails**
   ```bash
   # Check CSI driver
   kubectl get pods -n seaweedfs-csi
   kubectl logs -n seaweedfs-csi deployment/seaweedfs-csi-driver

   # Verify PVC binding
   kubectl get pvc -n jupyterhub
   kubectl describe pvc jupyter-notebooks-pvc -n jupyterhub
   ```

2. **GPU Not Available in Pod**
   ```bash
   # Check GPU operator
   kubectl get pods -n gpu-operator

   # Verify node labels
   kubectl get nodes --show-labels | grep nvidia

   # Check runtime configuration
   kubectl exec -n jupyterhub <pod> -- nvidia-smi
   ```

3. **Notebooks Don't Persist**
   ```bash
   # Check mount inside pod
   kubectl exec -n jupyterhub <pod> -- df -h /home/jovyan/notebooks

   # Verify SeaweedFS volume
   kubectl exec -n seaweedfs <master-pod> -- weed volume list
   ```

4. **Image Pull Errors**
   ```bash
   # Check Harbor connectivity
   curl -k https://<harbor-registry>/api/v2.0/health

   # Verify image exists
   podman search <harbor-registry>/library/jupyter
   ```

## Success Verification

### Checklist
- [ ] JupyterHub pods can start on any node
- [ ] Notebooks persist when switching nodes
- [ ] GPU is accessible in GPU-enabled images
- [ ] All custom images are available in profile list
- [ ] SeaweedFS performance is acceptable (< 2s save time)
- [ ] Scratch space is available and fast
- [ ] Example notebooks work correctly

### Performance Metrics
- Notebook save time: < 2 seconds
- Pod startup time: < 30 seconds
- GPU allocation: Successful
- Image pull time: < 2 minutes

## Next Steps After Implementation

1. Create more specialized images:
   - `jupyter-rapids` for GPU-accelerated data science
   - `jupyter-jax` for JAX/Flax workflows
   - `jupyter-rust` for Rust kernel support

2. Add notebook templates:
   - Fine-tuning workflows
   - Agent development patterns
   - Data pipeline examples

3. Integrate with thinkube-control:
   - Image selection UI
   - Resource monitoring
   - Notebook backup automation

4. Documentation:
   - User guide for GPU selection
   - Fine-tuning tutorials
   - Agent development guide