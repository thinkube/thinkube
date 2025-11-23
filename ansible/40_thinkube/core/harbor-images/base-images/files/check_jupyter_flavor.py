# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
Jupyter Flavor Validation Helper

This module provides utilities to validate that notebooks are running in the
correct Jupyter environment flavor (ml-gpu, agent-dev, or fine-tuning).

Usage in notebooks:
    from check_jupyter_flavor import check_flavor, get_current_flavor

    # Check if running in required flavor (raises error if mismatch)
    check_flavor('agent-dev')

    # Or get current flavor and handle manually
    current = get_current_flavor()
    print(f"Running in {current} environment")
"""

import os
from pathlib import Path


FLAVOR_FILE = Path.home() / '.jupyter_flavor'

FLAVOR_DESCRIPTIONS = {
    'ml-gpu': 'Base ML/GPU environment (PyTorch, transformers, all service clients)',
    'agent-dev': 'Agent Development (LangChain, CrewAI, FAISS + ml-gpu)',
    'fine-tuning': 'Fine-Tuning Lab (Unsloth, QLoRA, PEFT, TRL + ml-gpu)',
}


def get_current_flavor():
    """
    Get the current Jupyter environment flavor.

    Returns:
        str: The current flavor name ('ml-gpu', 'agent-dev', or 'fine-tuning')

    Raises:
        FileNotFoundError: If flavor file doesn't exist (not in Thinkube environment)
    """
    if not FLAVOR_FILE.exists():
        raise FileNotFoundError(
            f"Jupyter flavor file not found at {FLAVOR_FILE}. "
            "Are you running in a Thinkube JupyterHub environment?"
        )

    return FLAVOR_FILE.read_text().strip()


def check_flavor(required_flavor, strict=True):
    """
    Validate that the notebook is running in the required Jupyter flavor.

    Args:
        required_flavor (str): The required flavor ('ml-gpu', 'agent-dev', or 'fine-tuning')
        strict (bool): If True, raise an error on mismatch. If False, only print a warning.

    Returns:
        bool: True if flavor matches, False otherwise

    Raises:
        EnvironmentError: If strict=True and flavor doesn't match
    """
    try:
        current_flavor = get_current_flavor()
    except FileNotFoundError as e:
        if strict:
            raise EnvironmentError(str(e)) from e
        print(f"⚠️  Warning: {e}")
        return False

    if current_flavor == required_flavor:
        print(f"✓ Running in correct environment: {required_flavor}")
        print(f"  {FLAVOR_DESCRIPTIONS.get(required_flavor, 'Unknown flavor')}")
        return True

    error_msg = (
        f"\n{'='*70}\n"
        f"❌ Environment Mismatch!\n"
        f"{'='*70}\n"
        f"This notebook requires: {required_flavor}\n"
        f"Currently running in:   {current_flavor}\n"
        f"\n"
        f"Required: {FLAVOR_DESCRIPTIONS.get(required_flavor, 'Unknown')}\n"
        f"Current:  {FLAVOR_DESCRIPTIONS.get(current_flavor, 'Unknown')}\n"
        f"\n"
        f"Please switch to the correct JupyterHub image:\n"
        f"  1. Stop this server (File → Hub Control Panel → Stop My Server)\n"
        f"  2. Select '{required_flavor}' image from the dropdown\n"
        f"  3. Start the server and reopen this notebook\n"
        f"{'='*70}\n"
    )

    if strict:
        raise EnvironmentError(error_msg)
    else:
        print(f"⚠️  Warning: {error_msg}")
        return False


def get_flavor_info():
    """
    Get information about the current Jupyter flavor and all available flavors.

    Returns:
        dict: Information about current and available flavors
    """
    try:
        current = get_current_flavor()
    except FileNotFoundError:
        current = None

    return {
        'current': current,
        'current_description': FLAVOR_DESCRIPTIONS.get(current, 'Not in Thinkube environment'),
        'available_flavors': FLAVOR_DESCRIPTIONS,
    }


if __name__ == '__main__':
    # When run as a script, display current environment info
    info = get_flavor_info()

    print("Thinkube Jupyter Environment Information")
    print("=" * 70)
    print(f"Current Flavor: {info['current'] or 'Unknown'}")
    print(f"Description:    {info['current_description']}")
    print()
    print("Available Flavors:")
    for flavor, desc in info['available_flavors'].items():
        marker = "  ← (current)" if flavor == info['current'] else ""
        print(f"  • {flavor}: {desc}{marker}")
    print("=" * 70)
