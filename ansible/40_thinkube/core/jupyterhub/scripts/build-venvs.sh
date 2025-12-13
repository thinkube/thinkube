#!/bin/bash
# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0
#
# Build relocatable Python virtualenvs for JupyterHub
#
# This script runs inside a tk-jupyter-base container and creates venvs
# that inherit PyTorch from the base image via --system-site-packages.
#
# TWO venvs are built:
# - fine-tuning: Base ML packages + fine-tuning specific (bitsandbytes, peft, trl, unsloth)
# - agent-dev: Base ML packages + agent frameworks (langchain, crewai, etc.)
#
# Users who only need basic ML (PyTorch, transformers) use the system Python
# from tk-jupyter-base directly - no venv needed.

set -euo pipefail

# Version for the venvs release
VERSION="${VENVS_VERSION:-v0.1.0}"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
  ARCH_DIR="arm64"
else
  ARCH_DIR="amd64"
fi

echo "=============================================="
echo "Building Jupyter venvs for $ARCH_DIR"
echo "Version: $VERSION"
echo "=============================================="

BUILD_DIR="/tmp/venvs-build"
OUTPUT_DIR="${OUTPUT_DIR:-/output}/$ARCH_DIR"
mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

# Base ML packages (included in BOTH venvs)
# These provide the common ML/data science foundation
BASE_PACKAGES=(
  ipykernel
  transformers
  datasets
  accelerate
  nvidia-modelopt
  pandas
  scikit-learn
  matplotlib
  seaborn
  plotly
  psycopg2-binary
  redis
  qdrant-client
  opensearch-py
  mlflow
  boto3
  clickhouse-connect
  chromadb
  nats-py
  weaviate-client
  litellm
  kubernetes
  PyGithub
  hera-workflows
  argilla
  cvat-sdk
  langfuse
  openai
  arxiv
  python-dotenv
  requests
  httpx
  pydantic
  sqlalchemy
  alembic
  ipywidgets
  jupyterlab-widgets
  tqdm
  Pillow
  opencv-python
  sentence-transformers
  spacy
  grpcio
  grpcio-tools
  gql
  websockets
  claude-agent-sdk
  openai-harmony
)

# Fine-tuning specific packages (ON TOP of base)
FINETUNING_PACKAGES=(
  bitsandbytes
  peft
  trl
  tyro
  hf_transfer
  sentencepiece
  protobuf
  openpyxl
)

# Agent development packages (ON TOP of base)
# Note: Let pip resolve compatible versions for langchain ecosystem
AGENT_PACKAGES=(
  langchain
  langchain-core
  langchain-community
  langchain-openai
  langgraph
  "ag2[openai]"
  openai-agents
  crewai
  crewai-tools
  faiss-cpu
  opentelemetry-sdk
  opentelemetry-exporter-otlp
  opentelemetry-api
  tiktoken
)

# Function to create a venv with base packages
create_venv_with_base() {
  local name=$1
  local venv_path="$BUILD_DIR/$name"

  echo ""
  echo ">>> Creating venv: $name"
  echo "----------------------------------------------"

  # Create venv with system site packages (inherits PyTorch from base image)
  python3 -m venv --system-site-packages "$venv_path"

  # Upgrade pip
  "$venv_path/bin/pip" install --upgrade pip

  # Install base packages
  echo "Installing base ML packages..."
  "$venv_path/bin/pip" install "${BASE_PACKAGES[@]}"
}

# Function to make venv relocatable and package it
package_venv() {
  local name=$1
  local venv_path="$BUILD_DIR/$name"

  echo ""
  echo ">>> Packaging venv: $name"

  # Fix the pyvenv.cfg to use relative paths
  sed -i "s|^home = .*|home = /home/thinkube/venvs/$ARCH_DIR/$name|" "$venv_path/pyvenv.cfg"

  # Register as Jupyter kernel (kernel.json will be inside the venv)
  "$venv_path/bin/python" -m ipykernel install \
    --prefix="$venv_path" \
    --name="$name" \
    --display-name="$name ($ARCH_DIR)"

  # Create tarball
  echo "Creating tarball..."
  tar -czf "$OUTPUT_DIR/$name.tar.gz" -C "$BUILD_DIR" "$name"

  # Show size
  local size=$(du -h "$OUTPUT_DIR/$name.tar.gz" | cut -f1)
  echo "Created: $OUTPUT_DIR/$name.tar.gz ($size)"
}

# ============================================
# Build fine-tuning venv (base + fine-tuning)
# ============================================
create_venv_with_base "fine-tuning"

echo "Installing fine-tuning packages..."
"$BUILD_DIR/fine-tuning/bin/pip" install "${FINETUNING_PACKAGES[@]}"

# Install Unsloth (special handling to avoid conflicts)
echo "Installing Unsloth..."
"$BUILD_DIR/fine-tuning/bin/pip" install "git+https://github.com/unslothai/unsloth-zoo.git" --no-deps
"$BUILD_DIR/fine-tuning/bin/pip" install "unsloth[cu130onlytorch291] @ git+https://github.com/unslothai/unsloth.git" --no-build-isolation --no-deps

package_venv "fine-tuning"

# ============================================
# Build agent-dev venv (base + agent frameworks)
# ============================================
create_venv_with_base "agent-dev"

echo "Installing agent development packages..."
"$BUILD_DIR/agent-dev/bin/pip" install "${AGENT_PACKAGES[@]}"

# Install openlit without deps to avoid langchain downgrade
echo "Installing openlit..."
"$BUILD_DIR/agent-dev/bin/pip" install openlit --no-deps

package_venv "agent-dev"

# ============================================
# Summary
# ============================================
echo ""
echo "=============================================="
echo "Build complete!"
echo "=============================================="
echo ""
echo "Output directory: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"
echo ""
echo "Venvs built:"
echo "  - fine-tuning: Base ML + fine-tuning packages"
echo "  - agent-dev: Base ML + agent frameworks"
echo ""
echo "Users who only need PyTorch/transformers use the system Python directly."
