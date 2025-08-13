/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Generate minimal inventory for SSH setup between physical servers
 */

export function generateMinimalInventory() {
  // Get discovered servers from session storage
  const discoveredServers = JSON.parse(sessionStorage.getItem('discoveredServers') || '[]')
  
  if (!discoveredServers || discoveredServers.length === 0) {
    throw new Error('No servers discovered. Please complete server discovery first.')
  }
  
  // Get current user from session storage (set during sudo password verification)
  const currentUser = sessionStorage.getItem('systemUsername') || sessionStorage.getItem('currentUser') || 'ubuntu'
  
  // Create minimal inventory with just baremetal group
  const inventory = {
    all: {
      vars: {
        ansible_become_pass: "{{ lookup('env', 'ANSIBLE_BECOME_PASSWORD') }}"
      },
      children: {
        baremetal: {
          hosts: {}
        }
      }
    }
  }
  
  // Add each discovered server to baremetal group
  discoveredServers.forEach(server => {
    // Try multiple possible hostname fields
    const hostname = server.hostname || server.host || server.name || `server-${(server.ip_address || server.ip).replace(/\./g, '-')}`
    
    // Store both for display purposes
    inventory.all.children.baremetal.hosts[hostname] = {
      ansible_host: server.ip_address || server.ip,
      ansible_user: currentUser,
      display_hostname: server.hostname || server.host || server.name || hostname
    }
  })
  
  return inventory
}

export function minimalInventoryToYAML(inventory) {
  // Simple YAML generation for minimal inventory
  let yaml = '---\n'
  yaml += 'all:\n'
  
  // Add vars section if present
  if (inventory.all.vars) {
    yaml += '  vars:\n'
    for (const [key, value] of Object.entries(inventory.all.vars)) {
      // Check if value contains Jinja2 template syntax and needs quotes
      if (typeof value === 'string' && value.includes('{{')) {
        yaml += `    ${key}: "${value}"\n`
      } else {
        yaml += `    ${key}: ${value}\n`
      }
    }
  }
  
  yaml += '  children:\n'
  yaml += '    baremetal:\n'
  yaml += '      hosts:\n'
  
  const baremetalHosts = inventory.all.children.baremetal.hosts
  for (const [hostname, hostConfig] of Object.entries(baremetalHosts)) {
    yaml += `        ${hostname}:\n`
    yaml += `          ansible_host: ${hostConfig.ansible_host}\n`
    yaml += `          ansible_user: ${hostConfig.ansible_user}\n`
  }
  
  return yaml
}