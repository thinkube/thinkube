/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Dynamic Inventory Generator for Thinkube Installer
 * Generates Ansible inventory based on user configuration with dynamic network allocation
 */

export function generateDynamicInventory() {
  // Get all configuration from sessionStorage and localStorage
  const config = JSON.parse(localStorage.getItem('thinkube-config') || '{}')
  const networkConfiguration = JSON.parse(sessionStorage.getItem('networkConfiguration') || '{}')
  const clusterNodes = JSON.parse(sessionStorage.getItem('clusterNodes') || '[]')
  const gpuAssignments = JSON.parse(sessionStorage.getItem('gpuAssignments') || '{}')  // GPU assignments from Review
  const hardwareData = JSON.parse(sessionStorage.getItem('hardwareData') || '{}')  // Hardware detection data
  const deploymentType = sessionStorage.getItem('deploymentType')
  
  // Debug GPU assignments
  console.log('GPU Assignments:', gpuAssignments)
  console.log('Cluster Nodes:', clusterNodes)
  console.log('Hardware Data:', hardwareData)
  
  // Validate required configuration exists
  if (!networkConfiguration.networkConfig) {
    throw new Error('Network configuration is required. Please complete the network configuration step.')
  }
  
  if (!networkConfiguration.physicalServers || networkConfiguration.physicalServers.length === 0) {
    throw new Error('Baremetal server configuration is required.')
  }
  
  if (!config.domainName) {
    throw new Error('Domain name is required.')
  }
  
  // ZeroTier validation only required for overlay mode
  if (config.networkMode === 'overlay') {
    if (!config.zerotierNetworkId) {
      throw new Error('ZeroTier network ID is required for overlay mode.')
    }
    
    if (!config.zerotierApiToken) {
      throw new Error('ZeroTier API token is required for overlay mode.')
    }
  }
  
  const networkConfig = networkConfiguration.networkConfig
  const configuredPhysicalServers = networkConfiguration.physicalServers
  
  
  // Validate required network configuration
  if (!networkConfig.cidr) {
    throw new Error('Network CIDR is required.')
  }
  
  if (!networkConfig.gateway) {
    throw new Error('Network gateway is required.')
  }
  
  // ZeroTier network config validation only for overlay mode
  if (config.networkMode === 'overlay' && !networkConfig.zerotierCIDR) {
    throw new Error('ZeroTier CIDR is required for overlay mode.')
  }
  
  // Build inventory structure
  const inventory = {
    all: {
      vars: {
        // Global variables from user configuration
        domain_name: config.domainName,
        admin_username: 'tkadmin',
        system_username: config.systemUsername,
        auth_realm_username: 'thinkube',
        ansible_python_interpreter: '/usr/bin/python3',
        ansible_become_pass: "{{ lookup('env', 'ANSIBLE_BECOME_PASSWORD') }}",
        home: "{{ lookup('env', 'HOME') }}",
        
        // Network configuration (user-provided values only)
        network_cidr: networkConfig.cidr,
        network_gateway: networkConfig.gateway,
        dns_servers: ["8.8.8.8", "8.8.4.4"],
        dns_search_domains: [],  // No custom DNS search domains to prevent wildcard matching
        
        // Network mode
        network_mode: config.networkMode || 'overlay',
        
        // MetalLB configuration (conditional based on network mode)
        metallb_ip_start_octet: networkConfig.metallbStartOctet || "200",
        metallb_ip_end_octet: networkConfig.metallbEndOctet || "210",
        
        // Kubernetes configuration (will be configured later with MicroK8s)
        
        // Cloudflare configuration - token written directly to inventory
        cloudflare_api_token: sessionStorage.getItem('cloudflareToken') || '',
        
        // GitHub configuration
        github_org: config.githubOrg || sessionStorage.getItem('githubOrg') || '',
        github_token: sessionStorage.getItem('githubToken') || '',
        
        // Admin email for Let's Encrypt registration
        admin_email: config.adminEmail || 'admin@' + config.domainName
      },
      children: {
        // Architecture groups
        arch: {
          children: {
            x86_64: {
              hosts: {}
            },
            arm64: {
              hosts: {}
            }
          }
        },
        
        // Physical servers (baremetal)
        baremetal: {
          hosts: {},
          children: {
            headless: {
              hosts: {}
            },
            desktops: {
              hosts: {}
            },
            dgx: {
              hosts: {}
            }
          }
        },
        
        
        // MicroK8s groups
        microk8s: {
          children: {
            microk8s_control_plane: {
              hosts: {}
            },
            microk8s_workers: {
              hosts: {}
            }
          }
        },
        
        // ZeroTier nodes - all nodes that need ZeroTier
        zerotier_nodes: {
          hosts: {}
        },
        
        // Management group - where Ansible runs from
        management: {
          hosts: {}
        },
        
        // GPU passthrough VMs
        
        // Baremetal node GPU configuration
        baremetal_gpus: {
          vars: {}
        }
      }
    }
  }
  
  // Add ZeroTier configuration conditionally for overlay mode
  if (config.networkMode === 'overlay') {
    // Add ZeroTier-specific variables
    inventory.all.vars.zerotier_network_id = config.zerotierNetworkId
    inventory.all.vars.zerotier_api_token = config.zerotierApiToken
    inventory.all.vars.zerotier_cidr = networkConfig.zerotierCIDR
    
    // ZeroTier subnet prefix - extract from ZeroTier CIDR
    inventory.all.vars.zerotier_subnet_prefix = networkConfig.zerotierCIDR.split('/')[0].split('.').slice(0, 3).join('.') + '.'
    
    // Ingress IP configuration for overlay network
    inventory.all.vars.primary_ingress_ip_octet = networkConfig.primaryIngressOctet || "200"
    inventory.all.vars.secondary_ingress_ip_octet = networkConfig.secondaryIngressOctet || "201"
    inventory.all.vars.dns_external_ip_octet = networkConfig.dnsExternalOctet
    inventory.all.vars.primary_ingress_ip = networkConfig.zerotierCIDR.split('/')[0].split('.').slice(0, 3).join('.') + '.' + (networkConfig.primaryIngressOctet || "200")
    inventory.all.vars.secondary_ingress_ip = networkConfig.zerotierCIDR.split('/')[0].split('.').slice(0, 3).join('.') + '.' + (networkConfig.secondaryIngressOctet || "201")
  } else {
    // Local mode - use local network for ingress IPs
    inventory.all.vars.primary_ingress_ip_octet = networkConfig.primaryIngressOctet || "200"
    inventory.all.vars.secondary_ingress_ip_octet = networkConfig.secondaryIngressOctet || "201"
    inventory.all.vars.dns_external_ip_octet = networkConfig.dnsExternalOctet
    inventory.all.vars.primary_ingress_ip = networkConfig.cidr.split('/')[0].split('.').slice(0, 3).join('.') + '.' + (networkConfig.primaryIngressOctet || "200")
    inventory.all.vars.secondary_ingress_ip = networkConfig.cidr.split('/')[0].split('.').slice(0, 3).join('.') + '.' + (networkConfig.secondaryIngressOctet || "201")
  }
  
  // Add baremetal servers from network configuration
  configuredPhysicalServers.forEach(server => {
    const hostname = server.hostname
    const serverDef = {
      ansible_host: config.networkMode === 'overlay' ? server.zerotierIP : server.ip,
      lan_ip: server.ip,
      arch: 'x86_64',
      zerotier_enabled: config.networkMode === 'overlay'
    }
    
    // Only add ZeroTier IP if overlay mode is enabled
    if (config.networkMode === 'overlay') {
      serverDef.zerotier_ip = server.zerotierIP
    }
    
    // Special handling for local connection
    // The server discovery process should have marked which server is local
    // First check if this server was marked as local during discovery
    const discoveredServers = JSON.parse(sessionStorage.getItem('discoveredServers') || '[]')
    const discoveredServer = discoveredServers.find(s => 
      (s.hostname === hostname || s.host === hostname || s.ip === server.ip) && s.is_local
    )
    
    // ONLY set ansible_connection: local if we have explicit confirmation
    // that this server is the local machine (where the installer is running)
    if (discoveredServer?.is_local) {
      serverDef.ansible_connection = 'local'
    }
    // REMOVED: Do not assume first server is local - this causes issues
    // when the installer runs on a different machine
    
    // Determine if this host needs GPU passthrough configuration
    const assignedSlots = []
    
    // Since we no longer have VMs, all GPUs are for baremetal use
    // No GPU passthrough configuration needed
    
    const hasGPUPassthrough = assignedSlots.length > 0
    serverDef.configure_gpu_passthrough = hasGPUPassthrough
    
    // Add assigned PCI slots if any
    if (hasGPUPassthrough) {
      serverDef.assigned_pci_slots = assignedSlots
      console.log(`Host ${hostname} configured for GPU passthrough with slots: ${assignedSlots}`)
    }
    
    // Add to inventory
    inventory.all.children.baremetal.hosts[hostname] = serverDef
    
    // Add to architecture group
    inventory.all.children.arch.children[serverDef.arch].hosts[hostname] = {}
    
    // Add to management group if it has local connection (is the installer host)
    if (serverDef.ansible_connection === 'local') {
      inventory.all.children.management.hosts[hostname] = {}
      // Assume the local host is a desktop (since we're running the installer GUI on it)
      inventory.all.children.baremetal.children.desktops.hosts[hostname] = {}
    } else {
      // Other servers are headless
      inventory.all.children.baremetal.children.headless.hosts[hostname] = {}
    }
    
    // Add to zerotier_nodes if zerotier is enabled (overlay mode)
    if (serverDef.zerotier_enabled) {
      inventory.all.children.zerotier_nodes.hosts[hostname] = {}
    }
  })
  
  
  // Add Kubernetes nodes based on clusterNodes assignments
  // Add Kubernetes nodes - only baremetal nodes supported (no VMs/LXD)
  clusterNodes.forEach((node) => {
    // Skip any VM nodes since LXD is not available
    if (node.type === 'vm') {
      console.warn(`Skipping VM node ${node.hostname} - VM support removed (no LXD)`)
      return
    }
    
    if (node.role === 'control_plane') {
      inventory.all.children.microk8s.children.microk8s_control_plane.hosts[node.hostname] = {}
    } else if (node.role === 'worker') {
      inventory.all.children.microk8s.children.microk8s_workers.hosts[node.hostname] = {}
    }
  })
  
  
  // Configure GPU detection for GPU operator
  configuredPhysicalServers.forEach(server => {
    // Get hardware info from stored data
    const serverHardware = JSON.parse(sessionStorage.getItem('serverHardware') || '[]')
    const hwInfo = serverHardware.find(s => s.hostname === server.hostname)
    
    if (hwInfo && hwInfo.hardware && hwInfo.hardware.gpu_detected) {
      // Store GPU info for the inventory
      const gpuInfo = {
        gpu_detected: true,
        gpu_count: hwInfo.hardware.gpu_count || 0,
        gpu_model: hwInfo.hardware.gpu_model || 'Unknown GPU'
      }
      
      // Add to baremetal_gpus group if GPUs are detected
      if (gpuInfo.gpu_count > 0) {
        if (!inventory.all.children.baremetal_gpus.hosts) {
          inventory.all.children.baremetal_gpus.hosts = {}
        }
        inventory.all.children.baremetal_gpus.hosts[server.hostname] = {
          gpu_count: gpuInfo.gpu_count,
          gpu_model: gpuInfo.gpu_model
        }
      }
    }
  })
  
  // Check if we're running from an external controller
  // If no physical server was marked as local, add a controller entry
  const discoveredServers = JSON.parse(sessionStorage.getItem('discoveredServers') || '[]')
  const hasLocalServer = configuredPhysicalServers.some(server => {
    const discoveredServer = discoveredServers.find(s => 
      (s.hostname === server.hostname || s.host === server.hostname || s.ip === server.ip) && s.is_local
    )
    return discoveredServer?.is_local
  })
  
  if (!hasLocalServer && configuredPhysicalServers.length > 0) {
    // We're running from an external controller
    // Add controller entry to enable proper management and ZeroTier access
    // 🤖 Controller IP is now configured in UI to prevent conflicts
    const controllerIP = window.location.hostname || 'controller'
    
    // Add controller as a special host
    // Detect architecture from user agent or navigator platform
    let controllerArch = 'x86_64'  // Default to x86_64
    const platform = navigator.platform?.toLowerCase() || ''
    const userAgent = navigator.userAgent?.toLowerCase() || ''
    
    if (platform.includes('arm') || userAgent.includes('arm') || userAgent.includes('aarch64')) {
      controllerArch = 'arm64'
    }
    
    // Get controller ZeroTier IP from network configuration (only needed for overlay mode)
    let controllerZerotierIP = null
    if (config.networkMode === 'overlay') {
      const zerotierPrefix = networkConfig.zerotierCIDR.split('/')[0].split('.').slice(0, 3).join('.')
      controllerZerotierIP = networkConfig.controllerZerotierIP || `${zerotierPrefix}.10` // fallback to .10 for backwards compatibility
    }
    
    const controllerDef = {
      ansible_connection: 'local',
      ansible_host: '127.0.0.1',
      lan_ip: controllerIP !== 'localhost' ? controllerIP : '127.0.0.1',
      zerotier_enabled: config.networkMode === 'overlay',
      arch: controllerArch
    }
    
    // Only add ZeroTier IP if overlay mode is enabled
    if (config.networkMode === 'overlay') {
      controllerDef.zerotier_ip = controllerZerotierIP
    }
    
    // Add controller to inventory
    inventory.all.children.management.hosts.controller = controllerDef
    if (config.networkMode === 'overlay') {
      inventory.all.children.zerotier_nodes.hosts.controller = {}
    }
    inventory.all.children.arch.children[controllerArch].hosts.controller = {}
    
    console.log('External controller detected, added to inventory:', controllerDef)
  }
  
  return inventory
}

