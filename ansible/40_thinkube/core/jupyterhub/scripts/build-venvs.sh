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
#
# ---------------------------------------------------------------------------
# PyTorch comes from the base image. Never from PyPI.
#
# tk-jupyter-base is built on the NGC PyTorch container, whose torch, CUDA
# libraries, triton and flash-attn are compiled for the GPUs this platform
# runs on - including GB10 / Grace Blackwell (sm_121), for which stock PyPI
# wheels carry no kernels. The venvs use --system-site-packages so they
# inherit that build.
#
# A PyPI torch installed into a venv SHADOWS the base image build for every
# process using that venv. It is a generic wheel: it drops the vendor tuning,
# and it breaks any extension compiled against the base image's torch ABI.
#
# Therefore:
#   - no package list here may name torch, and
#   - any package that depends on torch must not be allowed to resolve it.
#
# NVIDIA's DGX Spark playbook states this requirement directly: install
# Unsloth and its dependencies with --no-deps "to avoid overwriting the
# optimized PyTorch and CUDA libraries already present in the NGC container".
#   https://github.com/NVIDIA/dgx-spark-playbooks/tree/main/nvidia/unsloth
#
# To verify a built venv honours this, the venv's torch must resolve OUTSIDE
# the venv:
#   $VENV/bin/python -c "import torch,os; print(torch.__version__, os.path.dirname(torch.__file__))"
# A path under $VENV/lib/.../site-packages/torch means the venv shadows the
# base image and the build is wrong.
# ---------------------------------------------------------------------------

set -euo pipefail

# Version for the venvs release
VERSION="${VENVS_VERSION:-v0.1.0}"

# DevPI index URL for thinkube packages (tk-llm, etc.)
DEVPI_INDEX_URL="${DEVPI_INDEX_URL:-}"
EXTRA_INDEX_ARGS=""
if [ -n "$DEVPI_INDEX_URL" ]; then
  EXTRA_INDEX_ARGS="--extra-index-url $DEVPI_INDEX_URL"
  echo "Using DevPI index: $DEVPI_INDEX_URL"
fi

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
OUTPUT_DIR="${OUTPUT_DIR:-/output}"
mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

# Base ML packages (included in BOTH venvs)
# These provide the common ML/data science foundation
BASE_PACKAGES=(
  ipykernel
  transformers
  # transformers loads optimised kernels from the Hub through this, and
  # bitsandbytes looks for it too; without it both log a missing-module warning
  # on import. Pure Python, so it carries no torch ABI.
  kernels
  "datasets==4.3.0"  # Pinned for Unsloth compatibility (4.4.x causes recursion errors)
  # torchvision is NOT listed: it declares an exact torch== pin, so naming it
  # here installs a PyPI torch into the venv and shadows the base image build.
  # The base image already ships a torchvision matched to its own torch.
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
  langchain-qdrant
  opensearch-py
  mlflow
  boto3
  clickhouse-connect
  chromadb
  nats-py
  weaviate-client
  litellm
  kubernetes==36.0.3
  PyGithub
  hera-workflows
  argilla
  cvat-sdk
  langfuse
  openai
  "tk-llm[openai]"
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
  python-constraint  # Puzzle generator for the zebra-grpo example notebook
  # Kernels for hybrid-attention models (Qwen3.5 GatedDeltaNet layers).
  # Without them transformers falls back to a slow torch implementation.
  # flash-linear-attention is pure Python over triton, JIT-compiled at run
  # time, so it carries no torch ABI of its own and installs normally.
  flash-linear-attention
  # torchao needs a floor and, on older images, a ceiling too.
  #
  # The floor: peft gates LoRA creation on is_torchao_available(), which
  # rejects the torchao the base image ships and raises. Unsloth catches that
  # and carries on, but prints "Ignoring an unusable torchao" during model
  # setup - a warning in the first cells of every notebook using this venv.
  #
  # The ceiling only bites below torch 2.11: from 0.17 torchao imports
  # torch.nn.functional.ScalingType, absent before then, which makes
  # `import peft` fail outright. The base image now ships torch 2.11, so the
  # ceiling is gone and newer torchao is allowed - it also carries the CUDA
  # kernels that 0.16 failed to load on amd64.
  #
  # If the base image is ever moved back below torch 2.11, this becomes
  # torchao==0.16.0 again. The build's verification step catches it either way.
  "torchao>=0.16"
)
# causal-conv1d is NOT listed - it ships a compiled CUDA extension and is
# installed separately below, from source. See that step for why.

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
  "$venv_path/bin/pip" install $EXTRA_INDEX_ARGS "${BASE_PACKAGES[@]}"
}

