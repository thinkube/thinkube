# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
Thinkube Model Registration Helper

Provides a simple interface for:
- Loading models from MLflow Model Registry (mirrored from HuggingFace)
- Registering fine-tuned models with FP8 quantization

Usage:
    from thinkube_models import load_model_for_finetuning, register_finetuned_model

    # Load a model from MLflow (uses local JuiceFS, no HuggingFace download)
    model, tokenizer = load_model_for_finetuning("openai/gpt-oss-20b")

    # After fine-tuning with Unsloth:
    register_finetuned_model(
        model=model,
        tokenizer=tokenizer,
        name="gpt-oss-tool-use",
        base_model="openai/gpt-oss-20b",
        description="Fine-tuned for tool use",
        quantization="FP8"  # or "BF16" for no quantization
    )
"""

import os
import requests
from pathlib import Path
from typing import Optional, Literal


# Staging path for models (shared with Argo workflows via JuiceFS)
STAGING_PATH = Path.home() / "thinkube" / "mlflow" / ".staging"

# Supported quantization formats
QuantizationFormat = Literal["FP8", "NVFP4", "BF16"]


def get_mlflow_config():
    """Get MLflow configuration from environment."""
    return {
        'tracking_uri': os.environ.get('MLFLOW_TRACKING_URI', 'http://mlflow.mlflow.svc.cluster.local:5000'),
        'token_url': os.environ.get('MLFLOW_KEYCLOAK_TOKEN_URL'),
        'client_id': os.environ.get('MLFLOW_KEYCLOAK_CLIENT_ID', 'mlflow'),
        'client_secret': os.environ.get('MLFLOW_CLIENT_SECRET'),
        'username': os.environ.get('MLFLOW_AUTH_USERNAME'),
        'password': os.environ.get('MLFLOW_AUTH_PASSWORD'),
    }


def get_mlflow_token():
    """Get authentication token for MLflow API."""
    config = get_mlflow_config()

    if not config['token_url']:
        return None

    try:
        response = requests.post(
            config['token_url'],
            data={
                'grant_type': 'password',
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'username': config['username'],
                'password': config['password'],
                'scope': 'openid'
            },
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        print(f"Warning: Could not get MLflow token: {e}")
        return None


def load_model_for_finetuning(model_id: str, device_map: str = "auto"):
    """
    Load a model from MLflow Model Registry for fine-tuning.

    This loads models that have been mirrored from HuggingFace to MLflow,
    using local JuiceFS storage instead of downloading from the internet.

    Args:
        model_id: HuggingFace model ID (e.g., "unsloth/gpt-oss-20b")
        device_map: Device mapping for model loading (default: "auto")

    Returns:
        tuple: (model, tokenizer) ready for fine-tuning with Unsloth

    Example:
        from thinkube_models import load_model_for_finetuning

        # Load from MLflow (uses local JuiceFS, no HuggingFace download)
        model, tokenizer = load_model_for_finetuning("unsloth/gpt-oss-20b")

        # Then fine-tune with Unsloth as usual
        model = FastLanguageModel.get_peft_model(model, ...)
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Convert model_id to MLflow model name (replace / with -)
    model_name = model_id.replace('/', '-')

    print(f"Loading model from MLflow: {model_id}")
    print(f"  MLflow model name: {model_name}")

    # Get MLflow configuration and token
    config = get_mlflow_config()
    token = get_mlflow_token()

    if not token:
        raise RuntimeError(
            "Could not authenticate with MLflow. "
            "Ensure MLFLOW_* environment variables are set."
        )

    headers = {'Authorization': f'Bearer {token}'}
    mlflow_url = config['tracking_uri']

    # Query MLflow for model versions
    print(f"  Querying MLflow for model versions...")
    response = requests.get(
        f"{mlflow_url}/api/2.0/mlflow/model-versions/search",
        params={'filter': f"name='{model_name}'"},
        headers=headers,
        verify=False,
        timeout=30
    )
    response.raise_for_status()

    versions = response.json().get('model_versions', [])
    if not versions:
        raise ValueError(
            f"Model '{model_name}' not found in MLflow registry. "
            f"Please mirror the model first using thinkube-control."
        )

    # Get latest version
    latest = max(versions, key=lambda v: int(v['version']))
    run_id = latest['run_id']
    print(f"  Found version {latest['version']} (run_id: {run_id})")

    # Get run details to retrieve experiment_id
    run_response = requests.get(
        f"{mlflow_url}/api/2.0/mlflow/runs/get",
        params={'run_id': run_id},
        headers=headers,
        verify=False,
        timeout=30
    )
    run_response.raise_for_status()
    experiment_id = run_response.json()['run']['info']['experiment_id']

    # Construct model path on JuiceFS
    # Models are stored at: /mlflow-models/artifacts/{experiment_id}/{run_id}/artifacts/model
    model_path = Path(f'/mlflow-models/artifacts/{experiment_id}/{run_id}/artifacts/model')

    if not model_path.exists():
        raise FileNotFoundError(
            f"Model path does not exist: {model_path}. "
            f"The model may not have been mirrored correctly."
        )

    print(f"  Model path: {model_path}")

    # Load with Unsloth for efficient fine-tuning
    try:
        from unsloth import FastLanguageModel

        print(f"  Loading with Unsloth FastLanguageModel...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(model_path),
            dtype=None,  # Auto-detect
            load_in_4bit=True,  # Use 4-bit for fine-tuning efficiency
            device_map=device_map,
        )
        print(f"  ✓ Model loaded successfully with Unsloth")

    except ImportError:
        # Fallback to standard transformers if Unsloth not available
        print(f"  Unsloth not available, loading with transformers...")
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            device_map=device_map,
            torch_dtype="auto",
        )
        print(f"  ✓ Model loaded successfully with transformers")

    return model, tokenizer


