# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
API routes for server discovery
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import os
import asyncio
import json
from datetime import datetime
from pathlib import Path

from ..core.discovery import discover_ubuntu_servers, verify_ssh_connectivity
from ..utils.network import get_local_ip_addresses
from ..models.server import NetworkDiscoveryRequest, SSHVerificationRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["discovery"])


async def get_real_hardware_info(ip_address: str, username: str = "thinkube", password: str = None):
    """Get actual hardware information via SSH commands"""
    
    # Check if this is the local machine first
    local_ips = await get_local_ip_addresses()
    is_local = ip_address in local_ips
    
    # Create a bash script that collects all hardware info in one go
    hardware_script = '''#!/bin/bash
# Collect all hardware information in one script to minimize SSH connections

# Initialize output
echo "{"

# CPU cores
echo -n '"cpu_cores": '
nproc 2>/dev/null || echo -n "0"
echo ","

# CPU model
echo -n '"cpu_model": "'
cat /proc/cpuinfo 2>/dev/null | grep 'model name' | head -1 | cut -d: -f2 | sed 's/^ *//' | tr -d '\n' | sed 's/"/\\"/g' || echo -n "Unknown"
echo '",'

# Architecture
echo -n '"architecture": "'
uname -m 2>/dev/null | tr -d '\n' || echo -n "unknown"
echo '",'

# Memory in bytes
echo -n '"memory_bytes": '
free -b 2>/dev/null | grep '^Mem:' | awk '{print $2}' | tr -d '\n' || echo -n "0"
echo ","

# Disk in bytes
echo -n '"disk_bytes": '
df -B1 / 2>/dev/null | tail -1 | awk '{print $2}' | tr -d '\n' || echo -n "0"
echo ","

# NVIDIA GPU detection
echo -n '"nvidia_devices": ['
first=true
lspci -nn 2>/dev/null | grep -i nvidia | while IFS= read -r line; do
    if [ "$first" = true ]; then
        first=false
    else
        echo -n ","
    fi
    echo -n '"'
    echo -n "$line" | sed 's/"/\\"/g' | tr -d '\n'
    echo -n '"'
done
echo "],"

# Visible NVIDIA GPUs (excluding audio devices)
echo -n '"visible_gpus": ['
first=true
lspci -nn 2>/dev/null | grep -i nvidia | grep -E '\[030[0-2]\]' | while IFS= read -r line; do
    if [ "$first" = true ]; then
        first=false
    else
        echo -n ","
    fi
    echo -n '"'
    echo -n "$line" | sed 's/"/\\"/g' | tr -d '\n'
    echo -n '"'
done
echo "],"

# VFIO info
echo -n '"vfio_info": "'
lspci -k 2>/dev/null | grep -A 3 -i nvidia | tr '\n' ' ' | tr '\t' ' ' | sed 's/"/\\"/g' | sed 's/  */ /g' | tr -d '\n' || echo -n ""
echo '",'

# IOMMU enabled check - check if IOMMU groups exist
echo -n '"iommu_enabled": '
if [ -d /sys/kernel/iommu_groups/ ] && [ $(ls -1 /sys/kernel/iommu_groups/ 2>/dev/null | wc -l) -gt 0 ]; then
    echo -n "true"
else
    echo -n "false"
fi
echo ","

# IOMMU groups check
echo -n '"iommu_groups": ['
if [ -d /sys/kernel/iommu_groups/ ]; then
    group_count=$(ls -1 /sys/kernel/iommu_groups/ 2>/dev/null | wc -l)
    if [ "$group_count" -gt 0 ]; then
        first=true
        for gpu in $(lspci -nn | grep -i nvidia | grep -E '\[030[0-2]\]' | cut -d' ' -f1); do
            if [ "$first" = true ]; then
                first=false
            else
                echo -n ","
            fi
            echo -n "{"
            echo -n '"pci": "'$gpu'",'
            if [ -e /sys/bus/pci/devices/0000:$gpu/iommu_group ]; then
                group=$(readlink /sys/bus/pci/devices/0000:$gpu/iommu_group 2>/dev/null | sed 's/.*\///')
                echo -n '"group": "'$group'",'
                # Check if group has other devices that are NOT NVIDIA audio
                other_count=0
                for device in /sys/kernel/iommu_groups/$group/devices/*; do
                    dev_id=$(basename $device)
                    if [ "$dev_id" != "0000:$gpu" ]; then
                        # Check if it's an NVIDIA audio device (class 0403)
                        if ! lspci -n -s $dev_id 2>/dev/null | grep -q " 0403: 10de:"; then
                            # Not an NVIDIA audio device
                            other_count=$((other_count + 1))
                        fi
                    fi
                done
                if [ "$other_count" -eq 0 ]; then
                    echo -n '"isolated": true,'
                    echo -n '"eligible": true'
                else
                    echo -n '"isolated": false,'
                    echo -n '"eligible": false,'
                    echo -n '"other_devices": '$other_count
                fi
            else
                echo -n '"group": null,'
                echo -n '"eligible": false'
            fi
            echo -n "}"
        done
    fi
fi
echo "],"

# Network interface detection
echo -n '"network": {'

# Get primary network interface and IP using ip route
primary_route=$(ip route get 8.8.8.8 2>/dev/null | head -1)
if [ ! -z "$primary_route" ]; then
    # Extract interface name
    interface=$(echo "$primary_route" | grep -oP 'dev \K\S+' || echo "")
    echo -n '"interface": "'$interface'",'
    
    # Extract source IP
    src_ip=$(echo "$primary_route" | grep -oP 'src \K\S+' || echo "")
    echo -n '"ip_address": "'$src_ip'",'
    
    # Get CIDR for this interface
    if [ ! -z "$interface" ] && [ ! -z "$src_ip" ]; then
        cidr=$(ip addr show $interface 2>/dev/null | grep "inet $src_ip" | grep -oP 'inet \K\S+' || echo "")
        # Convert to network CIDR
        if [ ! -z "$cidr" ]; then
            # Use Python to calculate network CIDR properly
            network_cidr=$(python3 -c "import ipaddress; print(str(ipaddress.IPv4Network('$cidr', strict=False)))" 2>/dev/null || echo "$cidr")
            echo -n '"cidr": "'$network_cidr'",'
        else
            echo -n '"cidr": "",'
        fi
    else
        echo -n '"cidr": "",'
    fi
    
    # Get gateway
    gateway=$(ip route | grep "^default" | grep "dev $interface" | awk '{print $3}' | head -1 || echo "")
    echo -n '"gateway": "'$gateway'"'
else
    # Fallback if route detection fails
    echo -n '"interface": "",'
    echo -n '"ip_address": "",'
    echo -n '"cidr": "",'
    echo -n '"gateway": ""'
fi

echo "}"

echo "}"
'''
    
    async def run_hardware_collection():
        """Run the hardware collection script"""
        if is_local:
            # Run locally
            process = await asyncio.create_subprocess_shell(
                hardware_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return stdout.decode().strip() if process.returncode == 0 else "{}"
        else:
            # Run via SSH - single connection for all data
            # Always use password if provided since SSH keys might not be set up yet
            if password:
                # Use sshpass for password authentication
                ssh_cmd = [
                    'sshpass', '-p', password,
                    'ssh', '-o', 'ConnectTimeout=10',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'PreferredAuthentications=password',
                    '-o', 'PubkeyAuthentication=no',
                    f'{username}@{ip_address}',
                    'bash -s'
                ]
            else:
                # Try key-based authentication with BatchMode
                ssh_cmd = [
                    'ssh', '-o', 'ConnectTimeout=10',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'BatchMode=yes',
                    f'{username}@{ip_address}',
                    'bash -s'
                ]
            process = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=hardware_script.encode())
            if process.returncode != 0:
                logger.error(f"SSH command failed with return code {process.returncode}")
                logger.error(f"stderr: {stderr.decode()}")
                return "{}"
            return stdout.decode().strip()
    
    try:
        # Run the collection script and get JSON output
        logger.info(f"Collecting hardware info for {ip_address}")
        json_output = await run_hardware_collection()
        
        logger.info(f"Raw JSON output length: {len(json_output)}")
        if not json_output or json_output == "{}":
            logger.error(f"Empty or minimal JSON output for {ip_address}")
        
        # Parse the JSON output
        import json
        try:
            raw_data = json.loads(json_output)
            logger.info(f"Raw IOMMU data from {ip_address}: iommu_groups={raw_data.get('iommu_groups', [])}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse hardware JSON: {e}, output was: {json_output}")
            raw_data = {}
        
        # Convert to expected format
        hardware_info = {
            "cpu_cores": int(raw_data.get("cpu_cores", 0)),
            "cpu_model": raw_data.get("cpu_model", "Unknown"),
            "memory_gb": round(int(raw_data.get("memory_bytes", 0)) / (1024**3), 1),
            "disk_gb": round(int(raw_data.get("disk_bytes", 0)) / (1024**3), 1),
            "gpu_detected": False,
            "gpu_model": None,
            "gpu_count": 0,
            "architecture": raw_data.get("architecture", "unknown")
        }
        
        # Process GPU information
        nvidia_gpus = []
        vfio_gpus = []
        all_nvidia_devices = raw_data.get("nvidia_devices", [])
        visible_gpus = raw_data.get("visible_gpus", [])
        vfio_info = raw_data.get("vfio_info", "")
        total_nvidia_devices = len(all_nvidia_devices)
        
        if total_nvidia_devices > 0:
            logger.info(f"Total NVIDIA devices found: {total_nvidia_devices}")
            for device in all_nvidia_devices:
                logger.info(f"NVIDIA device: {device}")
        
        # Process visible NVIDIA GPUs
        for line in visible_gpus:
            logger.info(f"Processing GPU line: {line}")
            # Extract NVIDIA GPU model from lspci output
            # Format: "01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GP107 [GeForce GTX 1050 Ti] [10de:1c82]"
            if 'NVIDIA Corporation' in line:
                # Split after NVIDIA Corporation to get the model part
                parts = line.split('NVIDIA Corporation', 1)
                if len(parts) > 1:
                    model_part = parts[1]
                    logger.info(f"Model part after split: {model_part}")
                    # Extract text between first set of brackets after corporation name
                    # This contains the actual GPU model name
                    bracket_start = model_part.find('[')
                    if bracket_start != -1:
                        bracket_end = model_part.find(']', bracket_start)
                        if bracket_end != -1:
                            gpu_model = model_part[bracket_start+1:bracket_end].strip()
                            logger.info(f"Extracted GPU model: {gpu_model}")
                        else:
                            gpu_model = model_part.split('[')[0].strip()
                            logger.info(f"Fallback GPU model (no closing bracket): {gpu_model}")
                    else:
                        gpu_model = model_part.split('[')[0].strip()
                        logger.info(f"Fallback GPU model (no opening bracket): {gpu_model}")
                else:
                    gpu_model = "NVIDIA GPU"
                    logger.info("No parts after split, using default")
            else:
                gpu_model = "Unknown GPU"
                logger.info("No NVIDIA Corporation found in line")
            nvidia_gpus.append(gpu_model)
        
        # Check for VFIO-bound GPUs in vfio_info
        if vfio_info:
            vfio_lines = vfio_info.split('  ')  # Split by double space since we joined with spaces
            for i, segment in enumerate(vfio_lines):
                if 'nvidia' in segment.lower() and ('vga' in segment.lower() or '3d' in segment.lower()):
                    # Check if vfio-pci is mentioned nearby
                    combined_text = ' '.join(vfio_lines[i:i+4])  # Check next few segments
                    if 'vfio-pci' in combined_text:
                        # Try to extract GPU model name from VFIO info
                        if 'NVIDIA Corporation' in segment:
                            parts = segment.split('NVIDIA Corporation', 1)
                            if len(parts) > 1 and '[' in parts[1]:
                                model_part = parts[1]
                                bracket_start = model_part.find('[')
                                bracket_end = model_part.find(']', bracket_start)
                                if bracket_end != -1:
                                    gpu_model = model_part[bracket_start+1:bracket_end].strip()
                                else:
                                    gpu_model = "NVIDIA GPU (VFIO-bound)"
                            else:
                                gpu_model = "NVIDIA GPU (VFIO-bound)"
                        else:
                            gpu_model = "NVIDIA GPU (VFIO-bound)"
                        vfio_gpus.append(gpu_model)
                        logger.info(f"Found VFIO-bound GPU: {gpu_model}")
        
        # Set GPU information
        visible_count = len(nvidia_gpus)
        vfio_count = len(vfio_gpus)
        total_gpu_count = visible_count + vfio_count
        
        if total_gpu_count > 0:
            hardware_info["gpu_detected"] = True
            hardware_info["gpu_count"] = total_gpu_count
            
            # Create descriptive model string
            if visible_count > 0 and vfio_count > 0:
                # Mix of visible and VFIO-bound
                if visible_count == 1 and vfio_count == 1:
                    hardware_info["gpu_model"] = f"{nvidia_gpus[0]} + 1 VFIO-bound"
                else:
                    hardware_info["gpu_model"] = f"{visible_count} visible + {vfio_count} VFIO-bound NVIDIA GPUs"
            elif visible_count > 0:
                # Only visible GPUs
                if visible_count == 1:
                    hardware_info["gpu_model"] = nvidia_gpus[0]
                elif len(set(nvidia_gpus)) == 1:
                    hardware_info["gpu_model"] = f"{visible_count}x {nvidia_gpus[0]}"
                else:
                    hardware_info["gpu_model"] = f"{visible_count} NVIDIA GPUs: {', '.join(nvidia_gpus)}"
            elif vfio_count > 0:
                # Only VFIO-bound GPUs
                if vfio_count == 1:
                    hardware_info["gpu_model"] = f"{vfio_gpus[0]} (VFIO-bound)"
                else:
                    hardware_info["gpu_model"] = f"{vfio_count} NVIDIA GPUs (all VFIO-bound)"
            
            logger.info(f"GPU Summary: {visible_count} visible, {vfio_count} VFIO-bound, {total_gpu_count} total")
        
        # Process IOMMU information for GPU passthrough
        iommu_enabled = raw_data.get("iommu_enabled", False)
        iommu_groups = raw_data.get("iommu_groups", [])
        
        # First, collect basic GPU info from visible GPUs (for baremetal use)
        gpu_passthrough_info = []
        
        # Process all visible NVIDIA GPUs - these can be used by GPU operator on baremetal
        if visible_gpus:
            logger.info(f"Processing {len(visible_gpus)} visible GPU(s)")
            for line in visible_gpus:
                # Extract PCI address
                pci_addr = line.split()[0] if line else "unknown"
                
                # For baremetal GPU operator use, all detected GPUs are "eligible"
                # even without IOMMU (they just can't be passed to VMs)
                gpu_info = {
                    "pci": pci_addr,
                    "group": None,
                    "eligible": True,  # Eligible for baremetal GPU operator use
                    "driver": "nvidia",  # Assume nvidia driver for visible GPUs
                    "reason": "Available for GPU operator on baremetal"
                }
                
                # If IOMMU is enabled, check passthrough eligibility
                if iommu_enabled and iommu_groups:
                    # Find matching IOMMU group info
                    for iommu_gpu in iommu_groups:
                        if iommu_gpu.get("pci") == pci_addr:
                            gpu_info["group"] = iommu_gpu.get("group")
                            gpu_info["eligible"] = iommu_gpu.get("eligible", False)
                            if iommu_gpu.get("eligible"):
                                gpu_info["reason"] = f"IOMMU group {gpu_info['group']} isolated - can pass to VMs"
                            else:
                                gpu_info["reason"] = f"IOMMU group {gpu_info['group']} not isolated - baremetal only"
                            break
                else:
                    gpu_info["reason"] = "IOMMU not enabled - baremetal use only"
                
                gpu_passthrough_info.append(gpu_info)
                logger.info(f"GPU {pci_addr}: {gpu_info['reason']}")
        
        # Add GPU passthrough information to the hardware info
        hardware_info["gpu_passthrough"] = {
            "iommu_enabled": iommu_enabled,
            "gpus": gpu_passthrough_info,
            "total_eligible": sum(1 for gpu in gpu_passthrough_info if gpu.get("eligible", False)),
            "total_found": len(gpu_passthrough_info)
        }
        
        # Debug log the GPU passthrough data
        logger.info(f"GPU passthrough data for {ip_address}: {json.dumps(hardware_info['gpu_passthrough'], indent=2)}")
            
        # Log diagnostic info
        if total_nvidia_devices != total_gpu_count:
            logger.warning(f"Device count mismatch: {total_nvidia_devices} total devices vs {total_gpu_count} GPUs detected")
        
        # Add network information if available
        network_info = raw_data.get("network", {})
        
        logger.info(f"Hardware detection completed for {ip_address}: {hardware_info}")
        logger.info(f"Network info for {ip_address}: {network_info}")
        
        # Return both hardware and network info
        return {
            "hardware": hardware_info,
            "network": network_info
        }
        
    except Exception as e:
        logger.error(f"Error in hardware detection for {ip_address}: {e}")
        raise


