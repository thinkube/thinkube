# Network Discovery Options for Ubuntu Devices

## Overview
Discovering Ubuntu devices on a local network can be accomplished through various methods, each with trade-offs between accuracy, speed, and requirements.

## Discovery Methods

### 1. ARP Scan + SSH Banner Grabbing
**Most Practical Approach**

```python
# Step 1: ARP scan to find all devices
import subprocess
import asyncio
import socket

async def arp_scan(network="10.0.1.0/24"):
    """Find all active IPs on the network"""
    # Requires: apt install arp-scan
    cmd = ["sudo", "arp-scan", "-l", "-I", "eth0", network]
    result = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE)
    stdout, _ = await result.communicate()
    
    # Parse IPs from output
    ips = []
    for line in stdout.decode().split('\n'):
        if '\t' in line:
            ip = line.split('\t')[0]
            if ip.count('.') == 3:  # Valid IP
                ips.append(ip)
    return ips

async def check_ssh_banner(ip, port=22, timeout=3):
    """Check if SSH is running and get banner"""
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
        
        # Ubuntu SSH banner typically contains "Ubuntu"
        banner_str = banner.decode('utf-8', errors='ignore')
        if 'Ubuntu' in banner_str:
            return True, banner_str
        return False, banner_str
        
    except:
        return False, None

async def discover_ubuntu_servers(network="10.0.1.0/24"):
    """Discover Ubuntu servers on the network"""
    print(f"Scanning network {network}...")
    
    # Get all IPs
    ips = await arp_scan(network)
    print(f"Found {len(ips)} active devices")
    
    # Check each for SSH
    ubuntu_servers = []
    tasks = []
    
    for ip in ips:
        tasks.append(check_ssh_banner(ip))
    
    results = await asyncio.gather(*tasks)
    
    for ip, (is_ubuntu, banner) in zip(ips, results):
        if is_ubuntu:
            ubuntu_servers.append({
                'ip': ip,
                'banner': banner,
                'os': 'Ubuntu'
            })
    
    return ubuntu_servers
```

### 2. Nmap OS Detection
**More Accurate but Slower**

```python
async def nmap_os_detection(network="10.0.1.0/24"):
    """Use nmap for OS detection"""
    # Requires: apt install nmap
    # Note: OS detection requires root
    cmd = [
        "sudo", "nmap", 
        "-sS",  # SYN scan
        "-O",   # OS detection
        "-T4",  # Faster timing
        "--osscan-limit",  # Only scan promising hosts
        network
    ]
    
    result = await asyncio.create_subprocess_exec(
        *cmd, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, _ = await result.communicate()
    
    # Parse nmap output for Ubuntu systems
    ubuntu_hosts = []
    current_host = None
    
    for line in stdout.decode().split('\n'):
        if 'Nmap scan report for' in line:
            # Extract IP
            parts = line.split()
            current_host = parts[-1].strip('()')
        elif 'OS details:' in line and 'Ubuntu' in line:
            if current_host:
                ubuntu_hosts.append({
                    'ip': current_host,
                    'os_details': line.split(':', 1)[1].strip()
                })
    
    return ubuntu_hosts
```

### 3. mDNS/Avahi Discovery
**Works if Avahi is installed (default on Ubuntu Desktop)**

```python
async def mdns_discovery():
    """Discover Ubuntu systems via mDNS"""
    # Requires: apt install avahi-utils
    cmd = ["avahi-browse", "-a", "-t", "-r", "-p"]
    
    result = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE
    )
    stdout, _ = await result.communicate()
    
    # Parse for workstation services (Ubuntu desktops advertise these)
    ubuntu_hosts = []
    for line in stdout.decode().split('\n'):
        if '_workstation._tcp' in line:
            parts = line.split(';')
            if len(parts) > 7:
                hostname = parts[3]
                ip = parts[7]
                ubuntu_hosts.append({
                    'hostname': hostname,
                    'ip': ip,
                    'type': 'desktop'
                })
    
    return ubuntu_hosts
```

### 4. DHCP Lease Analysis
**If you have access to the DHCP server**

```python
def parse_dhcp_leases(lease_file="/var/lib/dhcp/dhcpd.leases"):
    """Parse DHCP leases for Ubuntu systems"""
    # Look for Ubuntu in hostname or vendor-class-identifier
    with open(lease_file, 'r') as f:
        content = f.read()
    
    # Parse lease blocks
    leases = []
    for block in content.split('lease '):
        if 'ubuntu' in block.lower():
            # Extract IP and hostname
            lines = block.split('\n')
            ip = lines[0].split()[0]
            hostname = None
            
            for line in lines:
                if 'client-hostname' in line:
                    hostname = line.split('"')[1]
                    break
            
            leases.append({
                'ip': ip,
                'hostname': hostname
            })
    
    return leases
```

