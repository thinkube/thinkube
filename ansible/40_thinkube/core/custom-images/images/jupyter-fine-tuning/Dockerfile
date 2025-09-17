# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

ARG HARBOR_REGISTRY
FROM ${HARBOR_REGISTRY}/library/jupyter-ml-gpu:latest

USER root

# Install additional system dependencies for Unsloth
RUN apt-get update && apt-get install -y \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt /tmp/finetuning-requirements.txt

# Install fine-tuning packages from requirements
RUN pip install --no-cache-dir --break-system-packages -r /tmp/finetuning-requirements.txt

# Install Unsloth from git (not in requirements due to git dependency)
RUN pip install --no-cache-dir --break-system-packages \
    "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

# Copy example notebooks (will be added during build)
COPY --chown=jovyan:jovyan notebooks/fine-tuning /home/jovyan/examples/fine-tuning || true

USER jovyan

# Create fine-tuning specific directories
RUN mkdir -p /home/jovyan/notebooks/fine-tuning \
    && mkdir -p /home/jovyan/notebooks/models \
    && mkdir -p /home/jovyan/notebooks/datasets \
    && mkdir -p /home/jovyan/notebooks/checkpoints

# Add environment variables for fine-tuning
ENV TRANSFORMERS_CACHE=/home/jovyan/models/cache
ENV HF_HOME=/home/jovyan/models/huggingface
ENV TORCH_CUDA_ARCH_LIST="7.0;7.5;8.0;8.6;8.9;9.0"

EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--allow-root"]