@router.post("/discover-servers")
async def discover_servers(request: Dict[str, Any]):
    """Discover Ubuntu servers on the network"""
    network_cidr = request.get("network_cidr", "192.168.1.0/24")
    username = request.get("username")
    password = request.get("password")
    
    # Real network discovery
    try:
        result = await discover_ubuntu_servers(network_cidr, username, password)
        return result
    except Exception as e:
        logger.error(f"Network discovery error: {e}")
        return {
            "error": f"Network discovery failed: {str(e)}",
            "servers": [],
            "total_scanned": 0,
            "scan_time": 0
        }


@router.post("/verify-server-ssh")
async def verify_server_ssh(server: Dict[str, Any]):
    """Verify SSH connectivity to a server"""
    ip_address = server.get("ip_address")
    password = server.get("password")
    
    # Get current system username as default
    import pwd
    current_username = pwd.getpwuid(os.getuid()).pw_name
    username = server.get("username", current_username)
    
    if not ip_address:
        return {
            "connected": False,
            "message": "IP address is required",
            "os_info": None,
            "hostname": None
        }
    
    return await verify_ssh_connectivity(ip_address, username, password)


@router.post("/verify-ssh")
async def verify_ssh(request: Dict[str, Any]):
    """Verify SSH connectivity - frontend compatibility endpoint"""
    # Extract parameters from frontend request format
    server_ip = request.get("server")
    password = request.get("password")
    
    # Get current system username as default if not provided
    import pwd
    current_username = pwd.getpwuid(os.getuid()).pw_name
    username = request.get("username", current_username)
    
    if not server_ip:
        return {
            "connected": False,
            "message": "Server IP is required",
            "os_info": None,
            "hostname": None
        }
    
    return await verify_ssh_connectivity(server_ip, username, password)


