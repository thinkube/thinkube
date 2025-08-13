# ZeroTier and DNS Network Configuration

This directory contains playbooks for configuring ZeroTier networking and DNS services for the Thinkube platform.

## Playbook Overview

### 10_setup_zerotier.yaml
- **Purpose**: Complete ZeroTier setup in a single playbook
- **What it does**:
  - Installs ZeroTier package on all nodes in `zerotier_nodes` group one at a time
  - Joins each node to the ZeroTier network
  - Automatically authorizes nodes and assigns IPs via the ZeroTier API
  - Assigns additional IPs for MetalLB and ingress services on control plane nodes
  - Configures IP forwarding and firewall rules
  - Maintains existing network-wide settings to preserve other ZeroTier nodes
  - Processes one node at a time from start to finish
  - Uses `serial: 1` to ensure each node is fully configured before moving to the next

### 18_test_zerotier.yaml
- **Purpose**: Tests ZeroTier connectivity between nodes
- **What it does**:
  - Verifies ZeroTier is properly installed and running
  - Tests connectivity between nodes over ZeroTier network
  - Validates that routes are properly configured
  - Performs network performance tests using iperf3
  - Reports comprehensive test results with detailed diagnostics

### 19_reset_zerotier.yaml
- **Purpose**: Rolls back ZeroTier configuration if needed
- **What it does**:
  - Leaves the ZeroTier network on all nodes
  - Removes specified nodes from the network
  - Optionally uninstalls ZeroTier
  - Preserves the ZeroTier network itself for other nodes

### 20_setup_dns.yaml
- **Purpose**: Sets up DNS server for service discovery
- **What it does**:
  - Installs bind9 DNS server on the dns1 VM
  - Configures DNS zones and records for the main domain
  - Sets up wildcard records for service access
  - Creates Knative subdomain (kn.domain.com) for serverless applications
  - Configures resolver settings and DNS forwarders
  - Points wildcard domains to appropriate MetalLB ingress IPs

### 25_configure_dns_clients.yaml
- **Purpose**: Configures DNS resolution on all nodes
- **What it does**:
  - Configures all nodes to use the ZeroTier DNS server
  - Sets up systemd-resolved with proper domain routing
  - Ensures MicroK8s nodes use CoreDNS for internal resolution
  - Verifies DNS resolution works on all nodes

### 28_test_dns.yaml
- **Purpose**: Tests DNS resolution across all nodes
- **What it does**:
  - Verifies DNS server is running and reachable
  - Tests domain name resolution for all key domains
  - Validates wildcard records for services and Knative
  - Gracefully handles network connectivity issues
  - Provides detailed diagnostics for troubleshooting

### 29_reset_dns.yaml
- **Purpose**: Rolls back DNS configuration if needed
- **What it does**:
  - Removes bind9 configuration and zone files
  - Restores default resolver settings
  - Optionally reinstalls bind9 with clean configuration

## Order of Execution

The correct order to run these playbooks is:

1. **Setup**: `10_setup_zerotier.yaml` - Complete ZeroTier installation and configuration
2. **Test**: `18_test_zerotier.yaml` - Verify ZeroTier connectivity
3. **Setup**: `20_setup_dns.yaml` - Configure DNS server
4. **Test**: `28_test_dns.yaml` - Verify DNS resolution

## Special Configurations

### MetalLB and Ingress IP Configuration
- The ZeroTier setup assigns additional IPs to control plane node for MetalLB:
  - `10.0.191.200` - Primary ingress controller IP
  - `10.0.191.201` - Knative ingress controller IP
- DNS wildcard records are configured to point to these IPs:
  - `*.thinkube.com` → `10.0.191.200`
  - `*.kn.thinkube.com` → `10.0.191.201`

### DNS Configuration
The DNS server provides the following key functions:
- Forward DNS for the `thinkube.com` domain
- Wildcard DNS for dynamically created services
- Special subdomain for Knative serverless applications
- External DNS resolution for internet domains

## Testing and Validation

After running the playbooks, you can verify the setup:
- Check ZeroTier membership: `zerotier-cli listnetworks`
- Check node authorization status: `zerotier-cli listnetworks | grep "OK"`
- Check assigned IPs: `zerotier-cli listnetworks | grep "10.0.191"`
- Check DNS resolution: `dig @10.0.191.1 test.thinkube.com`
- Test wildcard domains: `dig @10.0.191.1 anything.thinkube.com`
- Test Knative domains: `dig @10.0.191.1 function.kn.thinkube.com`

## Environment Variables

Make sure to set the following environment variables before running the playbooks:
- `ZEROTIER_NETWORK_ID`: Your ZeroTier network ID
- `ZEROTIER_API_TOKEN`: Your ZeroTier API token for Central access

You can set these by adding them to your `~/.env` file:
```bash
export ZEROTIER_NETWORK_ID=93afae59634c1a70
export ZEROTIER_API_TOKEN=your_api_token_here
```

## Known Issues and Troubleshooting

### ZeroTier Connectivity Issues
- ICMP (ping) may be blocked between some ZeroTier nodes
- Adjust firewall settings if needed to allow UDP port 9993 for ZeroTier traffic
- Ensure each node has properly assigned IPs with `zerotier-cli listnetworks`

### DNS Resolution Issues
- UDP port 53 traffic may be blocked between nodes
- The DNS test playbook may show connectivity failures even if DNS is working
- Try using the DNS server directly from each node with: `dig @10.0.191.1 thinkube.com`

## Lessons Learned

### ZeroTier Configuration
- **Use caution with Central API**: The ZeroTier API can make global changes that affect all nodes
- **Serial execution**: Process one node at a time with `serial: 1` for more reliable results
- **Flow-based approach**: Complete all operations for one node before moving to the next
- **Preserve existing settings**: Avoid modifying network-wide settings that may affect other nodes

### DNS Server Configuration
- **Bind9 service**: After configuration, always reload the Bind9 service
- **Zone file newlines**: Ensure zone files end with newlines to avoid bind9 warnings
- **UDP traffic**: DNS requires UDP port 53 traffic to be allowed between nodes
- **Check logs**: Use `journalctl -u named` to check for Bind9 issues
- **Test from server**: Verify resolution on the DNS server itself first

### Playbook Design
- **Check mode support**: Ensure playbooks work in check mode with appropriate `check_mode: false`
- **Fail-fast approach**: Use early checks to ensure requirements are met
- **Graceful degradation**: Handle connectivity issues without failing the playbook
- **Detailed diagnostics**: Provide clear error messages and troubleshooting recommendations