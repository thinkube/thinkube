/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-6 text-base-content">SSH Connectivity Check</h1>
    
    <!-- SSH Info -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Verifying SSH Access</h2>
        
        <div class="alert alert-info mb-6">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <div class="prose prose-sm max-w-none">
            <p class="font-medium mb-1">Checking SSH connectivity to all discovered servers.</p>
            <p class="text-sm text-base-content text-opacity-80">Using credentials: <span class="font-mono text-primary">{{ currentUser }}</span> with the sudo password provided earlier.</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Discovered Servers -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Servers to Configure</h2>
        
        <div class="overflow-x-auto rounded-lg">
          <table class="table table-compact table-pin-rows hover">
            <thead>
              <tr>
                <th class="font-semibold text-base-content text-opacity-90">Hostname</th>
                <th class="font-semibold text-base-content text-opacity-90">IP Address</th>
                <th class="font-semibold text-base-content text-opacity-90">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="server in servers" :key="server.ip">
                <td class="font-medium">{{ server.hostname }}</td>
                <td>{{ server.ip }}</td>
                <td>
                  <div>
                    <div class="badge" :class="getStatusClass(server.status)">
                      {{ server.status || 'Pending' }}
                    </div>
                    <div v-if="server.error" class="text-sm text-error mt-1">
                      {{ server.error }}
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- Error Alert -->
    <div v-if="hasErrors" class="alert alert-error mb-6">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div>
        <h3 class="font-bold">SSH Connection Failed</h3>
        <div class="text-sm">
          <p>Unable to connect to one or more servers. Please ensure:</p>
          <ul class="list-disc list-inside mt-2">
            <li>User '{{ currentUser }}' exists on all servers</li>
            <li>The sudo password is the same on all servers</li>
            <li>SSH service is running on all servers</li>
          </ul>
        </div>
      </div>
    </div>
    
    <!-- Progress -->
    <div v-if="isChecking" class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Setup Progress</h2>
        <progress class="progress progress-primary w-full" :value="progress" max="100"></progress>
        <p class="text-sm mt-2">{{ currentTask }}</p>
      </div>
    </div>
    
    <!-- SSH Setup Complete -->
    <div v-if="!isChecking && sshSetupComplete" class="card bg-success bg-opacity-10 border border-success/20 shadow-xl mb-6">
      <div class="card-body">
        <div class="flex items-center gap-3 mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-success shrink-0 h-8 w-8" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 class="font-bold text-lg text-base-content">SSH Setup Complete!</h3>
            <div class="text-sm text-base-content text-opacity-80">Passwordless SSH has been configured between all servers.</div>
          </div>
        </div>
        
        <div class="flex gap-3 flex-wrap">
          <button 
            class="btn btn-outline gap-2"
            @click="runTestPlaybook"
            :disabled="isTestRunning || !sshSetupComplete"
          >
            <svg v-if="isTestRunning" class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
            </svg>
            {{ isTestRunning ? 'Testing...' : 'Test SSH Connectivity' }}
          </button>
          
          <button 
            class="btn btn-primary gap-2"
            @click="continueToNext"
            :disabled="!sshSetupComplete || !testResult?.success"
          >
            Continue to Next Step
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
            </svg>
          </button>
        </div>
        
        <div v-if="testResult" class="mt-4">
          <div class="alert" :class="testResult.success ? 'alert-success' : 'alert-error'">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
              <path v-if="testResult.success" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ testResult.message }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="!isChecking && servers.some(s => s.status === 'failed')" class="flex justify-end">
      <button 
        class="btn btn-primary gap-2"
        @click="setupSSH"
      >
        Retry SSH Setup
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
      </button>
    </div>

    <!-- Streaming Playbook Executor -->
    <PlaybookExecutorStream 
      ref="playbookExecutor" 
      title="SSH Key Setup"
      playbook-name="setup-ssh-keys"
      :on-retry="setupSSH"
      @complete="handlePlaybookComplete"
    />
    
    <!-- Test Playbook Executor -->
    <PlaybookExecutorStream 
      ref="testPlaybookExecutor" 
      title="SSH Connectivity Test"
      playbook-name="test-ssh-connectivity"
      :on-retry="runTestPlaybook"
      @complete="handleTestComplete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import PlaybookExecutorStream from '@/components/PlaybookExecutorStream.vue'
import { saveCheckpoint, getCheckpoint, STEPS } from '@/utils/installerState'

const router = useRouter()

// State
const servers = ref([])
const currentUser = ref('')
const isChecking = ref(false)
const progress = ref(0)
const currentTask = ref('')
const playbookExecutor = ref()
const testPlaybookExecutor = ref()
const sshSetupComplete = ref(false) // Only true after setup actually succeeds
const isTestRunning = ref(false)
const testResult = ref(null)

