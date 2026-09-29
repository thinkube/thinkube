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
import json
import os
import shutil
import time
import uuid
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
        verify=False,
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
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    # Try multiple possible mount points for different environments:
    # - JupyterHub: /home/jovyan/thinkube/mlflow/artifacts/...
    # - TensorRT-LLM pods: /mlflow-models/artifacts/...
    possible_base_paths = [
        Path('/home/jovyan/thinkube/mlflow'),  # JupyterHub mount
        Path('/mlflow-models'),                 # GPU pod mount
        Path.home() / 'thinkube' / 'mlflow',    # Generic home-based path
    ]

    model_path = None
    for base_path in possible_base_paths:
        candidate = base_path / 'artifacts' / experiment_id / run_id / 'artifacts' / 'model'
        if candidate.exists():
            model_path = candidate
            break

    if model_path is None:
        tried_paths = [str(p / 'artifacts' / experiment_id / run_id / 'artifacts' / 'model')
                       for p in possible_base_paths]
        raise FileNotFoundError(
            f"Model not found. Tried paths:\n" +
            "\n".join(f"  - {p}" for p in tried_paths) +
            f"\nThe model may not have been mirrored correctly."
        )

    print(f"  Model path: {model_path}")

    # Load with Unsloth for efficient fine-tuning
    # Unsloth handles MXFP4 models internally - it converts MXFP4 to NF4 for training
    # when load_in_4bit=True. This is their "magic" for gpt-oss models.
    try:
        from unsloth import FastLanguageModel

        print(f"  Loading with Unsloth FastLanguageModel from: {model_path}")
        print(f"  Using load_in_4bit=True (Unsloth handles MXFP4→NF4 conversion)")

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(model_path),
            dtype=None,
            load_in_4bit=True,  # Unsloth converts MXFP4 to trainable NF4 internally
            device_map=device_map,
        )
        print(f"  ✓ Model loaded with Unsloth (ready for QLoRA fine-tuning)")

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


def _upload_checkpoint(staging_dir: Path, artifact_uri: str) -> str:
    """Upload the checkpoint to the run's model folder; returns its S3 URI."""
    import boto3
    from boto3.s3.transfer import TransferConfig
    from botocore.config import Config as BotoConfig
    from kubernetes import client as k8s_client, config as k8s_config

    bucket = "mlflow"
    if not artifact_uri.startswith(f"s3://{bucket}/"):
        raise RuntimeError(f"the run's artifacts are at {artifact_uri}, outside the s3://{bucket} bucket")
    prefix = f"{artifact_uri[len(f's3://{bucket}/'):]}/model"

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
    return f"s3://{bucket}/{prefix}"


def _write_catalog_entry(entry: dict) -> str:
    """Write the entry to models.json of <GitHub user>/<GitHub user>-metadata.

    thinkube-control merges that file over the platform catalogue, so the
    entry is what makes the model known to the LLM Gateway.
    """
    github = requests.Session()
    github.headers.update({
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    })
    user = github.get("https://api.github.com/user", timeout=30)
    user.raise_for_status()
    login = user.json()["login"]
    repo = f"{login}/{login}-metadata"
    found = github.get(f"https://api.github.com/repos/{repo}", timeout=30)
    if found.status_code == 404:
        raise RuntimeError(f"{repo} does not exist; create it as a private repository on GitHub, then call this again")
    found.raise_for_status()

    contents_url = f"https://api.github.com/repos/{repo}/contents/models.json"
    current = github.get(contents_url, timeout=30)
    if current.status_code == 404:
        catalog, sha = {"models": []}, None
    else:
        current.raise_for_status()
        catalog = json.loads(base64.b64decode(current.json()["content"]))
        sha = current.json()["sha"]

    others = [m for m in catalog["models"] if m["id"] != entry["id"]]
    if others + [entry] == catalog["models"]:
        print(f"Catalogue entry already in {repo}/models.json")
        return repo
    body = {
        "message": f"Add {entry['id']} to the model catalogue",
        "content": base64.b64encode(
            (json.dumps({**catalog, "models": others + [entry]}, indent=2) + "\n").encode()
        ).decode(),
    }
    if sha:
        body["sha"] = sha
    github.put(contents_url, json=body, timeout=30).raise_for_status()
    print(f"Catalogue entry written to {repo}/models.json")
    return repo


def _record_registration(name: str) -> None:
    """Mark the model's weights as in place in thinkube-control's database."""
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname="thinkube_control",
    )
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_mirror_jobs (id, model_id, status, workflow_name, error_message)
                VALUES (%s, %s, 'succeeded', NULL, NULL)
                ON CONFLICT (model_id) DO UPDATE
                SET status = 'succeeded', error_message = NULL, updated_at = CURRENT_TIMESTAMP
                """,
                (str(uuid.uuid4()), name),
            )
    finally:
        conn.close()
    print(f"Registration recorded for {name}")


def register_finetuned_model(model, tokenizer, catalog_entry: dict, run_id: str, timeout: int = 600) -> str:
    """Publish a LoRA fine-tune so the LLM Gateway can load it on vLLM.

    Steps:
    1. Merge the adapter into the base weights and write a 16-bit Hugging Face
       checkpoint to the staging folder.
    2. Upload it to the model folder of the training run `run_id`, through the
       S3 gateway that holds MLflow's artifacts.
    3. Register a model version linked to that run, so the model can be traced
       back to the experiment that produced it.
    4. Write `catalog_entry` to models.json in the private repository
       <GitHub user>/<GitHub user>-metadata.
    5. Record the registration in thinkube-control's database, and wait until
       the gateway lists the model.

    Args:
        model: The Unsloth model with its trained LoRA adapter.
        tokenizer: Its tokenizer.
        catalog_entry: The model's catalogue entry, with every field in
            CATALOG_FIELDS; server_type ["vllm"], quantization "BF16" and
            is_finetuned true.
        run_id: The MLflow run of the training.
        timeout: Seconds to wait for the gateway to list the model.

    Returns:
        The model's state in the gateway, normally "deployable".
    """
    from mlflow.exceptions import RestException
    from tk_llm import LLMClient

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

    _write_catalog_entry(catalog_entry)
    _record_registration(name)

    # The gateway reads the catalogue again within 5 minutes
    llm = LLMClient()
    deadline = time.time() + timeout
    while True:
        listed = {m.id: m for m in llm.list_models().models}
        if name in listed:
            print(f"{name}: {listed[name].state}")
            return listed[name].state
        if time.time() > deadline:
            raise RuntimeError(f"{name} is not listed by the gateway after {timeout} seconds")
        time.sleep(15)