def get_thinkube_control_url():
    """Get thinkube-control API URL from environment."""
    # Try service discovery first
    url = os.environ.get('THINKUBE_CONTROL_URL')
    if url:
        return url.rstrip('/')

    # Fallback to in-cluster service
    return "http://backend.thinkube-control.svc.cluster.local:8000"


def get_auth_token():
    """Get authentication token for thinkube-control API."""
    # Try to get token from environment (set by service discovery)
    token = os.environ.get('THINKUBE_CONTROL_TOKEN')
    if token:
        return token

    # Try to read from JupyterHub auth
    token_file = Path.home() / ".config" / "thinkube" / "token"
    if token_file.exists():
        return token_file.read_text().strip()

    # Try to get from Keycloak using service account
    keycloak_url = os.environ.get('KEYCLOAK_URL')
    client_id = os.environ.get('KEYCLOAK_CLIENT_ID', 'thinkube-control')
    client_secret = os.environ.get('KEYCLOAK_CLIENT_SECRET')

    if keycloak_url and client_secret:
        try:
            realm = os.environ.get('KEYCLOAK_REALM', 'thinkube')
            token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"

            response = requests.post(
                token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            print(f"Warning: Could not get token from Keycloak: {e}")

    return None


def quantize_model_fp8(model, tokenizer, calib_data=None, num_samples: int = 128):
    """
    Quantize a model to FP8 format using NVIDIA ModelOpt.

    This produces a HuggingFace-compatible checkpoint that TensorRT-LLM can
    load directly with optimized FP8 inference.

    Args:
        model: The fine-tuned model (HuggingFace PreTrainedModel)
        tokenizer: The tokenizer
        calib_data: Optional calibration dataset (list of strings or Dataset)
        num_samples: Number of calibration samples (default: 128)

    Returns:
        Quantized model ready for saving
    """
    import torch
    import modelopt.torch.quantization as mtq
    from datasets import load_dataset

    print("Quantizing model to FP8 format...")
    print(f"  Using {num_samples} calibration samples")

    # Prepare calibration data
    if calib_data is None:
        print("  Loading default calibration dataset (cnn_dailymail)...")
        dataset = load_dataset("cnn_dailymail", "3.0.0", split="train")
        calib_texts = [item["article"][:1024] for item in dataset.select(range(num_samples))]
    elif isinstance(calib_data, list):
        calib_texts = calib_data[:num_samples]
    else:
        # Assume it's a HuggingFace Dataset
        calib_texts = [item.get("text", item.get("article", str(item)))[:1024]
                       for item in calib_data.select(range(min(num_samples, len(calib_data))))]

    # Tokenize calibration data
    print("  Tokenizing calibration data...")
    calib_tokens = tokenizer(
        calib_texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512
    )

    # Move to GPU if available
    device = next(model.parameters()).device
    calib_tokens = {k: v.to(device) for k, v in calib_tokens.items()}

    # Define calibration forward loop
    def forward_loop(model):
        with torch.no_grad():
            for i in range(0, len(calib_texts), 8):  # Batch size 8
                batch = {k: v[i:i+8] for k, v in calib_tokens.items()}
                if batch["input_ids"].shape[0] > 0:
                    model(**batch)

    # Apply FP8 quantization
    print("  Applying FP8 quantization with calibration...")
    config = mtq.FP8_DEFAULT_CFG

    with torch.no_grad():
        quantized_model = mtq.quantize(model, config, forward_loop)

    print("  ✓ FP8 quantization complete")
    return quantized_model


def quantize_model_nvfp4(model, tokenizer, calib_data=None, num_samples: int = 128):
    """
    Quantize a model to NVFP4 format using NVIDIA ModelOpt.

    NVFP4 provides 4-bit quantization for maximum compression.
    Note: Requires Blackwell GPU (GB10) for inference.

    Args:
        model: The fine-tuned model (HuggingFace PreTrainedModel)
        tokenizer: The tokenizer
        calib_data: Optional calibration dataset
        num_samples: Number of calibration samples (default: 128)

    Returns:
        Quantized model ready for saving
    """
    import torch
    import modelopt.torch.quantization as mtq
    from datasets import load_dataset

    print("Quantizing model to NVFP4 format...")
    print(f"  Using {num_samples} calibration samples")
    print("  Note: NVFP4 inference requires Blackwell GPU (GB10)")

    # Prepare calibration data (same as FP8)
    if calib_data is None:
        print("  Loading default calibration dataset (cnn_dailymail)...")
        dataset = load_dataset("cnn_dailymail", "3.0.0", split="train")
        calib_texts = [item["article"][:1024] for item in dataset.select(range(num_samples))]
    elif isinstance(calib_data, list):
        calib_texts = calib_data[:num_samples]
    else:
        calib_texts = [item.get("text", item.get("article", str(item)))[:1024]
                       for item in calib_data.select(range(min(num_samples, len(calib_data))))]

    # Tokenize calibration data
    print("  Tokenizing calibration data...")
    calib_tokens = tokenizer(
        calib_texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512
    )

    device = next(model.parameters()).device
    calib_tokens = {k: v.to(device) for k, v in calib_tokens.items()}

    def forward_loop(model):
        with torch.no_grad():
            for i in range(0, len(calib_texts), 8):
                batch = {k: v[i:i+8] for k, v in calib_tokens.items()}
                if batch["input_ids"].shape[0] > 0:
                    model(**batch)

    # Apply NVFP4 quantization
    print("  Applying NVFP4 quantization with calibration...")
    config = mtq.NVFP4_DEFAULT_CFG

    with torch.no_grad():
        quantized_model = mtq.quantize(model, config, forward_loop)

    print("  ✓ NVFP4 quantization complete")
    return quantized_model


def save_model_to_staging(model, tokenizer, name: str, save_method: str = "merged_16bit"):
    """
    Save a fine-tuned model to the staging area.

    Args:
        model: The fine-tuned model (Unsloth FastLanguageModel)
        tokenizer: The tokenizer
        name: Model name (used as directory name)
        save_method: How to save ("merged_16bit", "merged_4bit", "lora")

    Returns:
        Path to the saved model directory
    """
    staging_dir = STAGING_PATH / name
    staging_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving model to staging: {staging_dir}")

    # Use Unsloth's save method
    model.save_pretrained_merged(
        str(staging_dir),
        tokenizer,
        save_method=save_method,
    )

    print(f"✓ Model saved to staging: {staging_dir}")
    return staging_dir


def register_finetuned_model(
    model,
    tokenizer,
    name: str,
    base_model: str,
    task: str = "text-generation",
    server_type: str = "tensorrt-llm",
    description: str = None,
    quantization: QuantizationFormat = "FP8",
    calib_data=None,
    num_calib_samples: int = 128,
    wait: bool = False
):
    """
    Save and register a fine-tuned model in the Thinkube Model Catalog.

    This function:
    1. Quantizes the model to FP8/NVFP4 format (for TensorRT-LLM optimization)
    2. Saves the quantized model to the staging area (JuiceFS shared with Argo)
    3. Calls the thinkube-control API to register it in MLflow
    4. Optionally waits for registration to complete

    Args:
        model: The fine-tuned model (Unsloth FastLanguageModel or HuggingFace model)
        tokenizer: The tokenizer
        name: Model name for the catalog (e.g., "gpt-oss-tool-use")
        base_model: Original model ID (e.g., "unsloth/gpt-oss-20b")
        task: Model task (default: "text-generation")
        server_type: Target server (default: "tensorrt-llm")
        description: Optional description
        quantization: Quantization format - "FP8" (recommended), "NVFP4", or "BF16"
        calib_data: Optional calibration dataset for quantization
        num_calib_samples: Number of calibration samples (default: 128)
        wait: If True, wait for registration to complete

    Returns:
        dict: Registration job info with keys:
            - job_id: UUID of the registration job
            - workflow_id: Argo workflow name
            - status: Current status
            - message: Status message

    Example:
        from thinkube_models import register_finetuned_model

        # Register with FP8 quantization (recommended for TensorRT-LLM)
        result = register_finetuned_model(
            model=model,
            tokenizer=tokenizer,
            name="gpt-oss-tool-use",
            base_model="unsloth/gpt-oss-20b",
            description="Fine-tuned for tool use",
            quantization="FP8"
        )
        print(f"Registration started: {result['workflow_id']}")
    """
    # Step 1: Get the HuggingFace model from Unsloth if needed
    # Unsloth's FastLanguageModel wraps the actual model
    hf_model = model
    if hasattr(model, 'model'):
        hf_model = model.model
    elif hasattr(model, 'get_base_model'):
        hf_model = model.get_base_model()

    # Step 2: Apply quantization if requested
    if quantization == "FP8":
        print(f"Applying FP8 quantization for TensorRT-LLM optimization...")
        quantized_model = quantize_model_fp8(hf_model, tokenizer, calib_data, num_calib_samples)
    elif quantization == "NVFP4":
        print(f"Applying NVFP4 quantization for maximum compression...")
        quantized_model = quantize_model_nvfp4(hf_model, tokenizer, calib_data, num_calib_samples)
    elif quantization == "BF16":
        print(f"Skipping quantization, saving in BF16 format...")
        quantized_model = hf_model
    else:
        raise ValueError(f"Unsupported quantization format: {quantization}. Use 'FP8', 'NVFP4', or 'BF16'")

    # Step 3: Save model to staging using ModelOpt export for quantized models
    staging_dir = STAGING_PATH / name
    staging_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving model to staging: {staging_dir}")

    if quantization in ["FP8", "NVFP4"]:
        # Use ModelOpt's HuggingFace export for quantized models
        from modelopt.torch.export import export_hf_checkpoint
        export_hf_checkpoint(quantized_model, str(staging_dir))
        tokenizer.save_pretrained(str(staging_dir))
    else:
        # Save BF16 model directly
        quantized_model.save_pretrained(str(staging_dir))
        tokenizer.save_pretrained(str(staging_dir))

    print(f"✓ Model saved to staging: {staging_dir}")

    # Step 4: Call thinkube-control API to register in MLflow
    api_url = get_thinkube_control_url()
    token = get_auth_token()

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Include quantization info in description
    quant_info = f" ({quantization})" if quantization != "BF16" else ""
    full_description = description or f"Fine-tuned from {base_model}"
    full_description = f"{full_description}{quant_info}"

    payload = {
        "name": name,
        "source_path": name,  # Relative path in staging
        "base_model": base_model,
        "task": task,
        "server_type": server_type,
        "description": full_description,
        "quantization": quantization
    }

    print(f"Registering model with thinkube-control...")

    try:
        response = requests.post(
            f"{api_url}/api/v1/models/register",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        print(f"✓ Registration job submitted: {result['workflow_id']}")
        print(f"  Status: {result['status']}")
        print(f"  Job ID: {result['job_id']}")

        if wait:
            result = wait_for_registration(result['workflow_id'])

        return result

    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to register model: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        raise


def wait_for_registration(workflow_id: str, timeout: int = 600, poll_interval: int = 10):
    """
    Wait for a registration job to complete.

    Args:
        workflow_id: The Argo workflow ID
        timeout: Maximum seconds to wait (default: 600)
        poll_interval: Seconds between status checks (default: 10)

    Returns:
        dict: Final job status
    """
    import time

    api_url = get_thinkube_control_url()
    token = get_auth_token()

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{api_url}/api/v1/models/mirrors/{workflow_id}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            status = response.json()

            if status['is_complete']:
                print(f"✓ Registration complete: {status['model_id']}")
                return status
            elif status['is_failed']:
                print(f"✗ Registration failed: {status.get('error_message', 'Unknown error')}")
                return status
            else:
                elapsed = int(time.time() - start_time)
                print(f"  Waiting... ({elapsed}s) - Status: {status['status']}")

        except Exception as e:
            print(f"  Warning: Could not check status: {e}")

        time.sleep(poll_interval)

    print(f"✗ Timeout waiting for registration (>{timeout}s)")
    return {"status": "timeout", "workflow_id": workflow_id}


def list_registered_models():
    """
    List all registered models in the catalog.

    Returns:
        list: List of model info dictionaries
    """
    api_url = get_thinkube_control_url()
    token = get_auth_token()

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(
            f"{api_url}/api/v1/models/catalog",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()['models']
    except Exception as e:
        print(f"✗ Failed to list models: {e}")
        return []


def get_staging_path(name: str = None):
    """
    Get the staging path for models.

    Args:
        name: Optional model name to get specific path

    Returns:
        Path object
    """
    if name:
        return STAGING_PATH / name
    return STAGING_PATH
