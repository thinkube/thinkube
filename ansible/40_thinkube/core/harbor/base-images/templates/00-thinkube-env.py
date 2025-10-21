# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
Thinkube Environment Loader for Jupyter Notebooks
Automatically loads environment variables from multiple sources:
1. Core service endpoints from Docker image (.thinkube_env)
2. Optional service endpoints from service discovery (.config/thinkube/service-env.sh)
3. User secrets from thinkube-control (notebooks/.secrets.env)

These variables become available via os.environ in all notebook cells.
"""

import os
import sys
from pathlib import Path


def parse_env_file(file_path):
    """Parse a shell environment file and return dict of variables."""
    env_vars = {}

    if not file_path.exists():
        return env_vars

    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Handle both 'export VAR=value' and 'VAR=value' formats
                if line.startswith('export '):
                    line = line[7:]  # Remove 'export '

                # Handle 'set -gx VAR value' (Fish shell format)
                if line.startswith('set -gx '):
                    parts = line[8:].split(None, 1)
                    if len(parts) == 2:
                        key, value = parts
                        # Remove quotes if present
                        value = value.strip('"').strip("'")
                        env_vars[key] = value
                    continue

                # Split on first '=' only
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove surrounding quotes
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    env_vars[key] = value

    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)

    return env_vars


def load_thinkube_environment():
    """Load all Thinkube environment variables into os.environ."""
    home = Path.home()
    loaded_count = 0

    # 1. Load core service endpoints from Docker image
    thinkube_env = home / '.thinkube_env'
    if thinkube_env.exists():
        env_vars = parse_env_file(thinkube_env)
        os.environ.update(env_vars)
        loaded_count += len(env_vars)
        print(f"✓ Loaded {len(env_vars)} core service endpoints from .thinkube_env")

    # 2. Load optional service endpoints from service discovery
    service_env = home / '.config' / 'thinkube' / 'service-env.sh'
    if service_env.exists():
        env_vars = parse_env_file(service_env)
        os.environ.update(env_vars)
        loaded_count += len(env_vars)
        print(f"✓ Loaded {len(env_vars)} optional service endpoints from service-env.sh")

    # 3. Load user secrets from thinkube-control
    secrets_env = home / 'thinkube' / 'notebooks' / '.secrets.env'
    if secrets_env.exists():
        env_vars = parse_env_file(secrets_env)
        os.environ.update(env_vars)
        loaded_count += len(env_vars)
        print(f"✓ Loaded {len(env_vars)} user secrets from thinkube-control")

    if loaded_count > 0:
        print(f"\n✅ Thinkube environment ready: {loaded_count} total variables loaded")
        print("   Access via: import os; os.environ['VARIABLE_NAME']")
    else:
        print("ℹ No Thinkube environment files found (this is normal on first startup)")


# Auto-load environment when kernel starts
try:
    load_thinkube_environment()
except Exception as e:
    print(f"❌ Error loading Thinkube environment: {e}", file=sys.stderr)
    print("   Notebooks will work, but service credentials may not be available", file=sys.stderr)