// Computed properties
const hasErrors = computed(() => {
  return servers.value.some(server => server.status === 'failed')
})

// Status class helper
const getStatusClass = (status) => {
  switch (status) {
    case 'connected': return 'badge-success'
    case 'failed': return 'badge-error'
    case 'configuring': return 'badge-warning'
    default: return 'badge-ghost'
  }
}

// Verify SSH connectivity to individual servers
const verifyServerConnectivity = async () => {
  isChecking.value = true
  progress.value = 0
  currentTask.value = 'Checking SSH connectivity...'
  
  try {
    const sudoPassword = sessionStorage.getItem('sudoPassword')
    
    // Check connectivity to each server
    for (let i = 0; i < servers.value.length; i++) {
      const server = servers.value[i]
      currentTask.value = `Checking ${server.hostname}...`
      progress.value = ((i + 1) / servers.value.length) * 100
      
      try {
        const response = await axios.post('/api/verify-ssh', {
          server: server.ip,
          username: currentUser.value,
          password: sudoPassword
        })
        
        if (response.data.success || response.data.connected) {
          server.status = 'connected'
          server.error = null
        } else {
          server.status = 'failed'
          server.error = response.data.message || 'SSH connection failed'
        }
      } catch (error) {
        server.status = 'failed'
        server.error = error.response?.data?.detail || error.message || 'Connection error'
        console.error(`SSH check failed for ${server.hostname}:`, error)
      }
    }
  } catch (error) {
    console.error('SSH verification failed:', error)
  } finally {
    isChecking.value = false
  }
}

// Setup SSH keys using streaming playbook execution
const setupSSH = async () => {
  const sudoPassword = sessionStorage.getItem('sudoPassword')
  
  if (!sudoPassword) {
    alert('Sudo password not found. Please go back and enter your password.')
    return
  }
  
  // Mark all servers as configuring
  servers.value.forEach(server => {
    server.status = 'configuring'
  })
  
  // Execute playbook with streaming output
  playbookExecutor.value.startExecution({
    environment: {
      ANSIBLE_BECOME_PASSWORD: sudoPassword,
      ANSIBLE_SSH_PASSWORD: sudoPassword
    },
    extra_vars: {
      ansible_user: currentUser.value,
      ansible_ssh_pass: sudoPassword,
      ansible_become_pass: sudoPassword
    }
  })
}

// Handle playbook completion (called from the streaming component)
const handlePlaybookComplete = (result) => {
  if (result.status === 'success') {
    // Mark all servers as configured
    servers.value.forEach(server => {
      server.status = 'connected'
    })
    
    // Store SSH info for later use
    sessionStorage.setItem('sshCredentials', JSON.stringify({
      username: currentUser.value,
      password: sessionStorage.getItem('sudoPassword')
    }))
    
    sshSetupComplete.value = true
    
    // DON'T save checkpoint here - only save after test passes
  } else {
    // Mark servers as failed
    servers.value.forEach(server => {
      server.status = 'failed'
    })
    sshSetupComplete.value = false
  }
}

// Run SSH connectivity test playbook
const runTestPlaybook = () => {
  isTestRunning.value = true
  testResult.value = null
  
  // Show the test playbook executor
  testPlaybookExecutor.value.startExecution({
    environment: {
      // No password needed for test since SSH keys are already set up
    },
    extra_vars: {
      ansible_user: currentUser.value
    }
  })
}

// Handle test playbook completion
const handleTestComplete = (result) => {
  isTestRunning.value = false
  
  if (result.status === 'success') {
    testResult.value = {
      success: true,
      message: 'SSH connectivity test passed! All servers are accessible via SSH keys.'
    }
    
    // NOW save checkpoint after successful test
    saveCheckpoint(STEPS.SSH_SETUP, {
      servers: servers.value.map(s => ({
        hostname: s.hostname,
        ip: s.ip,
        status: 'configured'
      })),
      username: currentUser.value,
      completedAt: new Date().toISOString()
    })
  } else {
    testResult.value = {
      success: false,
      message: 'SSH connectivity test failed. Please check the logs for details.'
    }
  }
}

// Continue to next step
const continueToNext = () => {
  router.push('/hardware-detection')
}

// Load discovered servers and check state
onMounted(async () => {
  // Always load discovered servers fresh - don't trust checkpoints
  const discoveredServers = JSON.parse(sessionStorage.getItem('discoveredServers') || '[]')
  servers.value = discoveredServers.map(s => ({
    hostname: s.hostname,
    ip: s.ip_address || s.ip,
    status: 'pending'
  }))
  
  // Get current user from session storage
  currentUser.value = sessionStorage.getItem('systemUsername') || 'ubuntu'
  
  // Start SSH key setup automatically after a short delay to ensure component is ready
  if (servers.value.length > 0) {
    setTimeout(() => {
      setupSSH()
    }, 500)
  }
})
</script>