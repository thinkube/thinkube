/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold mb-6 text-base-content">Review Configuration</h1>
    
    <!-- Cluster Settings -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Cluster Settings</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p class="text-sm text-base-content text-opacity-60 font-medium">Cluster Name</p>
            <p class="font-semibold text-base-content">{{ config.clusterName }}</p>
          </div>
          <div>
            <p class="text-sm text-base-content text-opacity-60 font-medium">Domain Name</p>
            <p class="font-semibold text-base-content">{{ config.domainName }}</p>
          </div>
          <div>
            <p class="text-sm text-base-content text-opacity-60 font-medium">Admin Username</p>
            <p class="font-semibold text-base-content">{{ config.adminUsername || 'tkadmin' }}</p>
          </div>
          <div>
            <p class="text-sm text-base-content text-opacity-60 font-medium">Network Mode</p>
            <p class="font-semibold text-base-content">{{ config.networkMode === 'overlay' ? 'ZeroTier Overlay' : 'Local Network' }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Node Assignments -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Node Assignments</h2>
        
        <div class="space-y-3">
          <div v-for="node in allNodes" :key="node.id" class="border border-base-300 rounded-lg p-4 hover:bg-base-200/20 transition-colors">
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <h3 class="font-semibold text-lg text-base-content">{{ node.hostname }}</h3>
                <p class="text-sm text-base-content text-opacity-60">
                  Baremetal Server
                </p>
                
                <!-- Hardware specs -->
                <div class="text-sm mt-2 text-base-content text-opacity-80">
                  <div>
                    <span class="font-medium">{{ node.cpu || 0 }}</span> CPU cores, 
                    <span class="font-medium">{{ Math.round(node.memory || 0) }}</span> GB RAM,
                    <span class="font-medium">{{ Math.round(node.disk || 0) }}</span> GB Storage
                  </div>
                </div>
                
                <!-- Network information -->
                <div class="text-sm mt-2 space-y-1">
                  <div v-if="node.zerotierIP">
                    <span class="text-base-content text-opacity-60">ZeroTier:</span> 
                    <span class="font-mono">{{ node.zerotierIP }}</span>
                  </div>
                  <div v-if="node.localIP">
                    <span class="text-base-content text-opacity-60">Local:</span> 
                    <span class="font-mono">{{ node.localIP }}</span>
                  </div>
                </div>
                
                <!-- GPU information -->
                <div v-if="node.hasGPU && node.gpuInfo" class="mt-2">
                  <p class="text-sm font-medium text-base-content text-opacity-80">GPU:</p>
                  <div class="text-sm text-base-content text-opacity-70 ml-2">
                    {{ node.gpuInfo.gpu_count }}x {{ node.gpuInfo.gpu_model }}
                  </div>
                </div>
              </div>
              <div class="badge badge-lg" :class="getRoleBadgeClass(node.role)">
                {{ getRoleDisplay(node.role) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>


    <!-- Generated Inventory -->
    <div v-if="generatedInventory" class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Generated Ansible Inventory</h2>
        <div class="prose prose-sm max-w-none mb-4">
          <p class="text-base-content text-opacity-80">
            Your configuration has been converted to an Ansible inventory file. You can download this for manual playbook execution.
          </p>
        </div>
        
        <div class="flex gap-3">
          <button class="btn btn-outline btn-sm" @click="copyInventory">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
            </svg>
            Copy
          </button>
          
          <button class="btn btn-outline btn-sm" @click="downloadInventory">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            Download inventory.yaml
          </button>
          
          <button class="btn btn-outline btn-sm" @click="viewInventory">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
            </svg>
            View
          </button>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex justify-between">
      <button class="btn btn-ghost gap-2" @click="$router.push('/network-configuration')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
        Back to Network Configuration
      </button>
      
      <button 
        class="btn btn-primary gap-2"
        @click="startDeployment"
      >
        Start Deployment
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </button>
    </div>

    <!-- Inventory View Modal -->
    <dialog ref="inventoryModal" class="modal">
      <div class="modal-box w-11/12 max-w-5xl">
        <h3 class="font-bold text-lg mb-4">Ansible Inventory</h3>
        
        <div class="mockup-code bg-base-200 text-sm max-h-96 overflow-auto">
          <pre><code>{{ generatedInventory }}</code></pre>
        </div>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="closeInventoryModal">Close</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// State
const config = ref({})
const allNodes = ref([])
const deploymentType = ref('')
const gpuAssignments = ref({})
const generatedInventory = ref('')
const inventoryModal = ref(null)

// Computed
const hasGPUs = computed(() => {
  // Check if there are any GPU assignments that are not 'baremetal'
  return Object.keys(gpuAssignments.value).some(key => gpuAssignments.value[key] !== 'baremetal')
})

// Get role display text
const getRoleDisplay = (role) => {
  const roleMap = {
    'control_plane': 'Control Plane',
    'worker': 'Worker',
    'dns': 'DNS Server'
  }
  return roleMap[role] || role
}

// Get role badge class
const getRoleBadgeClass = (role) => {
  const classMap = {
    'control_plane': 'badge-primary',
    'worker': 'badge-secondary',
    'dns': 'badge-accent'
  }
  return classMap[role] || 'badge-ghost'
}

// Get GPUs assigned to a specific node
const getNodeGPUs = (nodename) => {
  const nodeGPUs = []
  const serverHardware = JSON.parse(sessionStorage.getItem('serverHardware') || '[]')
  
  // Check for GPUs physically on this node (baremetal only)
  if (allNodes.value.find(n => n.hostname === nodename && n.type === 'baremetal')) {
    const server = serverHardware.find(s => s.hostname === nodename)
    if (server?.hardware?.gpu_passthrough_info) {
      server.hardware.gpu_passthrough_info.forEach(gpu => {
        // Only show GPUs that remain on this host or are not assigned to VMs
        const assignment = gpuAssignments.value[gpu.pci_address]
        if (!assignment || assignment === 'baremetal') {
          nodeGPUs.push({
            address: gpu.pci_address,
            name: server.hardware.gpu_model?.replace(/^\d+x\s*/, '') || 'Unknown GPU',
            hostname: nodename,
            assignment: 'baremetal'
          })
        }
      })
    }
  }
  
  // Check for GPUs passed through to this node (VMs)
  Object.entries(gpuAssignments.value).forEach(([pciAddress, assignment]) => {
    if (assignment === nodename) {
      // Find the GPU info
      let foundServer = null
      for (const server of serverHardware) {
        if (server.hardware?.gpu_passthrough_info) {
          const gpu = server.hardware.gpu_passthrough_info.find(g => g.pci_address === pciAddress)
          if (gpu) {
            foundServer = server
            break
          }
        }
      }
      
      if (foundServer) {
        nodeGPUs.push({
          address: pciAddress,
          name: foundServer.hardware.gpu_model?.replace(/^\d+x\s*/, '') || 'Unknown GPU',
          hostname: foundServer.hostname,
          assignment: assignment
        })
      }
    }
  })
  
  return nodeGPUs
}

// Inventory methods
const copyInventory = async () => {
  try {
    await navigator.clipboard.writeText(generatedInventory.value)
    alert('Inventory copied to clipboard!')
  } catch (error) {
    alert('Failed to copy to clipboard: ' + error.message)
  }
}

const downloadInventory = () => {
  const blob = new Blob([generatedInventory.value], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'inventory.yaml'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const viewInventory = () => {
  inventoryModal.value.showModal()
}

const closeInventoryModal = () => {
  inventoryModal.value.close()
}

// Start deployment
const startDeployment = () => {
  // Navigate to deployment
  router.push('/deploy')
}

// Load configuration
onMounted(async () => {
  // Load saved configuration
  config.value = JSON.parse(localStorage.getItem('thinkube-config') || '{}')
  
  // Load deployment type
  // Since we only have baremetal servers now, deployment type is 'baremetal'
  deploymentType.value = 'baremetal'
  
  // Load nodes from role assignment
  const clusterNodes = JSON.parse(sessionStorage.getItem('clusterNodes') || '[]')
  
  // Load hardware info for baremetal nodes
  const serverHardware = JSON.parse(sessionStorage.getItem('serverHardware') || '[]')
  
  // Load network configuration
  const networkConfig = JSON.parse(sessionStorage.getItem('networkConfiguration') || '{}')
  const physicalServers = networkConfig.physicalServers || []
  
  // Merge hardware info with cluster nodes
  allNodes.value = clusterNodes.map(node => {
    if (node.type === 'baremetal') {
      const hwInfo = serverHardware.find(s => s.hostname === node.hostname)
      const networkInfo = physicalServers.find(s => s.hostname === node.hostname)
      
      const result = {
        ...node,
        cpu: node.cpu || hwInfo?.hardware?.cpu_cores || 0,
        memory: node.memory || hwInfo?.hardware?.memory_gb || 0,
        disk: node.disk || hwInfo?.hardware?.disk_gb || 0,
        hasGPU: hwInfo?.hardware?.gpu_detected || false,
        zerotierIP: networkInfo?.zerotierIP || networkInfo?.ip || '',
        localIP: networkInfo?.localIP || hwInfo?.network?.ip_address || ''
      }
      
      if (hwInfo?.hardware?.gpu_detected) {
        result.gpuInfo = {
          gpu_count: hwInfo.hardware.gpu_count || 0,
          gpu_model: hwInfo.hardware.gpu_model || '',
          gpu_passthrough_info: hwInfo.hardware.gpu_passthrough_info || [],
          iommu_enabled: hwInfo.hardware.iommu_enabled || false,
          gpu_passthrough_eligible_count: hwInfo.hardware.gpu_passthrough_eligible_count || 0
        }
      }
      
      return result
    }
    return node
  })
  
  // Load GPU assignments from previous step
  const savedAssignments = JSON.parse(sessionStorage.getItem('gpuAssignments') || '{}')
  gpuAssignments.value = savedAssignments
  
  // Update nodes with GPU data from nodeConfiguration
  const nodeConfig = JSON.parse(sessionStorage.getItem('nodeConfiguration') || '[]')
  allNodes.value = allNodes.value.map(node => {
    const configNode = nodeConfig.find(n => n.hostname === node.hostname)
    if (configNode?.gpus) {
      return { ...node, gpus: configNode.gpus }
    }
    return node
  })
  
  // Generate fresh inventory with GPU assignments
  try {
    const { generateDynamicInventory, inventoryToYAML } = await import('../utils/inventoryGenerator.js')
    const inventory = generateDynamicInventory()
    generatedInventory.value = inventoryToYAML(inventory)
    // Save the updated inventory
    sessionStorage.setItem('generatedInventory', generatedInventory.value)
    // Also save to localStorage for future skip-config runs
    localStorage.setItem('thinkube-last-inventory', generatedInventory.value)
  } catch (error) {
    console.error('Failed to generate inventory:', error)
    // Fall back to saved inventory if generation fails
    generatedInventory.value = sessionStorage.getItem('generatedInventory') || ''
  }
})
</script>

<style scoped>
.inventory-preview {
  font-family: monospace;
  font-size: 0.875rem;
  background-color: #f5f5f5;
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
}
</style>