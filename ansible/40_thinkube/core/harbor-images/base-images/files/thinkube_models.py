# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
Thinkube model helpers for notebooks.

- load_model_for_finetuning: load a mirrored model from the MLflow Model
  Registry for fine-tuning.
- register_finetuned_model: publish a LoRA fine-tune so the LLM Gateway can
  load it on vLLM.

Usage:
    import thinkube_models as tkm

    model, tokenizer = tkm.load_model_for_finetuning("unsloth/Qwen3.5-4B")
    # ... fine-tune with Unsloth, logging to the MLflow run `run_id` ...
    tkm.register_finetuned_model(model, tokenizer, catalog_entry, run_id)
"""

import base64
import os
import shutil
import requests
from pathlib import Path


# Staging folder for merged checkpoints, on the MLflow JuiceFS volume
STAGING_PATH = Path.home() / "thinkube" / "mlflow" / ".staging"

# Environment variables the MLflow helpers read; the notebook server sets them
MLFLOW_ENV = (
    "MLFLOW_TRACKING_URI",
    "MLFLOW_KEYCLOAK_TOKEN_URL",
    "MLFLOW_KEYCLOAK_CLIENT_ID",
    "MLFLOW_CLIENT_SECRET",
    "MLFLOW_AUTH_USERNAME",
    "MLFLOW_AUTH_PASSWORD",
)


def get_mlflow_config():
    """The MLflow settings from the environment; raises if any is missing."""
    missing = [name for name in MLFLOW_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            f"MLflow settings missing from the environment: {', '.join(missing)}. "
            "The notebook server sets them; restart it if they are absent."
        )
    return {
        'tracking_uri': os.environ['MLFLOW_TRACKING_URI'],
        'token_url': os.environ['MLFLOW_KEYCLOAK_TOKEN_URL'],
        'client_id': os.environ['MLFLOW_KEYCLOAK_CLIENT_ID'],
        'client_secret': os.environ['MLFLOW_CLIENT_SECRET'],
        'username': os.environ['MLFLOW_AUTH_USERNAME'],
        'password': os.environ['MLFLOW_AUTH_PASSWORD'],
    }


def get_mlflow_token():
    """A bearer token for the MLflow API, from Keycloak."""
    config = get_mlflow_config()
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
        timeout=30
    )
    response.raise_for_status()
    return response.json()['access_token']


def load_model_for_finetuning(model_id: str, device_map: str = "auto"):
    """
    Load a model from MLflow Model Registry for fine-tuning.

    This loads models that have been mirrored from HuggingFace to MLflow,
    using local JuiceFS storage instead of downloading from the internet.

    Args:
        model_id: HuggingFace model ID (e.g., "unsloth/Qwen3.5-4B")
        device_map: Device mapping for model loading (default: "auto")

    Returns:
        tuple: (model, tokenizer) ready for fine-tuning with Unsloth

    Example:
        from thinkube_models import load_model_for_finetuning

        # Load from MLflow (uses local JuiceFS, no HuggingFace download)
        model, tokenizer = load_model_for_finetuning("unsloth/Qwen3.5-4B")

        # Then fine-tune with Unsloth as usual
        model = FastLanguageModel.get_peft_model(model, ...)
    """
    # Convert model_id to MLflow model name (replace / with -)
    model_name = model_id.replace('/', '-')

    print(f"Loading model from MLflow: {model_id}")
    print(f"  MLflow model name: {model_name}")

    # Get MLflow configuration and token
    config = get_mlflow_config()
    token = get_mlflow_token()

    headers = {'Authorization': f'Bearer {token}'}
    mlflow_url = config['tracking_uri']

    # Query MLflow for model versions
    print(f"  Querying MLflow for model versions...")
    response = requests.get(
        f"{mlflow_url}/api/2.0/mlflow/model-versions/search",
        params={'filter': f"name='{model_name}'"},
        headers=headers,
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
        timeout=30
    )
    run_response.raise_for_status()
    experiment_id = run_response.json()['run']['info']['experiment_id']

    # The notebook server mounts the MLflow artifacts (JuiceFS) at
    # ~/thinkube/mlflow; this module ships only in the Jupyter images.
    model_path = (Path.home() / 'thinkube' / 'mlflow' / 'artifacts'
                  / experiment_id / run_id / 'artifacts' / 'model')
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model {model_id} is registered in MLflow, but its files are not at "
            f"{model_path}. The mirror may not have finished; mirror the model again "
            f"from Thinkube Control's Models page."
        )

    print(f"  Model path: {model_path}")

    # Unsloth converts MXFP4 weights (gpt-oss) to trainable NF4 when
    # load_in_4bit=True; the model it returns is ready for QLoRA.
    try:
        from unsloth import FastLanguageModel
    except ImportError as e:
        raise ImportError(
            "load_model_for_finetuning loads models with Unsloth, which this kernel "
            "does not have. Run the notebook with the fine-tuning kernel."
        ) from e

    print(f"  Loading with Unsloth FastLanguageModel from: {model_path}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(model_path),
        dtype=None,
        load_in_4bit=True,
        device_map=device_map,
    )
    print(f"  ✓ Model loaded with Unsloth (ready for QLoRA fine-tuning)")

    return model, tokenizer


# The fields of a fine-tune's catalogue entry, the same as a platform entry's
CATALOG_FIELDS = (
    "id", "name", "params_b", "active_params_b", "quantization", "context_length",
    "description", "server_type", "task", "reasoning_format", "tool_use",
    "stop_tokens", "license", "gated", "serving_name", "is_finetuned",
)


def _check_catalog_entry(entry: dict) -> None:
    """Refuse an entry that is incomplete or names a serving path other than vLLM."""
    missing = [field for field in CATALOG_FIELDS if field not in entry]
    if missing:
        raise ValueError(f"catalog_entry is missing: {', '.join(missing)}")
    # A fine-tune is published as a merged 16-bit checkpoint served by vLLM
    required = {
        "server_type": ["vllm"],
        "quantization": "BF16",
        "task": "text-generation",
        "is_finetuned": True,
        "serving_name": entry["id"],
    }
    wrong = {field: entry[field] for field, value in required.items() if entry[field] != value}
    if wrong:
        raise ValueError(f"catalog_entry has {wrong}; a fine-tune needs {required}")


def _mlflow_client():
    """An MLflow client with a fresh bearer token; tokens are short-lived."""
    import mlflow

    config = get_mlflow_config()
    os.environ["MLFLOW_TRACKING_TOKEN"] = get_mlflow_token()
    mlflow.set_tracking_uri(config["tracking_uri"])
    return mlflow.MlflowClient()


def _merge_to_staging(model, tokenizer, name: str, run_id: str) -> Path:
    """Write the merged 16-bit checkpoint of this run to the staging folder.

    A folder left by another run, or by a merge that did not finish, is
    removed, so the checkpoint uploaded is always the one of `run_id`.
    """
    staging_dir = STAGING_PATH / name
    stamp = staging_dir / ".run_id"
    if staging_dir.exists() and (not stamp.exists() or stamp.read_text().strip() != run_id):
        print(f"Staging holds another run; removing {staging_dir}")
        shutil.rmtree(staging_dir)
    if (staging_dir / "config.json").exists():
        print(f"Merged checkpoint already in staging: {staging_dir}")
        return staging_dir
    STAGING_PATH.mkdir(parents=True, exist_ok=True)
    print(f"Merging the adapter into the base weights: {staging_dir}")
    model.save_pretrained_merged(str(staging_dir), tokenizer, save_method="merged_16bit")
    stamp.write_text(run_id)
    return staging_dir


# MLflow serves the artifacts (mlflow-artifacts:/...) from this bucket and
# folder of the JuiceFS S3 gateway: mlflow-artifacts:/<x> is s3://mlflow/artifacts/<x>.
ARTIFACTS_URI = "mlflow-artifacts:/"
ARTIFACTS_BUCKET = "mlflow"
ARTIFACTS_FOLDER = "artifacts"


def _upload_checkpoint(staging_dir: Path, artifact_uri: str) -> str:
    """Upload the checkpoint to the run's model folder, straight to the S3
    gateway: a multi-GB checkpoint does not go through the MLflow server.
    Returns the folder's MLflow URI."""
    import boto3
    from boto3.s3.transfer import TransferConfig
    from botocore.config import Config as BotoConfig
    from kubernetes import client as k8s_client, config as k8s_config

    if not artifact_uri.startswith(ARTIFACTS_URI) or artifact_uri.startswith(ARTIFACTS_URI + "/"):
        raise RuntimeError(f"the run's artifacts are at {artifact_uri}, not under {ARTIFACTS_URI}")
    folder = f"{artifact_uri[len(ARTIFACTS_URI):]}/model"
    bucket, prefix = ARTIFACTS_BUCKET, f"{ARTIFACTS_FOLDER}/{folder}"

    # The S3 gateway credentials, read with the notebook pod's service account
    k8s_config.load_incluster_config()
    secret = k8s_client.CoreV1Api().read_namespaced_secret("mlflow-s3-secret", "mlflow")
    creds = {key: base64.b64decode(value).decode() for key, value in secret.data.items()}
    s3 = boto3.client(
        "s3",
        endpoint_url=creds["S3_ENDPOINT_URL"],
        aws_access_key_id=creds["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=creds["AWS_SECRET_ACCESS_KEY"],
        # The JuiceFS gateway ignores the region; boto3 needs one to sign requests
        region_name="us-east-1",
        # No checksums or payload signing: both read each file through the
        # JuiceFS mount before sending it, which fails on multi-GB weights
        config=BotoConfig(request_checksum_calculation="when_required",
                          s3={"payload_signing_enabled": False}),
    )
    transfer = TransferConfig(multipart_threshold=64 * 2**20,
                              multipart_chunksize=64 * 2**20, max_concurrency=4)

    files = sorted(p for p in staging_dir.rglob("*") if p.is_file() and p.name != ".run_id")
    print(f"Uploading {len(files)} files to s3://{bucket}/{prefix}")
    for path in files:
        size_gb = path.stat().st_size / 2**30
        if size_gb > 0.06:
            print(f"  {path.name} ({size_gb:.1f} GB)...")
        s3.upload_file(str(path), bucket, f"{prefix}/{path.relative_to(staging_dir)}", Config=transfer)
    print("Upload complete")
    return f"{ARTIFACTS_URI}{folder}"


def _publish_through_control(entry: dict) -> dict:
    """Ask thinkube-control to publish the model: it writes the entry to
    models.json of <GitHub user>/<GitHub user>-metadata, records the weights
    as in place and reads the catalogue again, so the gateway lists the model.
    The notebook server has its address and API token from service discovery."""
    missing = [name for name in ("THINKUBE_CONTROL_URL", "THINKUBE_API_TOKEN") if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            f"{', '.join(missing)} missing from the environment; the notebook server sets them "
            "from service discovery. Restart it if they are absent."
        )
    response = requests.post(
        f"{os.environ['THINKUBE_CONTROL_URL']}/api/v1/models/finetuned",
        json={"catalog_entry": entry},
        headers={"Authorization": f"Bearer {os.environ['THINKUBE_API_TOKEN']}"},
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"thinkube-control did not publish {entry['id']}: {response.status_code} {response.text}")
    return response.json()


def register_finetuned_model(model, tokenizer, catalog_entry: dict, run_id: str) -> str:
    """Publish a LoRA fine-tune so the LLM Gateway can load it on vLLM.

    Steps:
    1. Merge the adapter into the base weights and write a 16-bit Hugging Face
       checkpoint to the staging folder.
    2. Upload it to the model folder of the training run `run_id`, straight to
       the S3 gateway that holds MLflow's artifacts.
    3. Register a model version linked to that run, so the model can be traced
       back to the experiment that produced it.
    4. Ask thinkube-control to publish it: Control writes `catalog_entry` to
       models.json in the private repository <GitHub user>/<GitHub user>-metadata
       with its own GitHub token, records the weights as in place, and reads the
       catalogue again, so the gateway lists the model at once.

    Args:
        model: The Unsloth model with its trained LoRA adapter.
        tokenizer: Its tokenizer.
        catalog_entry: The model's catalogue entry, with every field in
            CATALOG_FIELDS; server_type ["vllm"], quantization "BF16" and
            is_finetuned true.
        run_id: The MLflow run of the training.

    Returns:
        The model's state in the gateway, normally "deployable".
    """
    from mlflow.exceptions import RestException

    _check_catalog_entry(catalog_entry)
    name = catalog_entry["id"]
    registered_name = name.replace("/", "-")

    client = _mlflow_client()
    artifact_uri = client.get_run(run_id).info.artifact_uri
    staging_dir = _merge_to_staging(model, tokenizer, name, run_id)
    source = _upload_checkpoint(staging_dir, artifact_uri)

    # A long upload can outlive the token that started it
    client = _mlflow_client()
    try:
        client.create_registered_model(registered_name)
    except RestException as e:
        if e.error_code != "RESOURCE_ALREADY_EXISTS":
            raise
    version = client.create_model_version(name=registered_name, source=source, run_id=run_id)
    print(f"Registered {registered_name} version {version.version}, linked to run {run_id}")

    published = _publish_through_control(catalog_entry)
    if published["state"] is None:
        raise RuntimeError(f"thinkube-control wrote {name} to {published['repository']}, but the gateway does not list it")
    print(f"{name}: {published['state']}, catalogue entry in {published['repository']}/models.json")
    return published["state"]