# Fail the build if a venv shadows the base image's torch, or ships a compiled
# extension built against a different one. Both are silent at install time and
# surface much later as import errors or as kernels that compute wrongly, so
# they are checked here rather than trusted to the install flags above.
verify_torch_inheritance() {
  local name=$1
  local venv_path="$BUILD_DIR/$name"

  echo ""
  echo ">>> Verifying torch inheritance: $name"
  # No heredoc: this script is inlined into a ConfigMap with every line
  # indented, and an indented heredoc terminator does not close the document.
  # The checker is written to a file, then run.
  local check_py="$venv_path/.verify_torch.py"
  {
    echo "import os, sys, importlib"
    echo "venv_path = sys.argv[1]"
    echo "failures = []"
    echo "import torch"
    echo "torch_dir = os.path.dirname(torch.__file__)"
    echo "print(\"    torch \" + torch.__version__)"
    echo "print(\"      from \" + torch_dir)"
    echo "if torch_dir.startswith(os.path.realpath(venv_path)):"
    echo "    failures.append(\"torch is installed INSIDE the venv and shadows the base image build. A package in the lists above declared a torch dependency pip was allowed to resolve. Find it and install it with --no-deps.\")"
    echo "for mod, note in ((\"causal_conv1d_cuda\", \"causal-conv1d CUDA extension\"), (\"flash_attn_2_cuda\", \"flash-attn CUDA extension\")):"
    echo "    try:"
    echo "        importlib.import_module(mod)"
    echo "        print(\"    ok   \" + mod)"
    echo "    except ModuleNotFoundError:"
    echo "        print(\"    n/a  \" + mod + \" (not installed in this venv)\")"
    echo "    except ImportError as e:"
    echo "        failures.append(note + \" is installed but does not load against this torch, so it was built against a different one: \" + str(e))"
    echo "    except Exception as e:"
    echo "        print(\"    skip \" + mod + \" (\" + type(e).__name__ + \")\")"
    echo "try:"
    echo "    import peft, torchao"
    echo "    from peft.import_utils import is_torchao_available"
    echo "    if is_torchao_available():"
    echo "        print(\"    ok   peft accepts torchao \" + torchao.__version__)"
    echo "    else:"
    echo "        failures.append(\"peft rejects torchao \" + torchao.__version__ + \"; LoRA creation will warn. Adjust the torchao pin in FINETUNING_PACKAGES.\")"
    echo "except ImportError as e:"
    echo "    if \"torchao\" in str(e) or \"ScalingType\" in str(e):"
    echo "        failures.append(\"torchao is unusable with this torch: \" + str(e))"
    echo "if failures:"
    echo "    print(\"\")"
    echo "    print(\"  TORCH VERIFICATION FAILED\")"
    echo "    for f in failures:"
    echo "        print(\"    - \" + f)"
    echo "    sys.exit(1)"
    echo "print(\"    torch inheritance OK\")"
  } > "$check_py"
  "$venv_path/bin/python" "$check_py" "$venv_path"
  rm -f "$check_py"
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

  # Create tarball with arch prefix
  echo "Creating tarball..."
  tar -czf "$OUTPUT_DIR/$ARCH_DIR-$name.tar.gz" -C "$BUILD_DIR" "$name"

  # Show size
  local size=$(du -h "$OUTPUT_DIR/$ARCH_DIR-$name.tar.gz" | cut -f1)
  echo "Created: $OUTPUT_DIR/$ARCH_DIR-$name.tar.gz ($size)"
}

