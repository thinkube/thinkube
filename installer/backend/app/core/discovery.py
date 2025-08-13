# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
Server discovery and analysis logic
"""

import asyncio
import logging
from typing import List, Dict, Any
from ..utils.network import (
    ping_sweep, check_ssh_banner, get_hostname_info, 
    get_hostname_via_ssh, get_local_ip_addresses
)

logger = logging.getLogger(__name__)


async def discover_ubuntu_servers(network_cidr: str, username: str = None, password: str = None) -> Dict[str, Any]:
    """Main discovery function that combines multiple methods"""
    start_time = asyncio.get_event_loop().time()
    
    logger.info(f"Starting network discovery for {network_cidr} with username: {username}")
    
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
        # Stage 1: Quick SSH banner check to filter out non-Ubuntu systems
        ssh_info = await check_ssh_banner(ip)
        
        if not ssh_info['ssh_available']:
            # No SSH at all, skip
            return None
            
        # Check if it looks like Ubuntu based on banner
        banner = ssh_info.get('banner', '')
        is_likely_ubuntu = False
        
        if 'Ubuntu' in banner:
            is_likely_ubuntu = True
        elif banner.startswith('SSH-2.0-OpenSSH'):
            # Check for OpenSSH versions commonly used by Ubuntu
            if any(ver in banner for ver in ['OpenSSH_8.9p1', 'OpenSSH_9.0p1', 'OpenSSH_9.3p1', 'OpenSSH_9.6p1']):
                is_likely_ubuntu = True
        
        if not is_likely_ubuntu:
            # Not Ubuntu-like, return as failed with reason
            return {
                "ip": ip,
                "hostname": None,
                "os_info": "Non-Ubuntu system",
                "ssh_available": True,
                "confidence": "failed",
                "error": f"Not Ubuntu (banner: {banner[:50]}...)",
                "banner": banner
            }
        
        # Stage 2: Try actual SSH connection for Ubuntu-like systems
        if not username or not password:
            logger.warning("No credentials provided for discovery")
            return {
                "ip": ip,
                "hostname": None,
                "os_info": "Ubuntu (detected from banner)",
                "ssh_available": True,
                "confidence": "possible",
                "error": "No credentials for verification",
                "banner": banner
            }
        
        # First try with short timeout to quickly filter out auth failures
        try:
            verify_result = await asyncio.wait_for(
                verify_ssh_connectivity(ip, username, password, connect_timeout=5),
                timeout=10.0
            )
            
            if verify_result['connected']:
                # We can connect! It's a valid candidate
                return {
                    "ip": ip,
                    "hostname": verify_result.get('hostname'),
                    "os_info": verify_result.get('os_info'),
                    "ssh_available": True,
                    "confidence": "confirmed",
                    "error": None,
                    "banner": banner,
                    "is_local": verify_result.get('is_local', False)
                }
            else:
                # Authentication failed - this is fast, no need to retry
                return {
                    "ip": ip,
                    "hostname": None,
                    "os_info": "Ubuntu (banner detected, SSH failed)",
                    "ssh_available": True,
                    "confidence": "failed",
                    "error": verify_result.get('message', 'SSH authentication failed'),
                    "banner": banner
                }
        except asyncio.TimeoutError:
            # First attempt timed out - might be slow SSH
            # Try again with extended timeout ONLY for potential slow SSH servers
            logger.info(f"First SSH attempt to {ip} timed out, trying with extended timeout...")
            try:
                verify_result = await asyncio.wait_for(
                    verify_ssh_connectivity(ip, username, password, connect_timeout=40),
                    timeout=45.0
                )
                
                if verify_result['connected']:
                    return {
                        "ip": ip,
                        "hostname": verify_result.get('hostname'),
                        "os_info": verify_result.get('os_info') + " (slow SSH)",
                        "ssh_available": True,
                        "confidence": "confirmed",
                        "error": None,
                        "banner": banner,
                        "slow_ssh": True,  # Flag for UI to show this server has slow SSH
                        "is_local": verify_result.get('is_local', False)
                    }
                else:
                    return {
                        "ip": ip,
                        "hostname": None,
                        "os_info": "Ubuntu (banner detected, SSH failed after extended timeout)",
                        "ssh_available": True,
                        "confidence": "failed",
                        "error": verify_result.get('message', 'SSH authentication failed'),
                        "banner": banner
                    }
            except asyncio.TimeoutError:
                return {
                    "ip": ip,
                    "hostname": None,
                    "os_info": "Ubuntu (banner detected, connection timeout)",
                    "ssh_available": True,
                    "confidence": "failed",
                    "error": "SSH connection timeout after 45s",
                    "banner": banner
                }
    
    # Analyze all hosts concurrently
    tasks = [analyze_host(ip) for ip in active_ips]
    servers = await asyncio.gather(*tasks)
    
    # Return all servers, including failed ones for diagnostic purposes
    # Frontend will show failures differently
    all_servers = [server for server in servers if server is not None]
    
    # Sort by confidence (confirmed first, then possible, then failed)
    confidence_order = {'confirmed': 0, 'possible': 1, 'failed': 2}
    all_servers.sort(key=lambda x: confidence_order.get(x['confidence'], 3))
    
    scan_time = asyncio.get_event_loop().time() - start_time
    
    successful = [s for s in all_servers if s['confidence'] in ['confirmed', 'possible']]
    logger.info(f"Discovery completed in {scan_time:.2f}s. Found {len(successful)} accessible servers, {len(all_servers) - len(successful)} failed.")
    
    return {
        "servers": all_servers,  # Return all servers, including failed ones
        "total_scanned": len(active_ips),
        "scan_time": scan_time
    }


async def verify_local_server() -> Dict[str, Any]:
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
            "success": True,  # Frontend compatibility
            "message": "Local server (running installer)",
            "os_info": os_info,
            "hostname": hostname,
            "is_local": True  # This is the local machine
        }
    except Exception as e:
        return {
            "connected": False,
            "success": False,  # Frontend compatibility
            "message": f"Local server verification error: {str(e)}",
            "os_info": None,
            "hostname": None
        }


async def verify_ssh_connectivity(ip_address: str, username: str = "thinkube", password: str = None, connect_timeout: int = 5) -> Dict[str, Any]:
    """Verify SSH connectivity to a server"""
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
        # Try SSH connection - use password if provided, otherwise try key-based
        if password:
            # Use sshpass for password authentication
            result = await asyncio.create_subprocess_exec(
                'sshpass', '-p', password,
                'ssh', '-o', f'ConnectTimeout={connect_timeout}',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                f'{username}@{ip_address}', 'echo "SSH OK"; lsb_release -d 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            # Fall back to key-based auth
            result = await asyncio.create_subprocess_exec(
                'ssh', '-o', f'ConnectTimeout={connect_timeout}',
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
            if password:
                hostname_result = await asyncio.create_subprocess_exec(
                    'sshpass', '-p', password,
                    'ssh', '-o', f'ConnectTimeout={connect_timeout}',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'UserKnownHostsFile=/dev/null',
                    f'{username}@{ip_address}', 'hostname',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                hostname_result = await asyncio.create_subprocess_exec(
                    'ssh', '-o', f'ConnectTimeout={connect_timeout}',
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
                "success": True,  # Frontend compatibility
                "message": "SSH connection successful",
                "os_info": os_info,
                "hostname": hostname,
                "is_local": False  # This was an SSH connection, not local
            }
        else:
            error_msg = stderr.decode().strip()
            return {
                "connected": False,
                "success": False,  # Frontend compatibility
                "message": f"SSH connection failed: {error_msg}",
                "os_info": None,
                "hostname": None
            }
    except Exception as e:
        return {
            "connected": False,
            "success": False,  # Frontend compatibility
            "message": f"SSH verification error: {str(e)}",
            "os_info": None,
            "hostname": None
        }