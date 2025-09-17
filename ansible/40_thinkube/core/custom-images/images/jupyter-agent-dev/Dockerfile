# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

ARG HARBOR_REGISTRY
FROM ${HARBOR_REGISTRY}/library/jupyter-ml-cpu:latest

USER root

# Install additional system dependencies for agent development
RUN apt-get update && apt-get install -y \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt /tmp/agent-requirements.txt

# Install all agent development packages
RUN pip install --no-cache-dir --break-system-packages -r /tmp/agent-requirements.txt

# Copy example notebooks (will be added during build)
COPY --chown=jovyan:jovyan notebooks/agents /home/jovyan/examples/agents || true

USER jovyan

# Create agent development directories
RUN mkdir -p /home/jovyan/notebooks/agents \
    && mkdir -p /home/jovyan/notebooks/tools \
    && mkdir -p /home/jovyan/notebooks/prompts \
    && mkdir -p /home/jovyan/notebooks/chains \
    && mkdir -p /home/jovyan/notebooks/crews

# Add environment variables for agent development
ENV LANGCHAIN_TRACING_V2=false
ENV LANGCHAIN_API_KEY=""

EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--allow-root"]