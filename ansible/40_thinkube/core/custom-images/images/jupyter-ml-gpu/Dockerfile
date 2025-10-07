# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

ARG HARBOR_REGISTRY
FROM ${HARBOR_REGISTRY}/library/cuda:12.6.0-runtime-ubuntu24.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3-pip \
    build-essential \
    git \
    curl \
    wget \
    vim \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x LTS (required for Claude Code CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create claude wrapper script to ensure it's in PATH
RUN printf '#!/bin/bash\n\
# Wrapper script for Claude Code CLI\n\
export PATH="/usr/local/lib/node_modules/.bin:$PATH"\n\
exec /usr/local/bin/claude "$@"\n' > /usr/local/bin/claude-wrapper && \
    chmod +x /usr/local/bin/claude-wrapper && \
    ln -sf /usr/local/bin/claude-wrapper /usr/bin/claude

# Set python3.12 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install PyTorch with CUDA support first
RUN pip install --no-cache-dir --break-system-packages \
    torch==2.4.1 \
    torchvision==0.19.1 \
    torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/cu121

# Install remaining packages from requirements
RUN pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# Create jovyan user (check if user with UID 1000 exists first)
RUN id -u 1000 &>/dev/null || useradd -m -s /bin/bash -u 1000 jovyan; \
    echo "jovyan ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER jovyan
WORKDIR /home/jovyan

# Create directory structure
RUN mkdir -p /home/jovyan/notebooks \
    && mkdir -p /home/jovyan/scratch \
    && mkdir -p /home/jovyan/datasets \
    && mkdir -p /home/jovyan/models \
    && mkdir -p /home/jovyan/.jupyter

# Configure JupyterLab
RUN jupyter lab --generate-config && \
    echo "c.ServerApp.allow_origin = '*'" >> /home/jovyan/.jupyter/jupyter_lab_config.py && \
    echo "c.ServerApp.allow_remote_access = True" >> /home/jovyan/.jupyter/jupyter_lab_config.py && \
    echo "c.ServerApp.ip = '0.0.0.0'" >> /home/jovyan/.jupyter/jupyter_lab_config.py

# Verify GPU access (will fail during build but helps with debugging)
RUN python -c "import torch; print(f'PyTorch version: {torch.__version__}')" || true

EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--allow-root"]