@router.get("/debug-local-ips")
async def debug_local_ips():
    """Debug endpoint to check local IP detection"""
    local_ips = await get_local_ip_addresses()
    return {
        "local_ips": list(local_ips),
        "count": len(local_ips)
    }


@router.post("/setup-ssh-keys")
async def setup_ssh_keys(request: Dict[str, Any]):
    """Set up SSH keys between servers using Ansible playbook"""
    from ..services.ansible_executor import ansible_executor
    
    servers = request.get("servers", [])
    username = request.get("username", "thinkube")
    password = request.get("password")
    
    # Define playbook path
    playbook_path = "ansible/00_initial_setup/10_setup_ssh_keys.yaml"
    
    # Set up environment variables for Ansible
    environment = {}
    if password:
        environment["ANSIBLE_SUDO_PASS"] = password
    
    # Execute the playbook using the reusable service
    result = await ansible_executor.execute_playbook(
        playbook_path=playbook_path,
        environment=environment,
        timeout=180  # 3 minutes for SSH setup
    )
    
    # Return standardized response
    return ansible_executor.format_result_for_api(result)


@router.post("/debug-ssh-check")
async def debug_ssh_check(request: Dict[str, Any]):
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


@router.post("/detect-hardware")
async def detect_hardware(server: Dict[str, Any]):
    """Detect hardware configuration of a server via SSH"""
    # Handle both parameter names for compatibility
    ip_address = server.get("ip_address") or server.get("server")
    username = server.get("username", "thinkube")
    password = server.get("password")
    
    if not ip_address:
        return {"error": "IP address is required for hardware detection"}
    
    try:
        logger.info(f"Detecting hardware for {ip_address} with user {username}")
        
        # Get actual hardware info via SSH
        result = await get_real_hardware_info(ip_address, username, password)
        
        # Handle both old and new response formats
        if isinstance(result, dict) and "hardware" in result:
            # New format with hardware and network
            return result
        else:
            # Old format - just hardware info
            return {"hardware": result, "network": {}}
        
    except Exception as e:
        logger.error(f"Failed to detect hardware for {ip_address}: {e}")
        return {
            "error": f"Hardware detection failed: {str(e)}",
            "hardware": {
                "cpu_cores": 0,
                "cpu_model": "Detection Failed",
                "memory_gb": 0,
                "disk_gb": 0,
                "gpu_detected": False,
                "gpu_model": None,
                "gpu_count": 0,
                "architecture": "unknown"
            },
            "network": {}
        }


