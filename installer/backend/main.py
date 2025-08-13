#!/usr/bin/env python3

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
thinkube Installer Backend
FastAPI server for handling configuration and Ansible playbook execution

Refactored modular version
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

# Import our modular components
from app.api.discovery import router as discovery_router
from app.api.system import router as system_router
from app.api.playbooks import router as playbooks_router
from app.api.playbook_stream import router as playbook_stream_router
from app.api.zerotier import router as zerotier_router
from app.api.tokens import router as tokens_router
from app.api.github import router as github_router
from app.api.configuration import router as configuration_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import shared state
from app.shared import app_state, broadcast_status

# Initialize FastAPI app
app = FastAPI(
    title="thinkube Installer Backend",
    description="Backend API for thinkube installer",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(discovery_router)
app.include_router(system_router)
app.include_router(playbooks_router)
app.include_router(playbook_stream_router)
app.include_router(zerotier_router)
app.include_router(tokens_router)
app.include_router(github_router)
app.include_router(configuration_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "thinkube-installer-backend"}


@app.get("/api/health")
async def api_health():
    """API health check endpoint"""
    return {"status": "healthy", "service": "thinkube-installer-backend"}


@app.get("/api/current-user")
async def get_current_user():
    """Get the current system user"""
    try:
        import pwd
        user_info = pwd.getpwuid(os.getuid())
        return {
            "username": user_info.pw_name,
            "uid": user_info.pw_uid,
            "home": user_info.pw_dir
        }
    except:
        return {
            "username": os.environ.get('USER', 'unknown'),
            "uid": os.getuid(),
            "home": os.path.expanduser("~")
        }


# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    app_state.active_connections.append(websocket)
    logger.info(f"WebSocket client connected. Total connections: {len(app_state.active_connections)}")
    
    try:
        # Send current status immediately
        logger.info(f"Sending initial status to new WebSocket client: {app_state.installation_status}")
        await websocket.send_json(app_state.installation_status)
        
        # Keep connection alive
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        app_state.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(app_state.active_connections)}")

# Also keep the /api/ws endpoint for compatibility
@app.websocket("/api/ws")
async def api_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    app_state.active_connections.append(websocket)
    logger.info(f"API WebSocket client connected. Total connections: {len(app_state.active_connections)}")
    
    try:
        # Send current status immediately
        logger.info(f"Sending initial status to new WebSocket client: {app_state.installation_status}")
        await websocket.send_json(app_state.installation_status)
        
        # Keep connection alive
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        app_state.active_connections.remove(websocket)
        logger.info(f"API WebSocket client disconnected. Total connections: {len(app_state.active_connections)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="thinkube Installer Backend")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "main:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )