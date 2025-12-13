#!/bin/bash
# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0
#
# Build relocatable Python virtualenvs for JupyterHub
#
# This script runs inside a tk-jupyter-base container and creates venvs
# that inherit PyTorch from the base image via --system-site-packages.
#
# Usage:
#   # Run inside tk-jupyter-base container on target architecture
#   docker run --rm -v /tmp/venvs-output:/output harbor.thinkube.io/library/tk-jupyter-base:latest \
#     /bin/bash /path/to/build-venvs.sh
#
# Output:
#   /output/{arch}/ml-gpu.tar.gz
#   /output/{arch}/fine-tuning.tar.gz
#   /output/{arch}/agent-dev.tar.gz

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

# Base packages (included in ALL venvs)
BASE_PACKAGES=(
  ipykernel
  "transformers==4.56.2"
  "datasets==4.1.1"
  "accelerate==1.10.1"
  nvidia-modelopt
  "pandas==2.3.2"
  "scikit-learn==1.7.2"
  "matplotlib==3.10.6"
  "seaborn==0.13.2"
  "plotly==6.3.0"
  "psycopg2-binary==2.9.10"
  "redis==6.4.0"
  "qdrant-client==1.15.1"
  "opensearch-py==3.0.0"
  "mlflow==3.4.0"
  "boto3==1.40.40"
  clickhouse-connect
  chromadb
  nats-py
  "weaviate-client==4.17.0"
  "litellm==1.74.9"
  kubernetes
  PyGithub
  hera-workflows
  argilla
  cvat-sdk
  langfuse
  openai
  arxiv
  "python-dotenv==1.1.1"
  "requests==2.32.5"
  "httpx==0.28.1"
  "pydantic==2.11.9"
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

# Fine-tuning specific packages
FINETUNING_PACKAGES=(
  "bitsandbytes>=0.48.2"
  "peft>=0.17.1"
  "trl==0.23.0"
  tyro
  hf_transfer
  sentencepiece
  protobuf
  openpyxl
)

# Agent development packages
AGENT_PACKAGES=(
  "langchain==1.1.3"
  "langchain-core==1.1.3"
  "langchain-community==0.4.1"
  "langchain-openai==1.1.1"
  "ag2[openai]==0.10.2"
  "langgraph==0.4.1"
  "openai-agents==0.6.2"
  "crewai==1.7.0"
  "crewai-tools==1.7.0"
  "faiss-cpu==1.12.0"
  "opentelemetry-sdk==1.39.0"
  "opentelemetry-exporter-otlp==1.39.0"
  "opentelemetry-api==1.39.0"
  tiktoken
)

# Function to create a venv with base packages
create_venv() {
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
  echo "Installing base packages..."
  "$venv_path/bin/pip" install "${BASE_PACKAGES[@]}"
}

# Function to make venv relocatable and package it
package_venv() {
  local name=$1
  local venv_path="$BUILD_DIR/$name"

  echo ""
  echo ">>> Packaging venv: $name"

  # Fix the pyvenv.cfg to use relative paths
  # The venv will be extracted to /home/thinkube/venvs/{arch}/{name}
  # We set home to a placeholder that gets fixed at extraction time
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
# Build ml-gpu venv (base only)
# ============================================
create_venv "ml-gpu"
package_venv "ml-gpu"

# ============================================
# Build fine-tuning venv (base + fine-tuning)
# ============================================
create_venv "fine-tuning"

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
create_venv "agent-dev"

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
echo "To upload to GitHub release $VERSION:"
echo "  gh release create $VERSION $OUTPUT_DIR/*.tar.gz --repo thinkube/thinkube-venvs"
echo ""
echo "Or upload to an existing release:"
echo "  gh release upload $VERSION $OUTPUT_DIR/*.tar.gz --repo thinkube/thinkube-venvs"
