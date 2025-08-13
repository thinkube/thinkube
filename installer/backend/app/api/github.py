# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
GitHub API endpoints for token verification
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
import httpx
import asyncio

router = APIRouter(prefix="/api", tags=["github"])

@router.post("/verify-github")
async def verify_github_token(data: Dict[str, str]):
    """Verify GitHub personal access token has required permissions"""
    token = data.get("token", "").strip()
    
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token is required")
    
    try:
        # Create async HTTP client
        async with httpx.AsyncClient() as client:
            # Test token by getting user info
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                user_data = response.json()
                username = user_data.get("login", "Unknown")
                
                # Check token scopes from response headers
                scopes = response.headers.get("X-OAuth-Scopes", "").split(", ")
                required_scopes = {"repo", "workflow", "write:packages"}
                has_required_scopes = all(
                    any(scope.startswith(req.split(":")[0]) for scope in scopes)
                    for req in required_scopes
                )
                
                if has_required_scopes:
                    return {
                        "valid": True,
                        "username": username,
                        "message": f"Token verified for user: {username}"
                    }
                else:
                    missing_scopes = required_scopes - set(scopes)
                    return {
                        "valid": False,
                        "message": f"Token missing required scopes: {', '.join(missing_scopes)}"
                    }
                    
            elif response.status_code == 401:
                return {
                    "valid": False,
                    "message": "Invalid or expired GitHub token"
                }
            else:
                return {
                    "valid": False,
                    "message": f"GitHub API error: {response.status_code}"
                }
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="GitHub API request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify token: {str(e)}")