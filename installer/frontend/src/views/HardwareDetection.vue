/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold mb-6 text-base-content">Hardware Detection</h1>
    
    <!-- Detection Progress -->
    <div v-if="isDetecting" class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Detecting Hardware Capabilities</h2>
        <progress class="progress progress-primary w-full" :value="progress" max="100"></progress>
        <p class="text-sm mt-2">{{ currentServer }}</p>
      </div>
    </div>
    
    <!-- Server Hardware List -->
    <div v-else class="space-y-4 mb-6">
      <div 
        v-for="(server, idx) in servers" 
        :key="server.ip"
        class="card bg-base-100 shadow-xl"
      >
        <div class="card-body">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <h2 class="text-xl font-bold text-base-content">{{ server.hostname }}</h2>
              <div class="badge badge-ghost font-mono">{{ server.ip }}</div>
            </div>
          </div>
          
          <!-- Hardware Stats -->
          <div v-if="server.hardware" class="stats stats-horizontal shadow w-full">
            <div class="stat place-items-center">
              <div class="stat-title font-medium">CPU</div>
              <div class="stat-value text-primary">{{ server.hardware.cpu_cores }}</div>
              <div class="stat-desc text-base-content text-opacity-60">cores</div>
            </div>
            
            <div class="stat place-items-center">
              <div class="stat-title font-medium">RAM</div>
              <div class="stat-value text-primary">{{ Math.round(server.hardware.memory_gb) }}</div>
              <div class="stat-desc text-base-content text-opacity-60">GB</div>
            </div>
            
            <div class="stat place-items-center">
              <div class="stat-title font-medium">Disk</div>
              <div class="stat-value text-primary">{{ Math.round(server.hardware.disk_gb) }}</div>
              <div class="stat-desc text-base-content text-opacity-60">GB</div>
            </div>
            
            <div v-if="server.hardware.gpu_detected" class="stat place-items-center">
              <div class="stat-title font-medium">GPU</div>
              <div class="stat-value text-primary">{{ server.hardware.gpu_count }}</div>
              <div class="stat-desc text-base-content text-opacity-60">{{ server.hardware.gpu_model?.split(' ').slice(-2).join(' ') || 'Detected' }}</div>
            </div>
          </div>
          
          <!-- Detection Error -->
          <div v-else-if="server.error" class="alert alert-error">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ server.error }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Summary -->
    <div v-if="!isDetecting && servers.length > 0" class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Cluster Capacity Summary</h2>
        
        <div class="prose prose-sm max-w-none">
          <h3 class="font-semibold mb-2 text-base-content">Total Resources</h3>
          <ul class="space-y-1 text-base-content text-opacity-80">
            <li>CPU Cores: <span class="font-medium text-base-content">{{ totalResources.cpu }}</span></li>
            <li>Memory: <span class="font-medium text-base-content">{{ Math.round(totalResources.memory) }}</span> GB</li>
            <li>Storage: <span class="font-medium text-base-content">{{ Math.round(totalResources.storage) }}</span> GB</li>
            <li v-if="totalResources.gpus > 0">GPUs: <span class="font-medium text-base-content">{{ totalResources.gpus }}</span></li>
          </ul>
        </div>
      </div>
    </div>
    
    <!-- Actions -->
    <div class="flex justify-between">
      <button class="btn btn-ghost gap-2" @click="$router.push('/ssh-setup')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
        Back
      </button>
      
      <button 
        v-if="!isDetecting"
        class="btn btn-primary gap-2"
        @click="continueToRoleAssignment"
        :disabled="servers.length === 0 || hasDetectionErrors || !hasValidHardware"
      >
        Continue to Role Assignment
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

// State
const servers = ref([])
const isDetecting = ref(false)
const progress = ref(0)
const currentServer = ref('')

// Computed
const totalResources = computed(() => {
  return servers.value.reduce((acc, server) => {
    if (server.hardware) {
      acc.cpu += server.hardware.cpu_cores || 0
      acc.memory += server.hardware.memory_gb || 0
      acc.storage += server.hardware.disk_gb || 0
      acc.gpus += server.hardware.gpu_count || 0
    }
    return acc
  }, { cpu: 0, memory: 0, storage: 0, gpus: 0 })
})


const hasDetectionErrors = computed(() => {
  return servers.value.some(server => server.error)
})

const hasValidHardware = computed(() => {
  return servers.value.some(server => 
    server.hardware && 
    server.hardware.cpu_cores > 0 && 
    server.hardware.memory_gb > 0 && 
    server.hardware.disk_gb > 0
  )
})

// Detect hardware
const detectHardware = async () => {
  isDetecting.value = true
  progress.value = 0
  
  try {
    const sshCreds = JSON.parse(sessionStorage.getItem('sshCredentials') || '{}')
    
    for (let i = 0; i < servers.value.length; i++) {
      const server = servers.value[i]
      currentServer.value = `Detecting ${server.hostname}...`
      progress.value = ((i + 1) / servers.value.length) * 100
      
      try {
        const response = await axios.post('/api/detect-hardware', {
          server: server.ip,
          username: sshCreds.username,
          password: sshCreds.password
        })
        
        if (response.data.error) {
          // Use the actual error message from the backend
          server.error = response.data.error
          server.hardware = null
          server.network = null
        } else if (response.data.hardware) {
          server.hardware = response.data.hardware
          server.network = response.data.network || null
          // Validate hardware values are reasonable
          if (server.hardware.cpu_cores === 0 || server.hardware.memory_gb === 0 || server.hardware.disk_gb === 0) {
            server.error = 'Hardware detection returned invalid values'
            server.hardware = null
          } else {
            // Log network info if available
            if (server.network && server.network.ip_address) {
              console.log(`Server ${server.hostname} local network: ${server.network.ip_address} on ${server.network.cidr}`)
            }
          }
        } else {
          server.error = 'Failed to detect hardware'
        }
      } catch (error) {
        server.error = error.response?.data?.detail || 'Detection failed'
      }
    }
  } finally {
    isDetecting.value = false
  }
}

// Continue to role assignment
const continueToRoleAssignment = () => {
  // Store hardware info for role assignment
  sessionStorage.setItem('serverHardware', JSON.stringify(servers.value))
  
  // Also extract and store network info for validation
  const networkInfo = servers.value
    .filter(s => s.network && s.network.cidr)
    .map(s => ({
      hostname: s.hostname,
      ip: s.ip,
      localIP: s.network.ip_address,
      cidr: s.network.cidr,
      gateway: s.network.gateway,
      interface: s.network.interface
    }))
  sessionStorage.setItem('serverNetworkInfo', JSON.stringify(networkInfo))
  
  router.push('/role-assignment')
}

// Load servers and start detection
onMounted(async () => {
  const discoveredServers = JSON.parse(sessionStorage.getItem('discoveredServers') || '[]')
  servers.value = discoveredServers.map(s => ({
    hostname: s.hostname,
    ip: s.ip_address || s.ip,
    hardware: null,
    network: null,
    error: null
  }))
  
  // Start detection automatically
  if (servers.value.length > 0) {
    await detectHardware()
  }
})
</script>