/**
 * Convert inventory object to YAML format
 */
export function inventoryToYAML(inventory) {
  // Simple YAML serializer for inventory
  const yaml = []
  yaml.push('---')
  yaml.push('# Dynamically generated inventory by Thinkube Installer')
  yaml.push('')
  
  function indent(level) {
    return '  '.repeat(level)
  }
  
  function writeObject(obj, level = 0) {
    Object.entries(obj).forEach(([key, value]) => {
      if (value === null || value === undefined) return
      
      if (typeof value === 'object' && !Array.isArray(value)) {
        yaml.push(`${indent(level)}${key}:`)
        writeObject(value, level + 1)
      } else if (Array.isArray(value)) {
        yaml.push(`${indent(level)}${key}:`)
        value.forEach(item => {
          if (typeof item === 'object' && item !== null) {
            // Handle objects in arrays
            yaml.push(`${indent(level + 1)}-`)
            Object.entries(item).forEach(([itemKey, itemValue]) => {
              if (typeof itemValue === 'string') {
                yaml.push(`${indent(level + 2)}${itemKey}: "${itemValue}"`)
              } else if (typeof itemValue === 'boolean') {
                yaml.push(`${indent(level + 2)}${itemKey}: ${itemValue}`)
              } else {
                yaml.push(`${indent(level + 2)}${itemKey}: ${itemValue}`)
              }
            })
          } else if (typeof item === 'string' && item.match(/^\d+:\d+\.\d+$/)) {
            yaml.push(`${indent(level + 1)}- "${item}"`)
          } else if (typeof item === 'string') {
            yaml.push(`${indent(level + 1)}- "${item}"`)
          } else {
            yaml.push(`${indent(level + 1)}- ${item}`)
          }
        })
      } else if (typeof value === 'string' && value.includes('{{')) {
        // Quote Jinja2 variables for proper YAML parsing
        yaml.push(`${indent(level)}${key}: "${value}"`)
      } else if (typeof value === 'string') {
        yaml.push(`${indent(level)}${key}: "${value}"`)
      } else {
        yaml.push(`${indent(level)}${key}: ${value}`)
      }
    })
  }
  
  writeObject(inventory)
  return yaml.join('\n')
}