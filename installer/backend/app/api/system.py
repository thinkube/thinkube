# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
API routes for system requirements and checks
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
import asyncio
import logging
import os
import json
import ipaddress
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/zerotier-network")
async def get_zerotier_network():
    """Detect the ZeroTier network CIDR from the zt* interface"""
    try:
        # Find ZeroTier interfaces (they start with 'zt')
        result = await asyncio.create_subprocess_exec(
            'ip', 'link', 'show',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if result.returncode != 0:
            logger.error("Failed to list network interfaces")
            return {"network_cidr": "", "detected": False}
        
        # Find zt* interface
        output = stdout.decode()
        zt_interface = None
        for line in output.split('\n'):
            match = re.search(r'^\d+:\s+(zt\w+):', line)
            if match:
                zt_interface = match.group(1)
                break
        
        if not zt_interface:
            logger.info("No ZeroTier interface found")
            return {"network_cidr": "", "detected": False, "message": "No ZeroTier interface found"}
        
        # Get IP address and netmask from the ZeroTier interface
        result = await asyncio.create_subprocess_exec(
            'ip', 'addr', 'show', zt_interface,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if result.returncode != 0:
            logger.error(f"Failed to get ZeroTier interface {zt_interface} info")
            return {"network_cidr": "", "detected": False}
        
        # Parse the IP address and netmask
        output = stdout.decode()
        cidr_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+/\d+)', output)
        
        if cidr_match:
            ip_cidr = cidr_match.group(1)
            # Convert IP/mask to network CIDR
            import ipaddress
            network = ipaddress.IPv4Network(ip_cidr, strict=False)
            network_cidr = str(network)
            
            logger.info(f"Detected ZeroTier network CIDR: {network_cidr} on interface {zt_interface}")
            return {
                "network_cidr": network_cidr,
                "interface": zt_interface,
                "detected": True
            }
        else:
            logger.error(f"Could not parse IP from ZeroTier interface {zt_interface}")
            return {"network_cidr": "", "detected": False}
            
    except Exception as e:
        logger.error(f"Error detecting ZeroTier network: {e}")
        return {"network_cidr": "", "detected": False, "error": str(e)}

@router.get("/local-network")
async def get_local_network():
    """Detect the local network CIDR based on the primary network interface"""
    try:
        # Get primary network interface info
        result = await asyncio.create_subprocess_exec(
            'ip', 'route', 'get', '8.8.8.8',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if result.returncode != 0:
            logger.error("Failed to get default route")
            return {"network_cidr": "192.168.1.0/24", "detected": False}
        
        # Parse output to get the interface and source IP
        output = stdout.decode()
        interface_match = re.search(r'dev (\S+)', output)
        src_ip_match = re.search(r'src (\d+\.\d+\.\d+\.\d+)', output)
        
        if not interface_match or not src_ip_match:
            logger.error("Could not parse route output")
            return {"network_cidr": "192.168.1.0/24", "detected": False}
        
        interface = interface_match.group(1)
        src_ip = src_ip_match.group(1)
        
        # Get network info for this interface
        result = await asyncio.create_subprocess_exec(
            'ip', 'addr', 'show', interface,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if result.returncode != 0:
            logger.error(f"Failed to get interface {interface} info")
            return {"network_cidr": "192.168.1.0/24", "detected": False}
        
        # Find the network CIDR for our source IP
        output = stdout.decode()
        for line in output.split('\n'):
            if 'inet ' in line and src_ip in line:
                # Extract CIDR notation
                cidr_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+/\d+)', line)
                if cidr_match:
                    ip_cidr = cidr_match.group(1)
                    # Convert to network CIDR
                    network = ipaddress.IPv4Network(ip_cidr, strict=False)
                    network_cidr = str(network)
                    
                    logger.info(f"Detected network CIDR: {network_cidr} on interface {interface}")
                    return {
                        "network_cidr": network_cidr,
                        "interface": interface,
                        "ip_address": src_ip,
                        "detected": True
                    }
        
        # Fallback
        logger.warning("Could not detect network CIDR, using default")
        return {"network_cidr": "192.168.1.0/24", "detected": False}
        
    except Exception as e:
        logger.error(f"Error detecting network: {e}")
        return {"network_cidr": "192.168.1.0/24", "detected": False, "error": str(e)}


@router.get("/check-installation-state")
async def check_installation_state():
    """Check what parts of thinkube are already installed"""
    state = {
        "environment_setup": False,
        "ansible_installed": False,
        "thinkube_repo_cloned": False,
        "ssh_keys_configured": False,
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
            state["kubernetes_running"] and
            len(state["services_deployed"]) >= 3  # At least 3 core services
        )
        
    except Exception as e:
        logger.error(f"Error checking installation state: {e}")
    
    return state


@router.post("/cleanup-installer-state")
async def cleanup_installer_state():
    """Clean up installer-generated files and state"""
    try:
        import os
        from pathlib import Path
        
        cleanup_results = []
        
        # Clean up inventory file (but keep reference-inventory.yaml)
        inventory_path = Path.home() / "thinkube" / "inventory" / "inventory.yaml"
        if inventory_path.exists():
            inventory_path.unlink()
            cleanup_results.append("Removed inventory.yaml")
        
        # Clean up any temporary SSH keys created by installer
        ssh_dir = Path.home() / ".ssh"
        installer_key = ssh_dir / "thinkube_installer_key"
        installer_pub = ssh_dir / "thinkube_installer_key.pub"
        
        if installer_key.exists():
            installer_key.unlink()
            cleanup_results.append("Removed installer SSH private key")
            
        if installer_pub.exists():
            installer_pub.unlink()
            cleanup_results.append("Removed installer SSH public key")
        
        # Clean up any ansible temp files
        ansible_tmp = Path("/tmp")
        for tmp_file in ansible_tmp.glob("ansible-*"):
            if tmp_file.is_file():
                try:
                    tmp_file.unlink()
                except:
                    pass  # Ignore permission errors
        
        return {
            "status": "success",
            "cleaned": cleanup_results,
            "message": "Installer state cleaned successfully"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning installer state: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/check-requirements")
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
    
    # 3. Check OpenSSH server is installed (required for Ansible to connect to localhost)
    try:
        # Check if openssh-server package is installed
        result = await asyncio.create_subprocess_exec(
            'dpkg', '-l', 'openssh-server',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        
        if result.returncode == 0 and b'ii  openssh-server' in stdout:
            # Check if SSH service is running
            service_result = await asyncio.create_subprocess_exec(
                'systemctl', 'is-active', 'ssh',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            service_stdout, _ = await service_result.communicate()
            service_status = service_stdout.decode().strip()
            
            # Also check SSH socket status for socket activation
            socket_result = await asyncio.create_subprocess_exec(
                'systemctl', 'is-active', 'ssh.socket',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            socket_stdout, _ = await socket_result.communicate()
            socket_status = socket_stdout.decode().strip()
            
            if service_status == 'active':
                requirements.append({
                    "name": "OpenSSH Server",
                    "category": "system",
                    "required": True,
                    "status": "pass",
                    "details": "OpenSSH server is installed and running"
                })
            elif socket_status == 'active':
                requirements.append({
                    "name": "OpenSSH Server",
                    "category": "system",
                    "required": True,
                    "status": "pass",
                    "details": "OpenSSH server is installed and available via socket activation"
                })
            else:
                requirements.append({
                    "name": "OpenSSH Server",
                    "category": "system",
                    "required": True,
                    "status": "fail",
                    "details": f"OpenSSH server is installed but not available (service: {service_status}, socket: {socket_status})"
                })
        else:
            requirements.append({
                "name": "OpenSSH Server",
                "category": "system",
                "required": True,
                "status": "fail",
                "details": "OpenSSH server is not installed. Run: sudo apt install openssh-server"
            })
    except Exception as e:
        requirements.append({
            "name": "OpenSSH Server",
            "category": "system",
            "required": True,
            "status": "fail",
            "details": f"Could not check OpenSSH server: {str(e)}"
        })
    
    # 4. Check network connectivity
    try:
        # Try to reach Ubuntu package servers
        import socket
        socket.create_connection(("archive.ubuntu.com", 443), timeout=3)
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
    
    # 5. Check disk space (10GB minimum for control node)
    try:
        import shutil
        free_gb = shutil.disk_usage(os.path.expanduser("~")).free / (1024**3)
        
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


@router.post("/verify-sudo")
async def verify_sudo_password(request: Dict[str, Any]):
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


@router.post("/run-setup")
async def run_setup(background_tasks: BackgroundTasks, request: Dict[str, Any] = {}):
    """Run the thinkube setup script"""
    try:
        # Check if thinkube is already installed by looking for actual installation markers
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


async def run_setup_script(sudo_password: str):
    """Background task to run the setup script"""
    # Import shared state
    from app.shared import app_state, broadcast_status
    
    try:
        logger.info("Starting thinkube setup script in background")
        
        # Reset installation status
        app_state.installation_status["phase"] = "starting"
        app_state.installation_status["progress"] = 0
        app_state.installation_status["current_task"] = "Initializing installation..."
        app_state.installation_status["logs"] = []
        app_state.installation_status["errors"] = []
        await broadcast_status(app_state.installation_status)
        
        # Find the setup script - use 10_install-tools.sh directly
        script_path = Path.home() / "thinkube" / "scripts" / "10_install-tools.sh"
        if not script_path.exists():
            logger.error(f"Setup script not found at {script_path}")
            app_state.installation_status["phase"] = "failed"
            app_state.installation_status["errors"].append(f"Setup script not found at {script_path}")
            await broadcast_status(app_state.installation_status)
            return
        
        # Set up environment
        env = os.environ.copy()
        if sudo_password:
            # Create a temporary askpass script for sudo
            import tempfile
            askpass_fd, askpass_path = tempfile.mkstemp()
            try:
                with os.fdopen(askpass_fd, 'w') as f:
                    f.write(f'#!/bin/sh\necho "{sudo_password}"\n')
                os.chmod(askpass_path, 0o700)
                env["SUDO_ASKPASS"] = askpass_path
            except:
                os.close(askpass_fd)
                raise
        
        # Update status to running
        app_state.installation_status["phase"] = "running"
        app_state.installation_status["logs"].append("Starting installation script...")
        await broadcast_status(app_state.installation_status)
        
        # Run the setup script with real-time output
        process = await asyncio.create_subprocess_exec(
            str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # Combine stderr into stdout
            env=env
        )
        
        # Read output line by line
        while True:
            line = await process.stdout.readline()
            if not line:
                break
                
            line_text = line.decode('utf-8', errors='replace').rstrip()
            if not line_text:
                continue
            
            # Log the line
            logger.info(f"Setup output: {line_text}")
            app_state.installation_status["logs"].append(line_text)
            
            # Parse [INSTALLER_STATUS] messages
            if "[INSTALLER_STATUS]" in line_text:
                status_part = line_text.split("[INSTALLER_STATUS]", 1)[1].strip()
                
                if status_part.startswith("PROGRESS:"):
                    try:
                        progress = int(status_part.split(":", 1)[1])
                        app_state.installation_status["progress"] = progress
                    except:
                        pass
                
                elif status_part.startswith("COMPLETED:"):
                    status = status_part.split(":", 1)[1]
                    if status == "FAILED":
                        app_state.installation_status["phase"] = "failed"
                    elif status == "SUCCESS":
                        app_state.installation_status["phase"] = "completed"
                        app_state.installation_status["progress"] = 100
                
                else:
                    # It's a status message
                    app_state.installation_status["current_task"] = status_part
            
            # Broadcast the update
            await broadcast_status(app_state.installation_status)
        
        # Wait for process to complete
        return_code = await process.wait()
        
        # Clean up askpass script if created
        if sudo_password and 'askpass_path' in locals():
            try:
                os.unlink(askpass_path)
            except:
                pass
        
        # Update final status
        if return_code == 0:
            if app_state.installation_status["phase"] != "completed":
                app_state.installation_status["phase"] = "completed"
                app_state.installation_status["progress"] = 100
                app_state.installation_status["current_task"] = "Installation completed successfully"
            logger.info("Setup script completed successfully")
        else:
            app_state.installation_status["phase"] = "failed"
            app_state.installation_status["errors"].append(f"Setup script failed with return code {return_code}")
            logger.error(f"Setup script failed with return code {return_code}")
        
        await broadcast_status(app_state.installation_status)
        
    except Exception as e:
        logger.error(f"Error running setup script: {e}")
        app_state.installation_status["phase"] = "failed"
        app_state.installation_status["errors"].append(f"Error: {str(e)}")
        await broadcast_status(app_state.installation_status)


@router.post("/verify-zerotier")
async def verify_zerotier(request: Dict[str, Any]):
    """Verify ZeroTier API token and network access"""
    try:
        api_token = request.get('api_token', '')
        network_id = request.get('network_id', '')
        
        if not api_token or not network_id:
            return {"valid": False, "message": "API token and network ID are required"}
        
        # Validate network ID format (16 hex characters)
        if len(network_id) != 16 or not all(c in '0123456789abcdef' for c in network_id.lower()):
            return {"valid": False, "message": "Network ID must be 16 hexadecimal characters"}
        
        # Test API token by getting network info
        import aiohttp
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {api_token}'
            }
            
            # Try to get network details
            url = f'https://api.zerotier.com/api/v1/network/{network_id}'
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    network_name = data.get('config', {}).get('name', 'Unnamed Network')
                    return {
                        "valid": True, 
                        "message": f"Successfully verified access to network: {network_name}",
                        "network_name": network_name
                    }
                elif response.status == 401:
                    return {"valid": False, "message": "Invalid API token"}
                elif response.status == 404:
                    return {"valid": False, "message": "Network not found or no access"}
                else:
                    return {"valid": False, "message": f"API error: {response.status}"}
                    
    except Exception as e:
        logger.error(f"Failed to verify ZeroTier credentials: {e}")
        return {"valid": False, "message": f"Verification error: {str(e)}"}


@router.get("/system/check-inventory")
async def check_inventory():
    """Check if inventory.yaml exists and return its content"""
    inventory_path = Path.home() / "thinkube" / "inventory" / "inventory.yaml"
    
    try:
        if inventory_path.exists():
            with open(inventory_path, 'r') as f:
                content = f.read()
            return {
                "exists": True,
                "path": str(inventory_path),
                "content": content
            }
        else:
            return {
                "exists": False,
                "path": str(inventory_path),
                "content": None
            }
    except Exception as e:
        logger.error(f"Error checking inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/deployment-state")
async def get_deployment_state():
    """Get the deployment state from persistent storage"""
    state_dir = Path.home() / ".thinkube-installer"
    state_file = state_dir / "deployment-state.json"
    
    try:
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
            return {
                "exists": True,
                "state": state
            }
        else:
            return {
                "exists": False,
                "state": None
            }
    except Exception as e:
        logger.error(f"Error loading deployment state: {e}")
        return {
            "exists": False,
            "state": None,
            "error": str(e)
        }


@router.post("/system/deployment-state")
async def save_deployment_state(request: Dict[str, Any]):
    """Save the deployment state to persistent storage"""
    state_dir = Path.home() / ".thinkube-installer"
    state_file = state_dir / "deployment-state.json"
    
    try:
        # Create directory if it doesn't exist
        state_dir.mkdir(exist_ok=True)
        
        # Save the state
        with open(state_file, 'w') as f:
            json.dump(request.get("state", {}), f, indent=2)
        
        return {
            "success": True,
            "path": str(state_file)
        }
    except Exception as e:
        logger.error(f"Error saving deployment state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/system/deployment-state")
async def clear_deployment_state():
    """Clear the deployment state file"""
    state_dir = Path.home() / ".thinkube-installer"
    state_file = state_dir / "deployment-state.json"
    
    try:
        if state_file.exists():
            state_file.unlink()
            return {
                "success": True,
                "message": "Deployment state cleared"
            }
        else:
            return {
                "success": True,
                "message": "No deployment state to clear"
            }
    except Exception as e:
        logger.error(f"Error clearing deployment state: {e}")
        raise HTTPException(status_code=500, detail=str(e))