### 5. Combined Approach for Installer

```python
class UbuntuDiscovery:
    """Combined discovery approach for the installer"""
    
    async def discover_all(self, network="10.0.1.0/24"):
        """Use multiple methods to find Ubuntu systems"""
        discovered = {}
        
        # Method 1: Quick SSH scan
        print("Scanning for SSH servers...")
        ssh_hosts = await self.ssh_scan(network)
        for host in ssh_hosts:
            discovered[host['ip']] = host
        
        # Method 2: mDNS (for desktops)
        print("Checking mDNS announcements...")
        mdns_hosts = await self.mdns_discovery()
        for host in mdns_hosts:
            if host['ip'] in discovered:
                discovered[host['ip']].update(host)
            else:
                discovered[host['ip']] = host
        
        # Method 3: Deeper scan for uncertain hosts
        uncertain_ips = [
            ip for ip in discovered 
            if not discovered[ip].get('confirmed_ubuntu')
        ]
        
        if uncertain_ips:
            print(f"Performing OS detection on {len(uncertain_ips)} hosts...")
            # Use nmap on uncertain hosts only
            
        return list(discovered.values())
    
    def filter_candidates(self, hosts):
        """Filter to likely Ubuntu 24.04 servers"""
        candidates = []
        
        for host in hosts:
            # Check various indicators
            score = 0
            
            # SSH banner mentions Ubuntu
            if 'Ubuntu' in host.get('banner', ''):
                score += 10
                
            # Has Ubuntu in hostname
            if 'ubuntu' in host.get('hostname', '').lower():
                score += 5
                
            # Has workstation service (desktop)
            if host.get('type') == 'desktop':
                score += 3
                
            # SSH is running
            if host.get('ssh_available'):
                score += 2
            
            if score >= 5:  # Likely Ubuntu
                host['confidence'] = score
                candidates.append(host)
        
        return sorted(candidates, key=lambda x: x['confidence'], reverse=True)
```

## UI Integration

### Discovery Screen

```
=== Network Discovery ===

Scanning your network for Ubuntu servers...

[████████████████████░░░░] 75% - Checking 10.0.1.75

Found Servers:
┌─────────────────────────────────────────────────┐
│ ✓ 10.0.1.101 - Ubuntu 24.04.2 LTS           │
│   Hostname: bcn1                                │
│   Type: Desktop (SSH available)                 │
│   [Select]                                      │
├─────────────────────────────────────────────────┤
│ ✓ 10.0.1.102 - Ubuntu Server                │
│   Hostname: bcn2                                │
│   Type: Server (SSH available)                  │
│   [Select]                                      │
├─────────────────────────────────────────────────┤
│ ? 10.0.1.150 - Possible Ubuntu              │
│   SSH available, OS unclear                     │
│   [Verify]                                      │
└─────────────────────────────────────────────────┘

[Scan Again] [Manual Entry] [Continue with Selected]
```

## Recommendations for Thinkube

### Recommended Approach: Hybrid Discovery

1. **Quick Scan First** (1-5 seconds)
   - ARP scan for active IPs
   - Concurrent SSH banner check
   - mDNS query for desktop systems

2. **Present Results with Confidence Levels**
   - ✓ Confirmed Ubuntu (SSH banner says Ubuntu)
   - ? Possible Ubuntu (SSH available, needs verification)
   - ○ Unknown (active IP, no SSH)

3. **Allow Manual Addition**
   - Users can add IPs not discovered
   - Useful for firewalled systems

4. **Verification Step**
   - For selected hosts, verify Ubuntu 24.04
   - Test SSH connectivity
   - Check sudo access

### Implementation Considerations

1. **Permissions**
   - ARP scan requires sudo on control node
   - Can fallback to ping sweep if no sudo

2. **Network Segments**
   - Allow scanning multiple subnets
   - Handle VLANs appropriately

3. **Security**
   - Don't be too aggressive (no port scans)
   - Respect firewall rules
   - Allow opt-out of discovery

4. **Performance**
   - Concurrent checks for speed
   - Timeout aggressive (2-3 seconds)
   - Show progress to user

### Example Implementation for Installer

```python
@app.post("/api/discover-servers")
async def discover_servers(request: DiscoveryRequest):
    """Discover Ubuntu servers on the network"""
    try:
        discovery = UbuntuDiscovery()
        
        # Quick discovery
        hosts = await discovery.discover_all(request.network_cidr)
        
        # Filter to likely candidates
        candidates = discovery.filter_candidates(hosts)
        
        return {
            "servers": candidates,
            "total_scanned": len(hosts),
            "scan_time": discovery.scan_time
        }
        
    except PermissionError:
        return {
            "error": "Sudo access required for network scanning",
            "fallback": "manual_entry"
        }
```

This provides a good balance between automation and user control.