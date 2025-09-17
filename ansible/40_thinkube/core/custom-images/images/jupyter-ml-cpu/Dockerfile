# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    vim \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install all packages from requirements
RUN pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# Create jovyan user (JupyterHub convention)
RUN useradd -m -s /bin/bash -u 1000 jovyan && \
    echo "jovyan ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Setup Jupyter configuration
USER jovyan
WORKDIR /home/jovyan

# Create directory structure
RUN mkdir -p /home/jovyan/notebooks \
    && mkdir -p /home/jovyan/scratch \
    && mkdir -p /home/jovyan/datasets \
    && mkdir -p /home/jovyan/models \
    && mkdir -p /home/jovyan/.jupyter

# Configure JupyterLab settings
RUN jupyter lab --generate-config && \
    echo "c.ServerApp.allow_origin = '*'" >> /home/jovyan/.jupyter/jupyter_lab_config.py && \
    echo "c.ServerApp.allow_remote_access = True" >> /home/jovyan/.jupyter/jupyter_lab_config.py && \
    echo "c.ServerApp.ip = '0.0.0.0'" >> /home/jovyan/.jupyter/jupyter_lab_config.py

EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--allow-root"]