# ============================================
# Build fine-tuning venv (base + fine-tuning)
# ============================================
create_venv_with_base "fine-tuning"

echo "Installing fine-tuning packages..."
"$BUILD_DIR/fine-tuning/bin/pip" install "${FINETUNING_PACKAGES[@]}"

# causal-conv1d: compiled CUDA extension, must be built against THIS torch
#
# It provides the fast causal convolution used by hybrid-attention models
# (Qwen3.5's GatedDeltaNet layers). Because it is a C++/CUDA extension, a
# binary built against a different torch does not fail at install time - it
# fails at import, with an undefined-symbol error, long after the build looks
# successful. Installing it plainly is not safe: every default leads to a
# foreign binary.
#
#   CAUSAL_CONV1D_FORCE_BUILD=TRUE  its setup.py otherwise downloads a
#                                   prebuilt CUDA wheel from GitHub releases,
#                                   built against whatever torch upstream used
#   --no-binary causal_conv1d       stops pip preferring a PyPI wheel
#   --no-cache-dir                  stops pip reusing a wheel it built or
#                                   downloaded under a previous torch
#   --no-build-isolation            builds against the torch installed here;
#                                   without it pip creates an isolated env,
#                                   pulls its OWN torch to build against, and
#                                   produces a binary for that torch instead
#   --no-deps                       it declares a bare torch dependency, which
#                                   would install a PyPI torch over the image's
#
# TORCH_CUDA_ARCH_LIST pins the target architectures so the build does not
# depend on which GPU happens to be visible in the builder. 12.0 covers
# GB10 / Grace Blackwell (sm_121) by forward compatibility.
echo "Building causal-conv1d from source against the image's torch..."
CAUSAL_CONV1D_FORCE_BUILD=TRUE \
TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.0 8.6 8.9 9.0 12.0}" \
MAX_JOBS="${MAX_JOBS:-8}" \
"$BUILD_DIR/fine-tuning/bin/pip" install \
  --no-binary causal_conv1d --no-cache-dir --no-build-isolation --no-deps \
  causal-conv1d

# Install Unsloth
#
# --no-deps is mandatory, for two independent reasons:
#
# 1. Unsloth's dependency chain resolves torch, which would shadow the base
#    image build. See the PyTorch note at the top of this file.
#
# 2. Unsloth's declared ranges lag its own code. Released versions still
#    declare torch<2.12.0, transformers<=5.5.0 and trl<=0.24.0, while the
#    code targets newer ones - the torch 2.12 support below ships in a
#    version whose metadata still excludes torch 2.12. Resolving those
#    ranges pins the venv to versions Unsloth itself has moved past.
#
# Minimum version: Unsloth 2026.7.x.
#   torch 2.12 made torch._dynamo.config overrides thread-local, so a
#   recompile limit raised on the main thread never reaches the autograd
#   worker threads that run backward under gradient checkpointing. Those
#   threads recompile fullgraph kernels against the default limit of 8.
#   Against torch 2.12, earlier Unsloth dies at training step 0 with
#   "FailOnRecompileLimitHit: Hard failure due to fullgraph=True", and
#   raising torch._dynamo.config.recompile_limit does NOT help - that
#   symptom pair is the signature of an Unsloth too old for the torch here.
#   Restored to process-global by unslothai/unsloth#7019.
#   https://github.com/unslothai/unsloth/issues/6825
#
# Installing from git HEAD satisfies the floor, and keeps whatever GB10 /
# sm_121 support has landed upstream. Pin a tag here only alongside a
# recorded reason, and never below 2026.7.x while the base image ships
# torch 2.12 or newer.
echo "Installing Unsloth..."
"$BUILD_DIR/fine-tuning/bin/pip" install "git+https://github.com/unslothai/unsloth-zoo.git" --no-deps
"$BUILD_DIR/fine-tuning/bin/pip" install "unsloth[cu130onlytorch291] @ git+https://github.com/unslothai/unsloth.git" --no-build-isolation --no-deps

verify_torch_inheritance "fine-tuning"
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

verify_torch_inheritance "agent-dev"
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
