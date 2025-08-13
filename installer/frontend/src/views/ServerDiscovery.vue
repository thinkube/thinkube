/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold mb-6">Server Discovery</h1>
    
    <!-- Network Mode Selection -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Network Mode</h2>
        <p class="text-sm text-base-content text-opacity-70 mb-4">
          Choose how to discover your servers. ZeroTier is recommended for distributed nodes.
        </p>
        
        <div class="form-control">
          <div class="flex flex-col gap-2">
            <label class="label cursor-pointer justify-start gap-4">
              <input 
                v-model="networkMode" 
                type="radio" 
                name="networkMode" 
                value="overlay" 
                class="radio radio-primary" 
                @change="onNetworkModeChange"
              />
              <div class="flex flex-col">
                <span class="label-text font-medium">Overlay Network (ZeroTier) - Recommended</span>
                <span class="label-text-alt text-sm">Discover nodes on your ZeroTier network</span>
              </div>
            </label>
            <label class="label cursor-pointer justify-start gap-4">
              <input 
                v-model="networkMode" 
                type="radio" 
                name="networkMode" 
                value="local" 
                class="radio radio-primary" 
                @change="onNetworkModeChange"
              />
              <div class="flex flex-col">
                <span class="label-text font-medium">Local Network</span>
                <span class="label-text-alt text-sm">Scan your local network for Ubuntu servers</span>
              </div>
            </label>
          </div>
        </div>
        
      </div>
    </div>
    
    <!-- Discovery Controls -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">{{ networkMode === 'overlay' ? 'Discover ZeroTier Nodes' : 'Scan Network for Ubuntu Servers' }}</h2>
        
        <div class="mb-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">{{ networkMode === 'overlay' ? 'ZeroTier Network CIDR' : 'Network CIDR' }}</span>
              <span class="label-text-alt">{{ networkMode === 'overlay' ? 'e.g., 172.30.0.0/24' : 'e.g., 192.168.1.0/24' }}</span>
            </label>
            <input 
              v-model="networkCIDR" 
              type="text" 
              :placeholder="networkMode === 'overlay' ? 'Enter your ZeroTier network CIDR' : '192.168.1.0/24'" 
              class="input input-md"
              :disabled="isScanning"
            />
          </div>
        </div>
        
        <div class="flex items-center gap-4">
          <button 
            class="btn btn-primary"
            @click="startDiscovery"
            :disabled="isScanning"
          >
            <span v-if="isScanning" class="loading loading-spinner"></span>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
            {{ isScanning ? 'Discovering...' : networkMode === 'overlay' ? 'Discover ZeroTier Nodes' : 'Start Network Scan' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- Scanning Progress -->
    <div v-if="isScanning" class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <div class="flex items-center gap-4">
          <div class="radial-progress text-primary" :style="`--value:${Math.round(scanProgress)};`">
            {{ Math.round(scanProgress) }}%
          </div>
          <div class="flex-1">
            <p class="text-lg font-semibold">Scanning Network...</p>
            <p class="text-sm text-base-content text-opacity-70">{{ scanStatus }}</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Discovered Servers -->
    <div v-if="discoveredServers.length > 0" class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">
          Discovered Servers
          <div class="badge badge-primary">{{ discoveredServers.length }}</div>
        </h2>
        
        <div class="space-y-4">
          <div 
            v-for="server in discoveredServers" 
            :key="server.ip"
            class="card bg-base-200 shadow-sm"
          >
            <div class="card-body p-4">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                  <!-- Confidence Icon -->
                  <div class="flex-shrink-0">
                    <div v-if="server.confidence === 'confirmed'" class="tooltip" data-tip="Confirmed Ubuntu">
                      <svg class="w-8 h-8 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                      </svg>
                    </div>
                    <div v-else-if="server.confidence === 'possible'" class="tooltip" data-tip="Possible Ubuntu">
                      <svg class="w-8 h-8 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                      </svg>
                    </div>
                    <div v-else-if="server.confidence === 'failed'" class="tooltip" data-tip="SSH Verification Failed">
                      <svg class="w-8 h-8 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                      </svg>
                    </div>
                    <div v-else class="tooltip" data-tip="Unknown OS">
                      <svg class="w-8 h-8 text-base-content text-opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                      </svg>
                    </div>
                  </div>
                  
                  <!-- Server Info -->
                  <div>
                    <h3 class="font-semibold text-lg">
                      {{ server.ip }}
                      <span v-if="server.hostname" class="text-sm text-base-content text-opacity-70 ml-2">
                        ({{ server.hostname }})
                      </span>
                    </h3>
                    <div class="text-sm text-base-content text-opacity-70">
                      <span v-if="server.error" class="text-error">{{ server.error }}</span>
                      <span v-else-if="server.os_info">{{ server.os_info }}</span>
                      <span v-else-if="server.ssh_available">SSH Available</span>
                      <span v-else>No SSH Access</span>
                      <span v-if="server.banner && !server.error" class="ml-2 font-mono text-xs">
                        • {{ server.banner.substring(0, 30) }}...
                      </span>
                    </div>
                  </div>
                </div>
                
                <!-- Actions -->
                <div class="flex items-center gap-2">
                  <button 
                    v-if="server.confidence === 'possible'"
                    class="btn btn-sm btn-ghost"
                    @click="verifyServer(server)"
                  >
                    Verify
                  </button>
                  <button 
                    v-if="server.ssh_available && !server.error && !selectedServers.find(s => s.ip === server.ip)"
                    class="btn btn-sm btn-primary"
                    @click="selectServer(server)"
                  >
                    Select
                  </button>
                  <button 
                    v-else-if="server.error"
                    class="btn btn-sm btn-error"
                    disabled
                  >
                    Failed
                  </button>
                  <div v-else-if="selectedServers.find(s => s.ip === server.ip)" class="badge badge-success">
                    Selected
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    
    <!-- Navigation -->
    <div class="flex justify-between mt-6">
      <button class="btn btn-ghost gap-2" @click="$router.push('/installation')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
        Back
      </button>
      <button 
        class="btn btn-primary gap-2"
        @click="proceedToNodeConfig"
        :disabled="selectedServers.length === 0"
      >
        Continue with {{ selectedServers.length }} Server{{ selectedServers.length !== 1 ? 's' : '' }}
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

// Get network mode from config
const config = ref(JSON.parse(localStorage.getItem('thinkube-config') || '{}'))
const networkMode = ref(config.value.networkMode || 'overlay')

// State
const networkCIDR = ref('192.168.1.0/24')
const testMode = ref(false)
const isScanning = ref(false)
const scanProgress = ref(0)
const scanStatus = ref('')
const discoveredServers = ref([])
const selectedServers = ref([])


// Methods
const onNetworkModeChange = async () => {
  // Save the network mode to config
  config.value.networkMode = networkMode.value
  localStorage.setItem('thinkube-config', JSON.stringify(config.value))
  
  // Clear any discovered servers when switching modes
  discoveredServers.value = []
  selectedServers.value = []
  
  // Update default CIDR based on mode
  if (networkMode.value === 'overlay') {
    // Try to auto-detect ZeroTier network
    try {
      const response = await axios.get('/api/zerotier-network')
      if (response.data.detected) {
        networkCIDR.value = response.data.network_cidr
        console.log(`Auto-detected ZeroTier network: ${response.data.network_cidr}`)
      } else {
        networkCIDR.value = ''  // No default - user must provide
      }
    } catch (error) {
      networkCIDR.value = '172.30.0.0/24'  // Fallback default
    }
  } else {
    // For local mode, try to auto-detect
    autoDetectNetwork()
  }
}

const startDiscovery = async () => {
  isScanning.value = true
  scanProgress.value = 0
  scanStatus.value = networkMode.value === 'overlay' ? 'Connecting to ZeroTier API...' : 'Initializing scan...'
  discoveredServers.value = []
  
  if (networkMode.value === 'overlay') {
    // ZeroTier discovery - scan the ZeroTier network directly
    // Users should enter their ZeroTier network CIDR (e.g., 172.30.0.0/24)
    const progressInterval = setInterval(() => {
      if (scanProgress.value < 90) {
        scanProgress.value = Math.min(90, scanProgress.value + Math.random() * 20)
        scanStatus.value = `Scanning ZeroTier network ${networkCIDR.value} - Checking ${Math.floor(scanProgress.value * 2.54)} of 254 hosts`
      }
    }, 500)
    
    try {
      const sudoPassword = sessionStorage.getItem('sudoPassword')
      const currentUsername = sessionStorage.getItem('systemUsername')
      
      const response = await axios.post('/api/discover-servers', {
        network_cidr: networkCIDR.value,
        test_mode: testMode.value,
        username: currentUsername,
        password: sudoPassword
      })
      
      discoveredServers.value = response.data.servers || []
      scanProgress.value = 100
      scanStatus.value = `Scan complete - Found ${discoveredServers.value.length} servers on ZeroTier network`
      
    } catch (error) {
      console.error('Discovery failed:', error)
      scanStatus.value = 'Scan failed: ' + error.message
    } finally {
      clearInterval(progressInterval)
      setTimeout(() => {
        isScanning.value = false
      }, 1000)
    }
  } else {
    // Local network discovery
    const progressInterval = setInterval(() => {
      if (scanProgress.value < 90) {
        scanProgress.value = Math.min(90, scanProgress.value + Math.random() * 20)
        scanStatus.value = `Scanning ${networkCIDR.value} - Checking ${Math.floor(scanProgress.value * 2.54)} of 254 hosts`
      }
    }, 500)
    
    try {
      const sudoPassword = sessionStorage.getItem('sudoPassword')
      const currentUsername = sessionStorage.getItem('systemUsername')
      
      const response = await axios.post('/api/discover-servers', {
        network_cidr: networkCIDR.value,
        test_mode: testMode.value,
        username: currentUsername,
        password: sudoPassword
      })
      
      discoveredServers.value = response.data.servers || []
      scanProgress.value = 100
      scanStatus.value = `Scan complete - Found ${discoveredServers.value.length} servers`
      
    } catch (error) {
      console.error('Discovery failed:', error)
      scanStatus.value = 'Scan failed: ' + error.message
    } finally {
      clearInterval(progressInterval)
      setTimeout(() => {
        isScanning.value = false
      }, 1000)
    }
  }
}

const verifyServer = async (server) => {
  try {
    // Get password from sessionStorage
    const sudoPassword = sessionStorage.getItem('sudoPassword')
    
    const endpoint = server.is_zerotier ? '/api/verify-zerotier-ssh' : '/api/verify-server-ssh'
    const response = await axios.post(endpoint, {
      ip_address: server.ip,
      zerotier_ip: server.ip,  // For ZeroTier endpoint
      password: sudoPassword,
      test_mode: testMode.value
    })
    
    // Update server info based on verification
    const idx = discoveredServers.value.findIndex(s => s.ip === server.ip)
    if (idx >= 0) {
      if (response.data.connected) {
        discoveredServers.value[idx] = {
          ...discoveredServers.value[idx],
          hostname: response.data.hostname || server.hostname,
          os_info: response.data.os_info,
          confidence: response.data.os_info?.includes('24.04') ? 'confirmed' : 'possible',
          verified: true
        }
      } else {
        // SSH verification failed - show the error
        discoveredServers.value[idx] = {
          ...discoveredServers.value[idx],
          error: response.data.message || 'SSH verification failed',
          verified: false,
          confidence: 'failed'
        }
        // Show error to user
        alert(`SSH verification failed for ${server.ip}:\n${response.data.message}`)
      }
    }
  } catch (error) {
    console.error('Verification failed:', error)
    // Show error to user
    alert(`Failed to verify server ${server.ip}:\n${error.response?.data?.detail || error.message}`)
  }
}

const selectServer = (server) => {
  if (!selectedServers.value.find(s => s.ip === server.ip)) {
    selectedServers.value.push(server)
  }
}


const proceedToNodeConfig = () => {
  // Debug log to see what we're storing
  console.log('Selected servers:', selectedServers.value)
  
  // Store selected servers in a shared store or pass via router
  sessionStorage.setItem('selectedServers', JSON.stringify(selectedServers.value))
  sessionStorage.setItem('testMode', testMode.value)
  // Store discovered servers - these should have full server objects with hostnames
  sessionStorage.setItem('discoveredServers', JSON.stringify(selectedServers.value))
  // Store network CIDR for inventory generation
  sessionStorage.setItem('networkCIDR', networkCIDR.value)
  router.push('/ssh-setup')
}

const autoDetectNetwork = async () => {
  try {
    const response = await axios.get('/api/local-network')
    if (response.data.detected) {
      networkCIDR.value = response.data.network_cidr
      console.log(`Auto-detected network: ${response.data.network_cidr}`)
    }
  } catch (error) {
    console.error('Failed to auto-detect network:', error)
    // Keep default value
  }
}

// Auto-detect network on mount
onMounted(async () => {
  // Set initial CIDR based on network mode
  if (networkMode.value === 'overlay') {
    // Try to auto-detect ZeroTier network
    try {
      const response = await axios.get('/api/zerotier-network')
      if (response.data.detected) {
        networkCIDR.value = response.data.network_cidr
        console.log(`Auto-detected ZeroTier network: ${response.data.network_cidr} on ${response.data.interface}`)
      } else {
        // Fallback to common default
        networkCIDR.value = '172.30.0.0/24'
        if (response.data.message) {
          console.log(response.data.message)
        }
      }
    } catch (error) {
      console.error('Failed to auto-detect ZeroTier network:', error)
      networkCIDR.value = ''  // No default - user must provide or auto-detect
    }
  } else {
    await autoDetectNetwork()
  }
})
</script>