@router.post("/discover-zerotier-nodes")
async def discover_zerotier_nodes(request: Dict[str, Any]):
    """Discover nodes in a ZeroTier network"""
    network_id = request.get("network_id")
    api_token = request.get("api_token")
    
    if not network_id or not api_token:
        return {"error": "Network ID and API token are required", "nodes": []}
    
    try:
        import aiohttp
        headers = {"Authorization": f"Bearer {api_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Get network members
            async with session.get(
                f"https://api.zerotier.com/api/v1/network/{network_id}/member",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"ZeroTier API error: {response.status} - {error_text}")
                    return {"error": f"ZeroTier API error: {response.status}", "nodes": []}
                
                members = await response.json()
                
                nodes = []
                for member in members:
                    # Only include authorized and online members
                    if member.get("config", {}).get("authorized") and member.get("online"):
                        ip_assignments = member.get("config", {}).get("ipAssignments", [])
                        if ip_assignments:
                            nodes.append({
                                "hostname": member.get("name", f"node-{member['nodeId'][:8]}"),
                                "zerotier_ip": ip_assignments[0],
                                "node_id": member["nodeId"],
                                "online": True,
                                "description": member.get("description", ""),
                                "last_seen": member.get("lastSeen", 0)
                            })
                
                return {
                    "nodes": nodes,
                    "total": len(nodes),
                    "network_id": network_id
                }
                
    except Exception as e:
        logger.error(f"Failed to discover ZeroTier nodes: {e}")
        return {"error": f"Discovery failed: {str(e)}", "nodes": []}


@router.post("/verify-zerotier-ssh")
async def verify_zerotier_ssh(request: Dict[str, Any]):
    """Verify SSH connectivity over ZeroTier network"""
    zerotier_ip = request.get("zerotier_ip")
    username = request.get("username")
    password = request.get("password")
    
    if not zerotier_ip:
        return {
            "connected": False,
            "message": "ZeroTier IP is required",
            "os_info": None,
            "hostname": None
        }
    
    # Use the existing verify_ssh_connectivity function
    return await verify_ssh_connectivity(zerotier_ip, username, password)


@router.post("/verify-cloudflare")
async def verify_cloudflare(request: Dict[str, Any]):
    """Verify Cloudflare API token and domain access"""
    try:
        token = request.get('token', '')
        domain = request.get('domain', '')
        
        if not token:
            return {"valid": False, "message": "No API token provided"}
        
        if not domain:
            return {"valid": False, "message": "No domain provided"}
        
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


@router.post("/save-cluster-config")
async def save_cluster_config(config: Dict[str, Any]):
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
        # For now, save to a temporary location since we don't have get_project_root function
        home_dir = Path.home()
        config_dir = home_dir / "thinkube" / "inventory" / "installer_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        
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