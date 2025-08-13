# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
Configuration persistence API endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["configuration"])

# Configuration file path
CONFIG_DIR = Path.home() / ".thinkube-installer"
CONFIG_FILE = CONFIG_DIR / "session-config.json"


@router.post("/api/system/save-configuration")
async def save_configuration(config: Dict[str, Any]):
    """Save all session configuration data to disk"""
    try:
        # Ensure directory exists
        CONFIG_DIR.mkdir(exist_ok=True)
        
        # Save configuration
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved configuration to {CONFIG_FILE}")
        return {"success": True, "message": "Configuration saved"}
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/system/load-configuration")
async def load_configuration():
    """Load saved session configuration from disk"""
    try:
        if not CONFIG_FILE.exists():
            return {"exists": False, "config": None}
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Loaded configuration from {CONFIG_FILE}")
        return {"exists": True, "config": config}
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/system/clear-configuration")
async def clear_configuration():
    """Clear saved configuration"""
    try:
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
            logger.info("Cleared saved configuration")
        return {"success": True, "message": "Configuration cleared"}
    except Exception as e:
        logger.error(f"Failed to clear configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))