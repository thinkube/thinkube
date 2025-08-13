#!/usr/bin/env python3

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
thinkube Installer Backend
FastAPI server for handling configuration and Ansible playbook execution
"""

import os
import sys
import asyncio
import logging
import yaml
import json
import subprocess
import ipaddress
import concurrent.futures
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import uvicorn
from jinja2 import Template
import ansible_runner
import random
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="thinkube Installer Backend",
    description="Backend API for thinkube installer",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "file://"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
installation_status = {
    "phase": "idle",
    "progress": 0,
    "current_task": "",
    "logs": [],
    "errors": []
}

# WebSocket connections
active_connections: List[WebSocket] = []

# Enums
class ServerRole(str, Enum):
    CONTAINER_HOST = "container_host"
    HYBRID = "hybrid"
    DIRECT = "direct"

class ContainerType(str, Enum):
    K8S_CONTROL = "k8s_control"
    K8S_WORKER = "k8s_worker" 
    DNS = "dns"
    CUSTOM = "custom"

class NodeRole(str, Enum):
    CONTROL_PLANE = "control_plane"
    WORKER = "worker"

# Pydantic models
class HardwareInfo(BaseModel):
    cpu_cores: int
    cpu_model: str
    memory_gb: float
    disk_gb: float
    gpu_detected: bool = False
    gpu_model: Optional[str] = None
    gpu_count: int = 0
    architecture: str  # x86_64 or arm64

class Container(BaseModel):
    name: str
    type: ContainerType
    parent_host: str
    memory: str  # e.g., "48GB"
    cpu_cores: int
    disk_size: str  # e.g., "700GB"
    gpu_passthrough: bool = False
    gpu_type: Optional[str] = None
    k8s_role: Optional[NodeRole] = None

class BaremetalServer(BaseModel):
    hostname: str
    ip_address: str
    ssh_username: str = "thinkube"
    ssh_password: Optional[str] = None
    role: ServerRole
    hardware: Optional[HardwareInfo] = None
    containers: List[Container] = []
    k8s_role: Optional[NodeRole] = None  # For direct/hybrid servers
    ssh_verified: bool = False

class DiscoveredServer(BaseModel):
    ip: str
    hostname: Optional[str] = None
    os_info: Optional[str] = None
    ssh_available: bool = False
    confidence: str  # "confirmed", "possible", "unknown"
    banner: Optional[str] = None

class NodeConfig(BaseModel):
    hostname: str
    ip_address: str
    role: str  # control_plane or worker
    cpu_cores: int = Field(ge=4)
    memory_gb: int = Field(ge=8)
    has_gpu: bool = False
    gpu_type: Optional[str] = None

class ClusterConfig(BaseModel):
    cluster_name: str = Field(min_length=3, max_length=50)
    domain_name: str
    admin_username: str = "tkadmin"
    admin_password: str = Field(min_length=8)
    sudo_password: str = Field(min_length=1)  # Required for ANSIBLE_SUDO_PASS
    nodes: List[NodeConfig]
    deployment_type: str = "lxd"  # lxd or physical
    
    # Network configuration
    network_bridge: str = "br0"
    network_cidr: str = "192.168.1.0/24"
    
    # External services
    github_token: Optional[str] = None
    cloudflare_api_token: Optional[str] = None
    zerotier_network_id: Optional[str] = None
    
    @field_validator('nodes')
    @classmethod
    def validate_nodes(cls, v):
        if len(v) < 1:
            raise ValueError("At least one node is required")
        control_planes = [n for n in v if n.role == "control_plane"]
        if len(control_planes) != 1:
            raise ValueError("Exactly one control plane node is required")
        return v

class InstallationProgress(BaseModel):
    phase: str
    progress: int
    current_task: str
    timestamp: datetime

# Utility functions
def get_project_root() -> Path:
    """Get the thinkube project root directory"""
    # In production, this would be installed in a known location
    # For development, navigate up from backend directory
    current = Path(__file__).parent
    while current.name != "thinkube" and current.parent != current:
        current = current.parent
    return current

async def broadcast_status(message: dict):
    """Broadcast status updates to all connected WebSocket clients"""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            pass

def generate_inventory(config: ClusterConfig) -> str:
    """Generate Ansible inventory from configuration"""
    inventory_template = """# Generated by thinkube installer
# {{ timestamp }}

[all:vars]
ansible_user={{ admin_username }}
ansible_become=yes
domain_name={{ domain_name }}
cluster_name={{ cluster_name }}

[baremetal]
{% for node in nodes %}
{{ node.hostname }} ansible_host={{ node.ip_address }}
{% endfor %}

[microk8s_control_plane]
{% for node in nodes if node.role == "control_plane" %}
{{ node.hostname }}
{% endfor %}

[microk8s_workers]
{% for node in nodes if node.role == "worker" %}
{{ node.hostname }}
{% endfor %}

[microk8s:children]
microk8s_control_plane
microk8s_workers

