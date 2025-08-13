# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
Shared state and utilities for the installer backend
"""
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Global state - shared across all modules
class AppState:
    installation_status = {
        "phase": "idle",
        "progress": 0,
        "current_task": "",
        "logs": [],
        "errors": []
    }
    active_connections: List[WebSocket] = []

# Create singleton instance
app_state = AppState()

async def broadcast_status(status):
    """Broadcast status update to all connected clients"""
    logger.info(f"Broadcasting status to {len(app_state.active_connections)} clients: phase={status.get('phase')}, progress={status.get('progress')}")
    if app_state.active_connections:
        disconnected = []
        for connection in app_state.active_connections:
            try:
                await connection.send_json(status)
                logger.debug(f"Status sent successfully to a client")
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            app_state.active_connections.remove(connection)
            logger.info(f"Removed disconnected client. Remaining: {len(app_state.active_connections)}")