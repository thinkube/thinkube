# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
API routes for Ansible playbook execution
Demonstrates the reusable pattern for executing various playbooks
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging

from ..services.ansible_executor import ansible_executor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])


@router.post("/microk8s-setup")
async def setup_microk8s(request: Dict[str, Any]):
    """Set up MicroK8s cluster using Ansible playbook"""
    servers = request.get("servers", [])
    username = request.get("username", "thinkube")
    password = request.get("password")
    
    # Define playbook path for MicroK8s setup
    playbook_path = "ansible/20_lxd_setup/20_deploy_microk8s.yaml"
    
    # Set up environment variables for Ansible
    environment = {}
    if password:
        environment["ANSIBLE_SUDO_PASS"] = password
    
    # Execute the playbook using the reusable service
    result = await ansible_executor.execute_playbook(
        playbook_path=playbook_path,
        environment=environment,
        timeout=600  # 10 minutes for MicroK8s setup
    )
    
    return ansible_executor.format_result_for_api(result)


@router.post("/keycloak-deploy")
async def deploy_keycloak(request: Dict[str, Any]):
    """Deploy Keycloak using Ansible playbook"""
    admin_username = request.get("admin_username", "tkadmin")
    admin_password = request.get("admin_password")
    domain_name = request.get("domain_name")
    
    if not admin_password:
        return {
            "status": "error",
            "message": "Admin password is required",
            "details": "Please provide admin_password in the request"
        }
    
    # Define playbook path for Keycloak deployment
    playbook_path = "ansible/40_thinkube/core/keycloak/10_deploy.yaml"
    
    # Set up extra variables and environment
    extra_vars = {
        "admin_username": admin_username,
        "admin_password": admin_password
    }
    
    if domain_name:
        extra_vars["domain_name"] = domain_name
    
    # Execute the playbook using the reusable service
    result = await ansible_executor.execute_playbook(
        playbook_path=playbook_path,
        extra_vars=extra_vars,
        timeout=300  # 5 minutes for Keycloak deployment
    )
    
    return ansible_executor.format_result_for_api(result)


@router.post("/harbor-deploy")
async def deploy_harbor(request: Dict[str, Any]):
    """Deploy Harbor registry using Ansible playbook"""
    admin_username = request.get("admin_username", "tkadmin")
    admin_password = request.get("admin_password")
    domain_name = request.get("domain_name")
    
    if not admin_password:
        return {
            "status": "error",
            "message": "Admin password is required",
            "details": "Please provide admin_password in the request"
        }
    
    # Define playbook path for Harbor deployment
    playbook_path = "ansible/40_thinkube/core/harbor/10_deploy.yaml"
    
    # Set up extra variables
    extra_vars = {
        "admin_username": admin_username,
        "admin_password": admin_password
    }
    
    if domain_name:
        extra_vars["domain_name"] = domain_name
    
    # Execute the playbook using the reusable service
    result = await ansible_executor.execute_playbook(
        playbook_path=playbook_path,
        extra_vars=extra_vars,
        timeout=600  # 10 minutes for Harbor deployment
    )
    
    return ansible_executor.format_result_for_api(result)


@router.post("/test-playbook")
async def test_playbook(request: Dict[str, Any]):
    """Test a specific playbook by path"""
    playbook_path = request.get("playbook_path")
    extra_vars = request.get("extra_vars", {})
    environment = request.get("environment", {})
    timeout = request.get("timeout", 300)
    
    if not playbook_path:
        return {
            "status": "error",
            "message": "Playbook path is required",
            "details": "Please provide playbook_path in the request"
        }
    
    # Execute the playbook using the reusable service
    result = await ansible_executor.execute_playbook(
        playbook_path=playbook_path,
        extra_vars=extra_vars if extra_vars else None,
        environment=environment if environment else None,
        timeout=timeout
    )
    
    return ansible_executor.format_result_for_api(result)


@router.get("/status")
async def get_playbook_status():
    """Get the current status of playbook execution"""
    return {
        "is_executing": ansible_executor.thinkube_root.exists(),  # Simple check
        "ansible_script_available": ansible_executor.ansible_script.exists(),
        "thinkube_root": str(ansible_executor.thinkube_root)
    }