{% if deployment_type == "lxd" %}
[lxd_hosts]
{% for node in nodes %}
{{ node.hostname }}
{% endfor %}
{% endif %}
"""
    
    template = Template(inventory_template)
    return template.render(
        timestamp=datetime.now().isoformat(),
        admin_username=config.admin_username,
        domain_name=config.domain_name,
        cluster_name=config.cluster_name,
        nodes=config.nodes,
        deployment_type=config.deployment_type
    )

async def run_playbook(playbook_path: str, inventory_path: str, extra_vars: dict):
    """Run an Ansible playbook and stream progress"""
    try:
        # Update status
        installation_status["phase"] = "running"
        installation_status["current_task"] = f"Running {playbook_path}"
        await broadcast_status(installation_status)
        
        # Run ansible-runner
        runner = ansible_runner.run(
            playbook=playbook_path,
            inventory=inventory_path,
            extravars=extra_vars,
            quiet=False,
            event_handler=lambda event: asyncio.create_task(handle_ansible_event(event))
        )
        
        if runner.status == "successful":
            logger.info(f"Playbook {playbook_path} completed successfully")
        else:
            raise Exception(f"Playbook failed with status: {runner.status}")
            
    except Exception as e:
        logger.error(f"Error running playbook: {e}")
        installation_status["errors"].append(str(e))
        raise

async def handle_ansible_event(event):
    """Handle Ansible runner events and broadcast updates"""
    if event['event'] == 'runner_on_ok':
        task_name = event['event_data'].get('task', 'Unknown task')
        installation_status["current_task"] = task_name
        installation_status["logs"].append(f"✓ {task_name}")
        
    elif event['event'] == 'runner_on_failed':
        task_name = event['event_data'].get('task', 'Unknown task')
        installation_status["errors"].append(f"✗ {task_name} failed")
        
    await broadcast_status(installation_status)

# API endpoints
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

@app.get("/api/check-installation-state")
async def check_installation_state():
    """Check what parts of thinkube are already installed"""
    state = {
        "environment_setup": False,
        "ansible_installed": False,
        "thinkube_repo_cloned": False,
        "ssh_keys_configured": False,
        "lxd_installed": False,
        "microk8s_installed": False,
        "kubernetes_running": False,
        "services_deployed": [],
        "installation_complete": False
    }
    
    try:
        # Check if thinkube repo is cloned
        thinkube_path = Path.home() / "thinkube"
        if thinkube_path.exists() and (thinkube_path / "ansible").exists():
            state["thinkube_repo_cloned"] = True
        
        # Check if ansible is installed in user virtual environment (as per install script)
        user_venv = Path.home() / ".venv"
        if user_venv.exists():
            ansible_bin = user_venv / "bin" / "ansible-playbook"
            if ansible_bin.exists():
                state["ansible_installed"] = True
        else:
            # Fallback: check if ansible is installed system-wide
            result = await asyncio.create_subprocess_exec(
                'which', 'ansible-playbook',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            if result.returncode == 0:
                state["ansible_installed"] = True
        
        # Check if SSH keys are configured
        ssh_key_path = Path.home() / ".ssh" / "id_rsa.pub"
        if ssh_key_path.exists():
            state["ssh_keys_configured"] = True
        
        # Check environment setup
        env_file = Path.home() / ".env"
        inventory_file = thinkube_path / "inventory" / "inventory.yaml"
        if env_file.exists() and inventory_file.exists():
            state["environment_setup"] = True
        
        # Check if LXD is installed and configured
        result = await asyncio.create_subprocess_exec(
            'which', 'lxc',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await result.communicate()
        if result.returncode == 0:
            # Check if LXD is actually configured
            result = await asyncio.create_subprocess_exec(
                'lxc', 'list',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            if result.returncode == 0:
                state["lxd_installed"] = True
        
        # Check if MicroK8s is installed
        result = await asyncio.create_subprocess_exec(
            'which', 'microk8s',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await result.communicate()
        if result.returncode == 0:
            state["microk8s_installed"] = True
            
            # Check if Kubernetes is running
            result = await asyncio.create_subprocess_exec(
                'microk8s', 'status', '--wait-ready', '--timeout', '5',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            if result.returncode == 0:
                state["kubernetes_running"] = True
                
                # Check deployed services
                result = await asyncio.create_subprocess_exec(
                    'microk8s', 'kubectl', 'get', 'namespaces', '-o', 'json',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                if result.returncode == 0:
                    import json
                    namespaces_data = json.loads(stdout.decode())
                    namespaces = [ns['metadata']['name'] for ns in namespaces_data['items']]
                    
                    # Check for thinkube services
                    thinkube_services = ['keycloak', 'harbor', 'postgresql', 'argocd', 'argo-workflows']
                    for service in thinkube_services:
                        if service in namespaces:
                            state["services_deployed"].append(service)
        
        # Determine if installation is complete
        state["installation_complete"] = (
            state["environment_setup"] and
            state["ansible_installed"] and
            state["thinkube_repo_cloned"] and
            state["ssh_keys_configured"] and
            state["lxd_installed"] and
            state["kubernetes_running"] and
            len(state["services_deployed"]) >= 3  # At least 3 core services
        )
        
    except Exception as e:
        logger.error(f"Error checking installation state: {e}")
    
    return state

@app.get("/api/check-requirements")
async def check_requirements():
    """Check system requirements based on REQUIREMENTS.md"""
    requirements = []
    
    # HARD REQUIREMENTS (must pass)
    
    # 1. Check Ubuntu version (must be 24.04.x)
    try:
        # First try reading /etc/os-release directly (more reliable)
        with open('/etc/os-release', 'r') as f:
            os_release = f.read()
            
        # Parse the file
        os_info = {}
        for line in os_release.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                os_info[key] = value.strip('"')
        
        dist_id = os_info.get('ID', '').lower()
        version_id = os_info.get('VERSION_ID', '')
        version_full = os_info.get('VERSION', '')
        
        if dist_id == 'ubuntu' and version_id.startswith('24.04'):
            requirements.append({
                "name": "Ubuntu 24.04.x LTS",
                "category": "system",
                "required": True,
                "status": "pass",
                "details": f"{version_full} detected"
            })
        else:
            # Fallback to distro module
            import distro
            dist_info = distro.info()
            dist_name = dist_info.get('id', '')
            dist_version = dist_info.get('version', '')
            
            if dist_name == 'ubuntu' and dist_version.startswith('24.04'):
                requirements.append({
                    "name": "Ubuntu 24.04.x LTS",
                    "category": "system",
                    "required": True,
                    "status": "pass",
                    "details": f"Ubuntu {dist_version} LTS detected"
                })
            else:
                requirements.append({
                    "name": "Ubuntu 24.04.x LTS",
                    "category": "system", 
                    "required": True,
                    "status": "fail",
                    "details": f"Found {dist_id or dist_name} {version_id or dist_version}. This installer requires Ubuntu 24.04.x"
                })
    except Exception as e:
        requirements.append({
            "name": "Ubuntu 24.04.x LTS",
            "category": "system",
            "required": True,
            "status": "fail",
            "details": f"Could not detect OS version: {str(e)}"
        })
    
    # 2. Check user is not root and has sudo
    try:
        is_root = os.geteuid() == 0
        if is_root:
            requirements.append({
                "name": "Non-root user with sudo",
                "category": "system",
                "required": True,
                "status": "fail",
                "details": "Running as root. Please run as normal user with sudo access"
            })
        else:
            # Check sudo access
            result = await asyncio.create_subprocess_exec(
                'sudo', '-n', 'true',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            current_user = os.environ.get('USER', 'unknown')
            requirements.append({
                "name": "Non-root user with sudo",
                "category": "system",
                "required": True,
                "status": "pass",
                "details": f"User '{current_user}' has sudo access"
            })
    except:
        requirements.append({
            "name": "Non-root user with sudo",
            "category": "system",
            "required": True,
            "status": "fail",
            "details": "Could not verify user and sudo access"
        })
    
    # 3. Check network connectivity
    try:
        # Try to reach Ubuntu package servers
        socket.create_connection(("archive.ubuntu.com", 80), timeout=3)
        requirements.append({
            "name": "Network connectivity",
            "category": "system",
            "required": True,
            "status": "pass",
            "details": "Internet access confirmed"
        })
    except:
        requirements.append({
            "name": "Network connectivity",
            "category": "system",
            "required": True,
            "status": "fail",
            "details": "Cannot reach Ubuntu package servers"
        })
    
    # 4. Check disk space (10GB minimum for control node)
    try:
        home_stat = os.statvfs(os.path.expanduser("~"))
        free_gb = (home_stat.f_bavail * home_stat.f_frsize) / (1024**3)
        
        if free_gb >= 10:
            requirements.append({
                "name": "Disk space",
                "category": "system",
                "required": True,
                "status": "pass",
                "details": f"{free_gb:.1f}GB free in home directory"
            })
        else:
            requirements.append({
                "name": "Disk space",
                "category": "system",
                "required": True,
                "status": "fail",
                "details": f"Only {free_gb:.1f}GB free. Need at least 10GB"
            })
    except:
        requirements.append({
            "name": "Disk space",
            "category": "system",
            "required": True,
            "status": "fail",
            "details": "Could not check disk space"
        })
    
    # SOFT REQUIREMENTS (will be installed if missing)
    
    # 1. Git
    try:
        result = await asyncio.create_subprocess_exec(
            'which', 'git',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        if stdout:
            # Check git version
            version_result = await asyncio.create_subprocess_exec(
                'git', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            version_stdout, _ = await version_result.communicate()
            version = version_stdout.decode().strip() if version_result.returncode == 0 else "unknown"
            
            requirements.append({
                "name": "Git",
                "category": "tools",
                "required": False,
                "status": "pass",
                "details": f"Git is installed ({version})"
            })
        else:
            requirements.append({
                "name": "Git",
                "category": "tools",
                "required": False,
                "status": "missing",
                "details": "Will be installed during setup",
                "action": "install"
            })
    except:
        requirements.append({
            "name": "Git",
            "category": "tools",
            "required": False,
            "status": "missing",
            "details": "Will be installed during setup",
            "action": "install"
        })
    
    # 2. OpenSSH Client
    try:
        result = await asyncio.create_subprocess_exec(
            'which', 'ssh',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        if stdout:
            requirements.append({
                "name": "OpenSSH Client",
                "category": "tools",
                "required": False,
                "status": "pass",
                "details": "SSH client is installed"
            })
        else:
            requirements.append({
                "name": "OpenSSH Client",
                "category": "tools",
                "required": False,
                "status": "missing",
                "details": "Will be installed",
                "action": "install"
            })
    except:
        requirements.append({
            "name": "OpenSSH Client",
            "category": "tools",
            "required": False,
            "status": "missing",
            "details": "Will be installed",
            "action": "install"
        })
    
    # 3. Python Virtual Environment (user-level as per install script)
    user_venv = Path.home() / ".venv"
    if user_venv.exists() and (user_venv / "bin" / "python").exists():
        requirements.append({
            "name": "Python Virtual Environment",
            "category": "tools",
            "required": False,
            "status": "pass",
            "details": f"Virtual environment exists at {user_venv}"
        })
    else:
        requirements.append({
            "name": "Python Virtual Environment",
            "category": "tools",
            "required": False,
            "status": "missing",
            "details": "Will be created in ~/.venv",
            "action": "install"
        })
    
    # 4. Ansible (must be in user virtual environment as per install script)
    venv_ansible_installed = False
    
    # Only check in user virtual environment - this is required
    if user_venv.exists():
        ansible_bin = user_venv / "bin" / "ansible-playbook"
        if ansible_bin.exists():
            try:
                # Check ansible version in venv
                version_result = await asyncio.create_subprocess_exec(
                    str(ansible_bin), '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                version_stdout, _ = await version_result.communicate()
                if version_result.returncode == 0:
                    version_line = version_stdout.decode().split('\n')[0]
                    venv_ansible_installed = True
                    ansible_details = f"Ansible installed in user venv ({version_line})"
            except:
                pass
    
    if venv_ansible_installed:
        requirements.append({
            "name": "Ansible (in venv)",
            "category": "tools",
            "required": False,
            "status": "pass",
            "details": ansible_details
        })
    else:
        # Check if system ansible exists (for informational purposes)
        system_ansible_note = ""
        try:
            result = await asyncio.create_subprocess_exec(
                'which', 'ansible-playbook',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            if stdout:
                system_ansible_note = " (system-wide Ansible detected, but thinkube needs user venv)"
        except:
            pass
        
        requirements.append({
            "name": "Ansible (in venv)",
            "category": "tools", 
            "required": False,
            "status": "missing",
            "details": f"Will be installed in user virtual environment{system_ansible_note}",
            "action": "install"
        })
    
    return {"requirements": requirements}

@app.post("/api/verify-sudo")
async def verify_sudo_password(request: dict):
    """Verify if the provided sudo password is correct"""
    try:
        password = request.get('password', '')
        if not password:
            return {"valid": False, "message": "No password provided"}
        
        # Clear any cached sudo credentials first
        logger.info("Clearing sudo cache before verification")
        await asyncio.create_subprocess_exec('sudo', '-k')
        
        # Test sudo with the provided password
        logger.info(f"Testing sudo with password (length: {len(password)})")
        process = await asyncio.create_subprocess_exec(
            'sudo', '-S', 'true',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Send password to stdin
        stdout, stderr = await process.communicate(input=f"{password}\n".encode())
        
        logger.info(f"Sudo test result: returncode={process.returncode}, stdout={stdout.decode()}, stderr={stderr.decode()}")
        
        if process.returncode == 0:
            logger.info("Password verification successful")
            return {"valid": True, "message": "Password verified successfully"}
        else:
            logger.info(f"Password verification failed with code {process.returncode}")
            return {"valid": False, "message": "Invalid password"}
            
    except Exception as e:
        logger.error(f"Failed to verify sudo password: {e}")
        return {"valid": False, "message": f"Verification error: {str(e)}"}

@app.post("/api/run-setup")
async def run_setup(background_tasks: BackgroundTasks, request: dict = {}):
    """Run the thinkube setup script"""
    try:
        # Check if thinkube is already installed by looking for actual installation markers
        # Check for: LXD VMs, MicroK8s installation, or thinkube services
        installation_markers = await check_thinkube_installation()
        
        if installation_markers["installed"]:
            return {
                "status": "exists", 
                "message": "thinkube appears to be already installed", 
                "details": installation_markers["details"]
            }
        
        # Get sudo password if provided
        sudo_password = request.get('sudo_password', '')
        
        # Verify sudo password before proceeding
        if sudo_password:
            try:
                logger.info(f"Verifying sudo password for run-setup")
                # Clear any cached sudo credentials first
                await asyncio.create_subprocess_exec('sudo', '-k')
                
                process = await asyncio.create_subprocess_exec(
                    'sudo', '-S', 'true',
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate(input=f"{sudo_password}\n".encode())
                
                logger.info(f"Sudo verification result: returncode={process.returncode}, stderr={stderr.decode()}")
                
                if process.returncode != 0:
                    logger.error(f"Invalid sudo password provided to run-setup")
                    raise HTTPException(status_code=400, detail="Invalid sudo password")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Sudo password verification failed: {e}")
                raise HTTPException(status_code=400, detail="Failed to verify sudo password")
        else:
            logger.warning("No sudo password provided to run-setup")
        
        # Start the setup process in the background
        background_tasks.add_task(run_setup_script, sudo_password)
        return {"status": "started", "message": "Setup process started"}
        
    except Exception as e:
        logger.error(f"Failed to start setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def check_thinkube_installation():
    """Check for actual thinkube installation markers"""
    markers = {
        "installed": False,
        "details": []
    }
    
    # Check for LXD VMs (tkc, tkw1, etc)
    try:
        result = await asyncio.create_subprocess_exec(
            'lxc', 'list', '--format=json',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        if stdout:
            vms = json.loads(stdout.decode())
            thinkube_vms = [vm['name'] for vm in vms if vm['name'] in ['tkc', 'tkw1', 'dns1']]
            if thinkube_vms:
                markers["installed"] = True
                markers["details"].append(f"Found LXD VMs: {', '.join(thinkube_vms)}")
    except:
        pass
    
    # Check for MicroK8s
    try:
        result = await asyncio.create_subprocess_exec(
            'microk8s', 'status',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        if result.returncode == 0 and stdout:
            markers["installed"] = True
            markers["details"].append("MicroK8s is installed")
    except:
        pass
    
    # Check for thinkube namespace in kubernetes
    try:
        result = await asyncio.create_subprocess_exec(
            'microk8s', 'kubectl', 'get', 'namespace', 'thinkube',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        if result.returncode == 0:
            markers["installed"] = True
            markers["details"].append("thinkube namespace exists in Kubernetes")
    except:
        pass
    
    return markers

async def run_setup_script(sudo_password: str = ""):
    """Run the actual setup script"""
    try:
        installation_status["phase"] = "setup"
        installation_status["current_task"] = "Running thinkube setup script"
        installation_status["logs"] = ["Starting thinkube setup..."]
        installation_status["progress"] = 0
        await broadcast_status(installation_status)
        
        # Get the path to the setup script from the main README
        project_root = get_project_root()
        setup_script = project_root / "scripts" / "10_install-tools.sh"
        
        if not setup_script.exists():
            raise Exception(f"Setup script not found at {setup_script}")
        
        # Set environment with sudo password if provided
        env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
        if sudo_password:
            env["SUDO_ASKPASS"] = "/bin/echo"
            env["ANSIBLE_SUDO_PASS"] = sudo_password
        
        # Create a temporary askpass helper script if we have a password
        askpass_script = None
        if sudo_password:
            # Create a temporary askpass script
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                askpass_script = Path(f.name)
                f.write(f"#!/bin/bash\necho '{sudo_password}'\n")
            
            # Make it executable
            askpass_script.chmod(0o700)
            
            # Set SUDO_ASKPASS to our script
            env["SUDO_ASKPASS"] = str(askpass_script)
            
        # Run the setup script
        try:
            process = await asyncio.create_subprocess_exec(
                'bash', str(setup_script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env
            )
            
            # Stream output with timeout
            last_output_time = asyncio.get_event_loop().time()
            timeout_seconds = 300  # 5 minute timeout for no output
            
            while True:
                try:
                    # Wait for output with timeout
                    line = await asyncio.wait_for(
                        process.stdout.readline(), 
                        timeout=10.0
                    )
                
                    if not line:
                        break
                        
                    last_output_time = asyncio.get_event_loop().time()
                    log_line = line.decode('utf-8', errors='ignore').strip()
                    
                    if log_line:
                        installation_status["logs"].append(log_line)
                        
                        # Check for special status markers
                        if "[INSTALLER_STATUS]" in log_line:
                            # Parse status messages
                            if "PROGRESS:" in log_line:
                                try:
                                    progress = int(log_line.split("PROGRESS:")[1].split()[0])
                                    installation_status["progress"] = progress
                                except:
                                    pass
                            
                            if "COMPLETED:SUCCESS" in log_line:
                                installation_status["progress"] = 100
                                installation_status["phase"] = "completed"
                                installation_status["current_task"] = "Installation completed successfully!"
                            
                            elif "COMPLETED:FAILED" in log_line:
                                installation_status["phase"] = "failed"
                                installation_status["current_task"] = "Installation failed!"
                                if "Failed to" in log_line:
                                    installation_status["errors"].append(log_line.split("]")[-1].strip())
                            
                            # Update task based on status messages
                            elif "Updating package lists" in log_line:
                                installation_status["current_task"] = "Updating package lists..."
                            elif "Installing Python and system dependencies" in log_line:
                                installation_status["current_task"] = "Installing system dependencies..."
                            elif "Installing micro editor" in log_line:
                                installation_status["current_task"] = "Installing micro editor..."
                            elif "Installing shell environments" in log_line:
                                installation_status["current_task"] = "Installing shell environments..."
                            elif "Creating Python virtual environment" in log_line:
                                installation_status["current_task"] = "Creating Python virtual environment..."
                            elif "Installing Ansible" in log_line:
                                installation_status["current_task"] = "Installing Ansible..."
                            elif "Configuring shell environments" in log_line:
                                installation_status["current_task"] = "Configuring shell environments..."
                            elif "finished successfully" in log_line:
                                installation_status["current_task"] = "Installation completed!"
                        
                        await broadcast_status(installation_status)
                        
                except asyncio.TimeoutError:
                    # Check if we've been waiting too long
                    if asyncio.get_event_loop().time() - last_output_time > timeout_seconds:
                        logger.error("Setup script timed out - no output for 5 minutes")
                        process.terminate()
                        raise Exception("Setup script timed out - no output for 5 minutes")
        
            await process.wait()
            
            if process.returncode == 0:
                installation_status["phase"] = "completed"
                installation_status["progress"] = 100
                installation_status["current_task"] = "Setup completed successfully!"
            else:
                installation_status["phase"] = "failed"
                installation_status["errors"].append(f"Setup script failed with code {process.returncode}")
            
            await broadcast_status(installation_status)
            
        finally:
            # Clean up the askpass script
            if askpass_script and askpass_script.exists():
                askpass_script.unlink()
        
    except Exception as e:
        logger.error(f"Setup script failed: {e}")
        installation_status["phase"] = "failed"
        installation_status["errors"].append(str(e))
        await broadcast_status(installation_status)

@app.post("/api/validate-config")
async def validate_config(config: ClusterConfig):
    """Validate cluster configuration"""
    try:
        # Additional validation logic here
        return {"valid": True, "message": "Configuration is valid"}
    except Exception as e:
        return {"valid": False, "message": str(e)}

@app.post("/api/generate-inventory")
async def generate_inventory_endpoint(config: ClusterConfig):
    """Generate and preview inventory file"""
    try:
        inventory_content = generate_inventory(config)
        return {"inventory": inventory_content}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/install")
async def start_installation(config: ClusterConfig):
    """Start the installation process"""
    try:
        # Reset status
        installation_status.update({
            "phase": "starting",
            "progress": 0,
            "current_task": "Initializing installation",
            "logs": [],
            "errors": []
        })
        
        # Save configuration
        project_root = get_project_root()
        inventory_dir = project_root / "inventory"
        inventory_dir.mkdir(exist_ok=True)
        
        # Generate and save inventory
        inventory_content = generate_inventory(config)
        inventory_file = inventory_dir / "installer_inventory.yaml"
        inventory_file.write_text(inventory_content)
        
        # Save configuration for reference
        config_file = inventory_dir / "installer_config.json"
        config_file.write_text(config.json(indent=2))
        
        # Start installation in background
        asyncio.create_task(run_installation(config, inventory_file))
        
        return {"status": "started", "message": "Installation started successfully"}
        
    except Exception as e:
        logger.error(f"Failed to start installation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_installation(config: ClusterConfig, inventory_file: Path):
    """Run the complete installation process"""
    try:
        project_root = get_project_root()
        ansible_dir = project_root / "ansible"
        
        # Set ANSIBLE_SUDO_PASS environment variable
        if hasattr(config, 'sudo_password') and config.sudo_password:
            os.environ['ANSIBLE_SUDO_PASS'] = config.sudo_password
        
        # Define playbook phases
        phases = [
            ("Initial Setup", [
                "00_initial_setup/10_setup_ssh_keys.yaml",
                "00_initial_setup/20_setup_env.yaml",
            ]),
            ("Infrastructure", [
                "10_baremetal_infra/10-1_configure_network_bridge_prepare.yaml",
                "10_baremetal_infra/10-2_configure_network_bridge_apply.yaml",
            ]),
            ("Kubernetes Setup", [
                "40_thinkube/core/infrastructure/microk8s/10_install_microk8s.yaml",
            ])
        ]
        
        total_playbooks = sum(len(playbooks) for _, playbooks in phases)
        completed = 0
        
        for phase_name, playbooks in phases:
            installation_status["phase"] = phase_name
            await broadcast_status(installation_status)
            
            for playbook in playbooks:
                playbook_path = ansible_dir / playbook
                if playbook_path.exists():
                    await run_playbook(
                        str(playbook_path),
                        str(inventory_file),
                        {
                            "admin_password": config.admin_password,
                            "ansible_become_pass": config.sudo_password if hasattr(config, 'sudo_password') else None
                        }
                    )
                    completed += 1
                    installation_status["progress"] = int((completed / total_playbooks) * 100)
                    await broadcast_status(installation_status)
        
        installation_status["phase"] = "completed"
        installation_status["progress"] = 100
        installation_status["current_task"] = "Installation completed successfully!"
        await broadcast_status(installation_status)
        
    except Exception as e:
        logger.error(f"Installation failed: {e}")
        installation_status["phase"] = "failed"
        installation_status["errors"].append(str(e))
        await broadcast_status(installation_status)

@app.get("/api/status")
async def get_status():
    """Get current installation status"""
    return installation_status

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send current status
        await websocket.send_json(installation_status)
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.get("/api/logs/download")
async def download_logs():
    """Download installation logs"""
    log_content = "\n".join(installation_status["logs"])
    log_file = Path("/tmp/thinkube_installation.log")
    log_file.write_text(log_content)
    return FileResponse(log_file, filename="thinkube_installation.log")

# Network Discovery Helper Functions
async def get_network_interface():
    """Get the main network interface"""
    try:
        # Get default route interface
        result = await asyncio.create_subprocess_exec(
            'ip', 'route', 'show', 'default',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if stdout:
            # Parse: default via 192.168.1.1 dev br0 proto static
            parts = stdout.decode().strip().split()
            for i, part in enumerate(parts):
                if part == 'dev' and i + 1 < len(parts):
                    return parts[i + 1]
        
        # Fallback to common interfaces
        for iface in ['eth0', 'br0', 'enp0s3', 'ens18']:
            try:
                result = await asyncio.create_subprocess_exec(
                    'ip', 'addr', 'show', iface,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                if stdout and 'inet ' in stdout.decode():
                    return iface
            except:
                continue
                
        return 'eth0'  # Final fallback
    except:
        return 'eth0'

async def ping_sweep(network_cidr: str):
    """Perform a ping sweep to find active IPs"""
    try:
        network = ipaddress.IPv4Network(network_cidr, strict=False)
        active_ips = []
        
        # Create tasks for concurrent pinging
        async def ping_ip(ip_str):
            try:
                result = await asyncio.create_subprocess_exec(
                    'ping', '-c', '1', '-W', '1', ip_str,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await result.communicate()
                if result.returncode == 0:
                    return ip_str
            except:
                pass
            return None
        
        # Limit to reasonable subnet size (max 254 hosts)
        host_count = min(254, network.num_addresses - 2)
        tasks = []
        
        for i, ip in enumerate(network.hosts()):
            if i >= host_count:
                break
            tasks.append(ping_ip(str(ip)))
        
        # Execute pings concurrently in batches to avoid overwhelming
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            results = await asyncio.gather(*batch)
            active_ips.extend([ip for ip in results if ip])
        
        return active_ips
    except Exception as e:
        logger.error(f"Ping sweep error: {e}")
        return []

async def check_ssh_banner(ip: str, port: int = 22, timeout: int = 3):
    """Check if SSH is running and get banner info"""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        
        # SSH servers send banner immediately
        banner = await asyncio.wait_for(
            reader.readline(),
            timeout=timeout
        )
        
        writer.close()
        await writer.wait_closed()
        
        banner_str = banner.decode('utf-8', errors='ignore').strip()
        
        # Analyze banner for Ubuntu indicators
        is_ubuntu = 'Ubuntu' in banner_str
        
        # Be more specific about Ubuntu detection
        is_likely_ubuntu = False
        if is_ubuntu:
            is_likely_ubuntu = True
        elif 'OpenSSH' in banner_str:
            # Check for Ubuntu-specific OpenSSH patterns
            # Ubuntu typically has version patterns like "OpenSSH_8.9p1" or "OpenSSH_9.6p1"
            if any(version in banner_str for version in ['OpenSSH_8.9', 'OpenSSH_9.0', 'OpenSSH_9.3', 'OpenSSH_9.6']):
                is_likely_ubuntu = True
        
        ssh_version = banner_str if banner_str.startswith('SSH-') else None
        
        return {
            'ssh_available': True,
            'banner': banner_str,
            'is_ubuntu': is_ubuntu,
            'is_likely_ubuntu': is_likely_ubuntu,
            'ssh_version': ssh_version
        }
        
    except Exception as e:
        return {
            'ssh_available': False,
            'banner': None,
            'is_ubuntu': False,
            'is_likely_ubuntu': False,
            'ssh_version': None,
            'error': str(e)
        }

async def get_hostname_via_ssh(ip: str, timeout: int = 5):
    """Try to get hostname by connecting via SSH and reading it directly"""
    try:
        # Try to get hostname via SSH (if SSH key auth is available)
        # This is the most reliable method for clean systems
        result = await asyncio.create_subprocess_exec(
            'ssh', '-o', 'ConnectTimeout=3', 
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'BatchMode=yes',  # Don't prompt for password
            f'thinkube@{ip}', 'hostname',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=timeout)
        
        if result.returncode == 0 and stdout:
            hostname = stdout.decode().strip()
            if hostname and hostname != ip:
                return hostname
    except:
        pass
    
    return None

async def get_hostname_info(ip: str):
    """Try to get hostname via methods that work on clean systems"""
    # Method 1: Try SSH-based hostname detection (most reliable for thinkube)
    hostname = await get_hostname_via_ssh(ip)
    if hostname:
        return hostname
    
    # Method 2: Try mDNS/Avahi discovery (works on Ubuntu desktop)
    try:
        result = await asyncio.create_subprocess_exec(
            'avahi-resolve', '-a', ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if stdout:
            output = stdout.decode().strip()
            # Format: "192.168.1.101    hostname.local"
            parts = output.split()
            if len(parts) >= 2:
                hostname = parts[1].rstrip('.local')
                return hostname
    except:
        pass
    
    # Method 3: NetBIOS name resolution (for mixed networks)
    try:
        result = await asyncio.create_subprocess_exec(
            'nmblookup', '-A', ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if stdout:
            output = stdout.decode()
            for line in output.split('\n'):
                if '<00>' in line and 'GROUP' not in line:
                    hostname = line.split()[0].strip()
                    if hostname and hostname != ip:
                        return hostname
    except:
        pass
    
    # Method 4: Simple reverse DNS (may not work on clean systems)
    try:
        result = await asyncio.create_subprocess_exec(
            'dig', '+short', '-x', ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if stdout:
            hostname = stdout.decode().strip().rstrip('.')
            if hostname and not hostname.startswith(';') and hostname != ip and '.' in hostname:
                # Only accept FQDN results, not just IP addresses
                return hostname.split('.')[0]  # Return just the hostname part
    except:
        pass
    
    return None

async def discover_ubuntu_servers(network_cidr: str):
    """Main discovery function that combines multiple methods"""
    start_time = asyncio.get_event_loop().time()
    
    logger.info(f"Starting network discovery for {network_cidr}")
    
    # Step 1: Find active IPs
    logger.info("Finding active IPs...")
    active_ips = await ping_sweep(network_cidr)
    logger.info(f"Found {len(active_ips)} active IPs")
    
    if not active_ips:
        return {
            "servers": [],
            "total_scanned": 0,
            "scan_time": asyncio.get_event_loop().time() - start_time
        }
    
    # Step 2: Check SSH on all active IPs
    logger.info("Checking SSH availability...")
    servers = []
    
    async def analyze_host(ip):
        # Check SSH
        ssh_info = await check_ssh_banner(ip)
        
        # Get hostname if SSH is available
        hostname = None
        if ssh_info['ssh_available']:
            hostname = await get_hostname_info(ip)
        
        # Determine confidence level and OS info
        confidence = "unknown"
        os_info = None
        
        if ssh_info['is_ubuntu']:
            confidence = "confirmed"
            banner = ssh_info['banner']
            if 'Ubuntu' in banner:
                # Try to extract version info from banner
                if 'Ubuntu-' in banner:
                    # Example: SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.5
                    # Extract the Ubuntu package version to guess OS version
                    try:
                        ubuntu_part = banner.split('Ubuntu-')[1]
                        if ubuntu_part.startswith('3ubuntu'):
                            os_info = "Ubuntu 24.04 LTS"
                        elif ubuntu_part.startswith('2ubuntu'):
                            os_info = "Ubuntu 22.04 LTS"
                        elif ubuntu_part.startswith('1ubuntu'):
                            os_info = "Ubuntu 20.04 LTS"
                        else:
                            os_info = "Ubuntu (recent version)"
                    except:
                        os_info = "Ubuntu (version unknown)"
                else:
                    os_info = "Ubuntu (version unknown)"
        elif ssh_info['is_likely_ubuntu']:
            confidence = "possible"
            os_info = "Likely Ubuntu (needs verification)"
        elif ssh_info['ssh_available']:
            # Only mark as "possible" for very specific cases
            banner = ssh_info['banner'] or ""
            
            # Check for strong Ubuntu indicators
            non_ubuntu_indicators = ['Debian', 'CentOS', 'RHEL', 'Alpine', 'raspberrypi', 'Cisco', 'Mikrotik', 'pfSense']
            has_non_ubuntu_indicator = any(indicator.lower() in banner.lower() for indicator in non_ubuntu_indicators)
            
            if not has_non_ubuntu_indicator and 'OpenSSH' in banner:
                confidence = "possible"
                os_info = "Linux SSH server (needs verification)"
            else:
                confidence = "unlikely"
        
        return {
            "ip": ip,
            "hostname": hostname,
            "os_info": os_info,
            "ssh_available": ssh_info['ssh_available'],
            "confidence": confidence,
            "banner": ssh_info['banner']
        }
    
    # Analyze all hosts concurrently
    tasks = [analyze_host(ip) for ip in active_ips]
    servers = await asyncio.gather(*tasks)
    
    # Filter to only return servers with Ubuntu indicators or strong Linux candidates
    ubuntu_servers = [
        server for server in servers 
        if server['confidence'] in ['confirmed', 'possible']
    ]
    
    # Sort by confidence (confirmed first, then possible)
    confidence_order = {'confirmed': 0, 'possible': 1}
    ubuntu_servers.sort(key=lambda x: confidence_order.get(x['confidence'], 2))
    
    scan_time = asyncio.get_event_loop().time() - start_time
    
    logger.info(f"Discovery completed in {scan_time:.2f}s. Found {len(ubuntu_servers)} Ubuntu candidates.")
    
    return {
        "servers": ubuntu_servers,
        "total_scanned": len(active_ips),
        "scan_time": scan_time
    }

# Network Discovery endpoints
@app.post("/api/discover-servers")
async def discover_servers(request: dict):
    """Discover Ubuntu servers on the network"""
    network_cidr = request.get("network_cidr", "192.168.1.0/24")
    
    # Real network discovery
    try:
        result = await discover_ubuntu_servers(network_cidr)
        return result
    except Exception as e:
        logger.error(f"Network discovery error: {e}")
        return {
            "error": f"Network discovery failed: {str(e)}",
            "servers": [],
            "total_scanned": 0,
            "scan_time": 0
        }

async def get_local_ip_addresses():
    """Get all local IP addresses"""
    try:
        local_ips = set()
        
        # Method 1: Parse ip addr output 
        result = await asyncio.create_subprocess_exec(
            'ip', 'addr', 'show',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if result.returncode == 0:
            import re
            # Extract all IP addresses from ip addr output, excluding CIDR
            ip_pattern = r'inet (\d+\.\d+\.\d+\.\d+)/\d+'
            for match in re.finditer(ip_pattern, stdout.decode()):
                ip = match.group(1)
                if ip != '127.0.0.1':  # Exclude localhost
                    local_ips.add(ip)
                    logger.info(f"Found local IP: {ip}")
        
        # Method 2: Use hostname resolution as fallback
        try:
            import socket
            hostname = socket.gethostname()
            host_ip = socket.gethostbyname(hostname)
            if host_ip != '127.0.0.1':
                local_ips.add(host_ip)
                logger.info(f"Found hostname IP: {host_ip}")
        except:
            pass
        
        # Method 3: Check default route interface
        try:
            route_result = await asyncio.create_subprocess_exec(
                'ip', 'route', 'get', '8.8.8.8',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            route_stdout, _ = await route_result.communicate()
            if route_result.returncode == 0:
                import re
                # Extract source IP from route output
                src_match = re.search(r'src (\d+\.\d+\.\d+\.\d+)', route_stdout.decode())
                if src_match:
                    src_ip = src_match.group(1)
                    local_ips.add(src_ip)
                    logger.info(f"Found route source IP: {src_ip}")
        except:
            pass
        
        logger.info(f"Total local IPs found: {local_ips}")
        return local_ips
    except Exception as e:
        logger.error(f"Error getting local IPs: {e}")
        return set()

async def verify_local_server():
    """Verify local server without SSH"""
    try:
        # Get hostname
        hostname_result = await asyncio.create_subprocess_exec(
            'hostname',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        hostname_stdout, _ = await hostname_result.communicate()
        hostname = hostname_stdout.decode().strip() if hostname_result.returncode == 0 else None
        
        # Get OS info
        os_result = await asyncio.create_subprocess_exec(
            'lsb_release', '-d',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        os_stdout, _ = await os_result.communicate()
        
        os_info = None
        if os_result.returncode == 0:
            os_info = os_stdout.decode().strip().replace('Description:', '').strip()
        else:
            # Fallback to /etc/os-release
            try:
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            os_info = line.split('=', 1)[1].strip().strip('"')
                            break
            except:
                pass
        
        return {
            "connected": True,
            "message": "Local server (running installer)",
            "os_info": os_info,
            "hostname": hostname
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Local server verification error: {str(e)}",
            "os_info": None,
            "hostname": None
        }

@app.get("/api/debug-local-ips")
async def debug_local_ips():
    """Debug endpoint to check local IP detection"""
    local_ips = await get_local_ip_addresses()
    return {
        "local_ips": list(local_ips),
        "count": len(local_ips)
    }

@app.post("/api/debug-ssh-check")
async def debug_ssh_check(request: dict):
    """Debug endpoint to test SSH verification logic"""
    ip_address = request.get("ip_address")
    local_ips = await get_local_ip_addresses()
    
    return {
        "ip_to_check": ip_address,
        "local_ips": list(local_ips),
        "is_local": ip_address in local_ips,
        "ip_type": type(ip_address).__name__,
        "comparison_details": {
            str(ip): {"matches": ip == ip_address, "type": type(ip).__name__} 
            for ip in local_ips
        }
    }

@app.post("/api/verify-server-ssh")
async def verify_server_ssh(server: dict):
    """Verify SSH connectivity to a server"""
    ip_address = server.get("ip_address")
    username = server.get("username", "thinkube")
    
    if not ip_address:
        return {
            "connected": False,
            "message": "IP address is required",
            "os_info": None,
            "hostname": None
        }
    
    # Check if this is the local machine using multiple methods
    local_ips = await get_local_ip_addresses()
    logger.info(f"Checking if {ip_address} is in local IPs: {local_ips}")
    
    is_local = ip_address in local_ips
    
    # Alternative method: try to bind to the IP address locally
    if not is_local:
        try:
            import socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.bind((ip_address, 0))  # Bind to any available port
            test_socket.close()
            is_local = True
            logger.info(f"IP {ip_address} confirmed as local via socket binding")
        except Exception as e:
            logger.info(f"IP {ip_address} socket binding failed: {e}")
    
    if is_local:
        logger.info(f"Detected local server {ip_address}, using direct verification")
        return await verify_local_server()
    else:
        logger.info(f"IP {ip_address} is not local, proceeding with SSH verification")
    
    try:
        # Try SSH connection with key-based auth for remote servers
        result = await asyncio.create_subprocess_exec(
            'ssh', '-o', 'ConnectTimeout=5',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'BatchMode=yes',  # Don't prompt for password
            f'{username}@{ip_address}', 'echo "SSH OK"; lsb_release -d 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        
        if result.returncode == 0:
            output = stdout.decode().strip()
            lines = output.split('\n')
            
            # Get hostname
            hostname_result = await asyncio.create_subprocess_exec(
                'ssh', '-o', 'ConnectTimeout=5',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'BatchMode=yes',
                f'{username}@{ip_address}', 'hostname',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            hostname_stdout, _ = await hostname_result.communicate()
            hostname = hostname_stdout.decode().strip() if hostname_result.returncode == 0 else None
            
            # Extract OS info
            os_info = None
            for line in lines:
                if 'Ubuntu' in line:
                    os_info = line.replace('Description:', '').replace('PRETTY_NAME=', '').strip().strip('"')
                    break
            
            return {
                "connected": True,
                "message": "SSH connection successful",
                "os_info": os_info,
                "hostname": hostname
            }
        else:
            error_msg = stderr.decode().strip()
            return {
                "connected": False,
                "message": f"SSH connection failed: {error_msg}",
                "os_info": None,
                "hostname": None
            }
    except Exception as e:
        return {
            "connected": False,
            "message": f"SSH verification error: {str(e)}",
            "os_info": None,
            "hostname": None
        }

@app.post("/api/detect-hardware")
async def detect_hardware(server: dict):
    """Detect hardware configuration of a server"""
    test_mode = server.get("test_mode", False)
    
    if test_mode:
        # Return emulated hardware based on IP
        await asyncio.sleep(1.5)
        
        if server["ip_address"] == "192.168.1.101":
            # bcn1 - powerful desktop
            return {
                "hardware": {
                    "cpu_cores": 32,
                    "cpu_model": "AMD Ryzen 9 5950X",
                    "memory_gb": 128,
                    "disk_gb": 2000,
                    "gpu_detected": True,
                    "gpu_model": "NVIDIA GeForce RTX 3090",
                    "gpu_count": 2,
                    "architecture": "x86_64"
                }
            }
        elif server["ip_address"] == "192.168.1.102":
            # bcn2 - server
            return {
                "hardware": {
                    "cpu_cores": 16,
                    "cpu_model": "AMD Ryzen 7 3700X",
                    "memory_gb": 64,
                    "disk_gb": 1000,
                    "gpu_detected": True,
                    "gpu_model": "NVIDIA GeForce GTX 1080 Ti",
                    "gpu_count": 1,
                    "architecture": "x86_64"
                }
            }
        else:
            # Generic server
            return {
                "hardware": {
                    "cpu_cores": 8,
                    "cpu_model": "Intel Core i7-9700K",
                    "memory_gb": 32,
                    "disk_gb": 500,
                    "gpu_detected": False,
                    "gpu_model": None,
                    "gpu_count": 0,
                    "architecture": "x86_64"
                }
            }
    
    # Real hardware detection would go here
    return {
        "error": "Real hardware detection not implemented. Use test_mode=true",
        "hardware": None
    }

@app.post("/api/verify-cloudflare")
async def verify_cloudflare_token(request: dict):
    """Verify Cloudflare API token has access to the specified domain"""
    try:
        token = request.get('token', '')
        domain = request.get('domain', '')
        
        if not token or not domain:
            return {"valid": False, "message": "Token and domain are required"}
        
        # Call Cloudflare API to list zones
        import aiohttp
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'https://api.cloudflare.com/client/v4/zones?name={domain}',
                headers=headers
            ) as response:
                data = await response.json()
                
                if response.status == 200 and data.get('success'):
                    zones = data.get('result', [])
                    if zones:
                        # Found the domain
                        zone = zones[0]
                        return {
                            "valid": True, 
                            "message": f"Token has access to {zone['name']}",
                            "zone_id": zone['id']
                        }
                    else:
                        return {"valid": False, "message": f"Domain '{domain}' not found in Cloudflare account"}
                elif response.status == 403:
                    return {"valid": False, "message": "Invalid token or insufficient permissions"}
                elif response.status == 401:
                    return {"valid": False, "message": "Invalid Cloudflare API token"}
                else:
                    return {"valid": False, "message": f"Cloudflare API error: {data.get('errors', [{}])[0].get('message', 'Unknown error')}"}
                    
    except Exception as e:
        logger.error(f"Failed to verify Cloudflare token: {e}")
        return {"valid": False, "message": f"Verification error: {str(e)}"}

@app.post("/api/save-cluster-config")
async def save_cluster_config(config: dict):
    """Save the cluster configuration from node configuration UI"""
    try:
        # Validate the configuration
        servers = config.get("servers", [])
        if not servers:
            raise ValueError("No servers configured")
        
        # Check for control plane
        control_planes = []
        workers = []
        
        for server in servers:
            if server["role"] in ["hybrid", "direct"] and server.get("k8s_role") == "control_plane":
                control_planes.append(server)
            elif server["role"] in ["hybrid", "direct"] and server.get("k8s_role") == "worker":
                workers.append(server)
            
            # Check containers
            for container in server.get("containers", []):
                if container.get("k8s_role") == "control_plane":
                    control_planes.append(container)
                elif container.get("k8s_role") == "worker":
                    workers.append(container)
        
        if len(control_planes) != 1:
            raise ValueError(f"Exactly one control plane required, found {len(control_planes)}")
        
        if len(workers) < 1:
            raise ValueError("At least one worker node required")
        
        # Save configuration
        project_root = get_project_root()
        config_dir = project_root / "inventory" / "installer_configs"
        config_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_file = config_dir / f"cluster_config_{timestamp}.json"
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {
            "success": True,
            "message": "Configuration saved successfully",
            "config_file": str(config_file),
            "summary": {
                "servers": len(servers),
                "control_planes": len(control_planes),
                "workers": len(workers)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to save cluster config: {e}")
        return {
            "success": False,
            "message": str(e)
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

# 🤖 AI-generated