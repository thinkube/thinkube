/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-6xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Deploying Thinkube Infrastructure</h1>
      <button 
        class="btn btn-ghost btn-sm gap-2" 
        @click="resetDeployment"
        title="Clear deployment state and start over"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
        Reset
      </button>
    </div>
    
    <!-- Deployment Progress Overview -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Deployment Progress</h2>
        
        <!-- Phase Indicators -->
        <div class="flex flex-wrap gap-2 mb-6">
          <div v-for="(phase, index) in deploymentPhases" :key="phase.id"
               class="badge gap-2"
               :class="getPhaseClass(phase)">
            <svg v-if="phase.status === 'completed'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <svg v-else-if="phase.status === 'active'" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ phase.name }}
          </div>
        </div>
        
        <progress class="progress progress-primary w-full" :value="overallProgress" max="100"></progress>
        <p class="text-sm text-center mt-2">{{ overallProgress }}% Complete</p>
      </div>
    </div>
    
    <!-- Current Playbook Execution -->
    <div v-if="currentPlaybook">
      <PlaybookExecutorStream 
        ref="currentPlaybookExecutor"
        :key="currentPlaybook.id"
        :title="currentPlaybook.title"
        :playbook-name="currentPlaybook.name"
        :extra-vars="currentPlaybook.extraVars"
        :on-retry="retryCurrentPlaybook"
        @complete="handlePlaybookComplete"
        @continue="handlePlaybookContinue"
      />
    </div>
    
    <!-- Machine Restart Notice -->
    <div v-if="showRestartNotice" class="card bg-warning bg-opacity-10 border-warning mb-6">
      <div class="card-body">
        <h2 class="card-title text-warning mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          System Restart Required
        </h2>
        
        <div class="space-y-4">
          <div>
            <p class="font-semibold mb-2">The network bridge configuration requires all baremetal servers to be restarted.</p>
            <p class="text-sm text-base-content text-opacity-70">Click the button below to begin the automated restart process.</p>
          </div>
          
          <div class="text-center">
            <button class="btn btn-primary btn-lg gap-2" @click="automatedRestart">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
              Restart All Servers
            </button>
            <p class="text-sm text-base-content text-opacity-70 mt-3">
              Remote servers will restart first, followed by this server.<br/>
              The installer will automatically continue after all servers are back online.
            </p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Completion -->
    <div v-if="deploymentComplete" class="card bg-base-100 shadow-xl">
      <div class="card-body text-center">
        <div class="text-6xl mb-4">🎉</div>
        <h2 class="card-title justify-center mb-4">Deployment Complete!</h2>
        <p class="mb-6">Your Thinkube infrastructure has been successfully deployed.</p>
        <button 
          class="btn btn-primary btn-lg gap-2"
          @click="$router.push('/complete')"
        >
          View Cluster Details
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- Error State -->
    <div v-if="deploymentError" class="alert alert-error">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div>
        <h3 class="font-bold">Deployment Failed</h3>
        <p>{{ deploymentError }}</p>
        <div class="flex gap-2 mt-2">
          <button class="btn btn-sm btn-outline" @click="retryDeployment">Retry</button>
          <button class="btn btn-sm btn-ghost" @click="resetDeployment">Reset & Start Over</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import PlaybookExecutorStream from '@/components/PlaybookExecutorStream.vue'
import axios from '@/utils/axios'
import { deploymentState } from '@/utils/deploymentState'

const router = useRouter()

// Deployment phases
const deploymentPhases = ref([
  { id: 'initial', name: 'Initial Setup', status: 'pending' },
  { id: 'kubernetes', name: 'Kubernetes', status: 'pending' }
])

// State variables
const currentPlaybook = ref(null)
const currentPhase = ref(null)
const showRestartNotice = ref(false)
const deploymentComplete = ref(false)
const deploymentError = ref('')

// Component refs
const currentPlaybookExecutor = ref(null)

// Progress tracking
const overallProgress = ref(0)

// Update progress and phase statuses
const updateProgress = async () => {
  try {
    const progress = await deploymentState.getProgress()
    overallProgress.value = progress.percentage
    
    // Also update phase statuses
    await updatePhaseStatuses()
  } catch (e) {
    console.error('Error updating progress:', e)
    overallProgress.value = 0
  }
}

// Update phase statuses based on deployment progress
const updatePhaseStatuses = async () => {
  try {
    const state = await deploymentState.loadState()
    if (!state || !state.allPlaybooks) return
    
    // Reset all phases
    deploymentPhases.value.forEach(phase => {
      phase.status = 'pending'
    })
    
    // Mark completed phases
    state.allPlaybooks.forEach(playbook => {
      if (state.completedIds.includes(playbook.id)) {
        const phase = deploymentPhases.value.find(p => p.id === playbook.phase)
        if (phase && phase.status === 'pending') {
          // Check if all playbooks in this phase are complete
          const phasePlaybooks = state.allPlaybooks.filter(p => p.phase === playbook.phase)
          const phaseComplete = phasePlaybooks.every(p => state.completedIds.includes(p.id))
          if (phaseComplete) {
            phase.status = 'completed'
          }
        }
      }
    })
    
    // Mark current phase as active
    if (currentPhase.value) {
      const phase = deploymentPhases.value.find(p => p.id === currentPhase.value)
      if (phase && phase.status === 'pending') {
        phase.status = 'active'
      }
    }
  } catch (e) {
    console.error('Error updating phase statuses:', e)
  }
}

// Get phase class for styling
const getPhaseClass = (phase) => {
  switch (phase.status) {
    case 'completed': return 'badge-success'
    case 'active': return 'badge-warning'
    case 'failed': return 'badge-error'
    default: return 'badge-ghost'
  }
}

// Build playbook queue based on deployment type
const buildPlaybookQueue = () => {
  const queue = []
  console.log('Building playbook queue...')
  
  // Phase 1: Initial Setup (00_initial_setup)
  // Skip SSH keys - already done in SSHSetup step
  queue.push({
    id: 'env-setup',
    phase: 'initial', 
    title: 'Setting up Environment',
    name: 'ansible/00_initial_setup/20_setup_env.yaml'
  })
  
  // Add Python setup for all hosts (required for Ansible to work properly)
  queue.push({
    id: 'python-setup',
    phase: 'initial',
    title: 'Setting up Python Virtual Environments',
    name: 'ansible/40_thinkube/core/infrastructure/00_setup_python_k8s.yaml'
  })
  
  // Add shell configuration (required before MicroK8s installation)
  queue.push({
    id: 'shell-setup',
    phase: 'initial',
    title: 'Configuring Shell Environments',
    name: 'ansible/misc/00_setup_shells.yml'
  })
  
  // GPU reservation is only needed for VM passthrough, not baremetal
  // Since we removed VM support, skip GPU reservation entirely
  
  queue.push({
    id: 'github-cli',
    phase: 'initial',
    title: 'Setting up GitHub CLI',
    name: 'ansible/00_initial_setup/40_setup_github_cli.yaml'
  })
  
  // Phase 2: Networking (30_networking)
  // ZeroTier is already configured as a prerequisite to run the installer
  // MetalLB addresses are handled by the ingress installer
  
  // Phase 3: Kubernetes Infrastructure (40_thinkube/core/infrastructure)
  // CRITICAL: Setup Python K8s libraries FIRST
  queue.push({
    id: 'setup-python-k8s',
    phase: 'kubernetes',
    title: 'Setting up Python Kubernetes Libraries',
    name: 'ansible/40_thinkube/core/infrastructure/00_setup_python_k8s.yaml'
  })
  
  queue.push({
    id: 'microk8s',
    phase: 'kubernetes',
    title: 'Installing MicroK8s',
    name: 'ansible/40_thinkube/core/infrastructure/microk8s/10_install_microk8s.yaml'
  })
  
  // Join worker nodes after control plane is set up
  const clusterNodes = JSON.parse(sessionStorage.getItem('clusterNodes') || '[]')
  const hasWorkers = clusterNodes.some(n => n.role === 'worker')
  if (hasWorkers) {
    queue.push({
      id: 'microk8s-join-workers',
      phase: 'kubernetes',
      title: 'Joining Worker Nodes to Cluster',
      name: 'ansible/40_thinkube/core/infrastructure/microk8s/20_join_workers.yaml'
    })
  }
  
  // GPU operator if needed
  const serverHardware = JSON.parse(sessionStorage.getItem('serverHardware') || '[]')
  const needsGPUOperator = serverHardware.some(s => s.hardware?.gpu_detected)
  if (needsGPUOperator) {
    queue.push({
      id: 'gpu-operator',
      phase: 'kubernetes',
      title: 'Installing NVIDIA GPU Operator',
      name: 'ansible/40_thinkube/core/infrastructure/gpu_operator/10_deploy.yaml'
    })
  }
  
  // DNS server (BIND9) must come before CoreDNS as CoreDNS forwards to it
  queue.push({
    id: 'dns-server',
    phase: 'kubernetes',
    title: 'Deploying DNS Server (BIND9)',
    name: 'ansible/40_thinkube/core/infrastructure/dns-server/10_deploy.yaml'
  })
  
  // CoreDNS must come after dns-server and before cert-manager and ingress
  queue.push({
    id: 'coredns',
    phase: 'kubernetes',
    title: 'Deploying CoreDNS',
    name: 'ansible/40_thinkube/core/infrastructure/coredns/10_deploy.yaml'
  })
  
  queue.push({
    id: 'coredns-configure-nodes',
    phase: 'kubernetes',
    title: 'Configuring Node DNS',
    name: 'ansible/40_thinkube/core/infrastructure/coredns/15_configure_node_dns.yaml'
  })
  
  // ACME certificates (acme.sh) for SSL/TLS management
  queue.push({
    id: 'acme-certificates',
    phase: 'kubernetes',
    title: 'Setting up SSL Certificates',
    name: 'ansible/40_thinkube/core/infrastructure/acme-certificates/10_deploy.yaml'
  })
  
  // Ingress controller
  queue.push({
    id: 'ingress',
    phase: 'kubernetes',
    title: 'Deploying Ingress Controller',
    name: 'ansible/40_thinkube/core/infrastructure/ingress/10_deploy.yaml'
  })
  
  // Core Services (dependencies in correct order)
  // PostgreSQL first (no Harbor dependency, provides storage for Keycloak)
  queue.push({
    id: 'postgresql',
    phase: 'kubernetes',
    title: 'Installing PostgreSQL',
    name: 'ansible/40_thinkube/core/postgresql/00_install.yaml'
  })
  
  // Keycloak (requires PostgreSQL for persistent storage)
  queue.push({
    id: 'keycloak',
    phase: 'kubernetes',
    title: 'Installing Keycloak',
    name: 'ansible/40_thinkube/core/keycloak/00_install.yaml'
  })
  
  // Harbor (requires Keycloak for OIDC authentication)
  queue.push({
    id: 'harbor',
    phase: 'kubernetes',
    title: 'Installing Harbor',
    name: 'ansible/40_thinkube/core/harbor/00_install.yaml'
  })
  
  // SeaweedFS for object storage (replacing MinIO)
  queue.push({
    id: 'seaweedfs',
    phase: 'kubernetes',
    title: 'Installing SeaweedFS',
    name: 'ansible/40_thinkube/core/seaweedfs/00_install.yaml'
  })
  
  // Argo Workflows
  queue.push({
    id: 'argo-workflows',
    phase: 'kubernetes',
    title: 'Installing Argo Workflows',
    name: 'ansible/40_thinkube/core/argo-workflows/00_install.yaml'
  })
  
  // ArgoCD
  queue.push({
    id: 'argocd',
    phase: 'kubernetes',
    title: 'Installing ArgoCD',
    name: 'ansible/40_thinkube/core/argocd/00_install.yaml'
  })
  
  // DevPi (Python package index)
  queue.push({
    id: 'devpi',
    phase: 'kubernetes',
    title: 'Installing DevPi',
    name: 'ansible/40_thinkube/core/devpi/00_install.yaml'
  })
  
  // Code-Server (VS Code in browser with CI/CD integration)
  queue.push({
    id: 'code-server',
    phase: 'kubernetes',
    title: 'Installing Code-Server',
    name: 'ansible/40_thinkube/core/code-server/00_install.yaml'
  })
  
  // Gitea (required by thinkube-control for GitOps)
  queue.push({
    id: 'gitea',
    phase: 'kubernetes',
    title: 'Installing Gitea',
    name: 'ansible/40_thinkube/core/gitea/00_install.yaml'
  })
  
  // Thinkube Control (management dashboard)
  queue.push({
    id: 'thinkube-control',
    phase: 'kubernetes',
    title: 'Deploying Thinkube Control',
    name: 'ansible/40_thinkube/core/thinkube-control/00_install.yaml'
  })
  
  console.log('Final playbook queue:', queue.map(p => `${p.id}: ${p.title}`))
  console.log('Total playbooks in queue:', queue.length)
  
  return queue
}

// Reference to current playbook executor is already declared above

// Execute next playbook in queue
const executeNextPlaybook = async () => {
  console.log('executeNextPlaybook called')
  
  // Get next playbook from state manager
  const next = await deploymentState.getNextPlaybook()
  
  if (!next) {
    console.log('No more playbooks to execute, deployment complete')
    deploymentComplete.value = true
    // Update final phase status
    await updateProgress()
    return
  }
  
  const { playbook, index } = next
  console.log('Next playbook to execute:', playbook.id, '-', playbook.title, '-', playbook.name)
  currentPlaybook.value = playbook
  
  // Update current phase
  if (currentPhase.value !== playbook.phase) {
    currentPhase.value = playbook.phase
  }
  
  // Update phase statuses
  await updateProgress()
  
  // Wait for Vue to update the DOM and component to mount
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 100))
  
  // Start playbook execution
  if (currentPlaybookExecutor.value && currentPlaybookExecutor.value.startExecution) {
    console.log('Starting playbook execution for:', playbook.name)
    
    // Get sudo password from sessionStorage
    const sudoPassword = sessionStorage.getItem('sudoPassword')
    
    currentPlaybookExecutor.value.startExecution({
      environment: {
        ANSIBLE_BECOME_PASSWORD: sudoPassword,
        ANSIBLE_SSH_PASSWORD: sudoPassword
      },
      extra_vars: playbook.extraVars || {}
    })
  } else {
    console.error('PlaybookExecutor not ready', currentPlaybookExecutor.value)
  }
}

// Handle playbook completion
const handlePlaybookComplete = async (result) => {
  console.log('=== PLAYBOOK COMPLETE ===')
  console.log('Completed playbook:', currentPlaybook.value?.title)
  console.log('Result:', result)
  
  // Check if playbook succeeded (status can be 'success' or 'ok')
  if (result.status === 'error' || result.status === 'failed' || result.status === 'cancelled') {
    console.log('Playbook failed or cancelled')
    
    // Mark as failed in state manager
    if (currentPlaybook.value) {
      const errorMsg = result.status === 'cancelled' 
        ? 'Cancelled by user' 
        : (result.message || 'Check the logs for details')
      try {
        await deploymentState.markFailed(currentPlaybook.value.id, errorMsg)
      } catch (e) {
        console.error('Failed to save deployment state:', e)
        // Show critical error to user
        alert(`CRITICAL: Failed to save deployment state: ${e.message}\n\nYour progress may be lost!`)
      }
    }
    
    if (result.status === 'cancelled') {
      deploymentError.value = `Deployment cancelled during: ${currentPlaybook.value.title}`
    } else {
      deploymentError.value = `Playbook ${currentPlaybook.value.title} failed: ${result.message || 'Check the logs for details'}`
    }
    
    // Update phase statuses
    await updateProgress()
    
    // Keep the playbook component visible so user can see the error/cancel modal
    // Don't set currentPlaybook to null here
    return
  }
  
  console.log('Playbook succeeded')
  
  // Clear any previous deployment error since the playbook succeeded
  deploymentError.value = ''
  
  // Mark as completed in state manager
  if (currentPlaybook.value) {
    try {
      await deploymentState.markCompleted(currentPlaybook.value.id)
    } catch (e) {
      console.error('Failed to save deployment state:', e)
      // Show critical error to user
      alert(`CRITICAL: Failed to save deployment state: ${e.message}\n\nYour progress may be lost!`)
      // Still show error in UI
      deploymentError.value = `Failed to save state: ${e.message}`
      return
    }
  }
  
  // Check if restart is required
  if (currentPlaybook.value?.requiresRestart) {
    console.log('Restart required, saving state...')
    showRestartNotice.value = true
    // Note: Restart state is handled by the state manager automatically
    return
  }
  
  console.log('No restart required, waiting for user to click Continue...')
  // Don't automatically continue - wait for user to click Continue button
  // The PlaybookExecutorStream component will emit 'continue' event when user clicks Continue
}

// Handle user clicking Continue button in playbook modal
const handlePlaybookContinue = () => {
  console.log('User clicked Continue...')
  
  // Check if the just-completed playbook requires restart
  if (currentPlaybook.value?.requiresRestart) {
    console.log('Playbook requires restart, showing restart notice...')
    currentPlaybook.value = null
    showRestartNotice.value = true
    // Note: Restart state is handled by the state manager automatically
    return
  }
  
  console.log('No restart required, clearing current playbook and executing next...')
  currentPlaybook.value = null
  executeNextPlaybook()
}

// Save all critical session data to localStorage for recovery after restart
const saveSessionDataForRestart = () => {
  const criticalKeys = [
    'networkConfiguration',
    'clusterNodes',
    'gpuAssignments',
    'serverHardware',
    'discoveredServers',
    'deploymentType',
    'currentUser',
    'sudoPassword',
    'generatedInventory'
  ]
  
  const sessionBackup = {}
  criticalKeys.forEach(key => {
    const value = sessionStorage.getItem(key)
    if (value) {
      sessionBackup[key] = value
    }
  })
  
  localStorage.setItem('thinkube-session-backup', JSON.stringify(sessionBackup))
}

// Restore session data from localStorage after restart
const restoreSessionDataAfterRestart = () => {
  const backup = localStorage.getItem('thinkube-session-backup')
  if (backup) {
    const sessionBackup = JSON.parse(backup)
    Object.entries(sessionBackup).forEach(([key, value]) => {
      sessionStorage.setItem(key, value)
    })
    // Clear the backup after restoring
    localStorage.removeItem('thinkube-session-backup')
    return true
  }
  return false
}

// Save configuration to backend for robust persistence
const saveConfigurationToBackend = async () => {
  const criticalKeys = [
    'networkConfiguration',
    'clusterNodes', 
    'gpuAssignments',
    'serverHardware',
    'discoveredServers',
    'deploymentType',
    'currentUser',
    'sudoPassword',
    'selectedServers',
    'servers',
    'zerotierApiToken',
    'zerotierNetworkId',
    'cloudflareToken',
    'githubToken'
  ]
  
  const config = {}
  criticalKeys.forEach(key => {
    const value = sessionStorage.getItem(key)
    if (value) {
      config[key] = value
    }
  })
  
  // Also save from localStorage
  const thinkubeConfig = localStorage.getItem('thinkube-config')
  if (thinkubeConfig) {
    config['thinkube-config'] = thinkubeConfig
  }
  
  try {
    await axios.post('/api/system/save-configuration', config)
    console.log('Configuration saved to backend')
  } catch (error) {
    console.error('Failed to save configuration to backend:', error)
    // Don't throw - continue with deployment even if backup fails
  }
}

// Restore configuration from backend
const restoreConfigurationFromBackend = async () => {
  try {
    const response = await axios.get('/api/system/load-configuration')
    if (response.data.exists && response.data.config) {
      const config = response.data.config
      
      // Restore to sessionStorage
      Object.entries(config).forEach(([key, value]) => {
        if (key === 'thinkube-config') {
          localStorage.setItem(key, value)
        } else {
          sessionStorage.setItem(key, value)
        }
      })
      
      console.log('Configuration restored from backend')
      return true
    }
    console.log('No backend configuration found')
  } catch (error) {
    console.error('Failed to restore configuration from backend:', error)
    // Don't throw - this is expected if the backend doesn't have the new endpoint yet
  }
  return false
}

// Automated restart of all servers in correct order
const automatedRestart = async () => {
  // Save all session data before restart
  saveSessionDataForRestart()
  
  // Note: The deployment state manager automatically handles restart state
  // by not advancing the currentIndex when a restart is needed
  
  // Now hide the restart notice for UI
  showRestartNotice.value = false
  
  // Create a special restart playbook entry
  const restartPlaybook = {
    id: 'restart-servers',
    phase: 'network',
    title: 'Restarting Servers (Ordered)',
    name: 'ansible/10_baremetal_infra/10-3_restart_servers_ordered.yaml',
    isRestart: true  // Special flag to handle differently
  }
  
  // Show the playbook executor for the restart
  currentPlaybook.value = restartPlaybook
  
  // Wait for component to mount
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 100))
  
  // Start the restart playbook
  if (currentPlaybookExecutor.value && currentPlaybookExecutor.value.startExecution) {
    const sudoPassword = sessionStorage.getItem('sudoPassword')
    
    currentPlaybookExecutor.value.startExecution({
      environment: {
        ANSIBLE_BECOME_PASSWORD: sudoPassword,
        ANSIBLE_SSH_PASSWORD: sudoPassword
      }
    })
  }
}

// Check systems after restart
const checkSystemsAfterRestart = async () => {
  try {
    // Check if all servers are reachable
    const servers = JSON.parse(sessionStorage.getItem('servers') || '[]')
    const checks = servers.map(server => 
      axios.post('/api/test-ssh', { ip_address: server.ip })
    )
    
    const results = await Promise.all(checks)
    const allOnline = results.every(r => r.data.success)
    
    if (allOnline) {
      showRestartNotice.value = false
      // State is already saved by deployment state manager
      executeNextPlaybook()
    } else {
      alert('Some servers are not yet reachable. Please wait and try again.')
    }
  } catch (error) {
    console.error('Error checking systems:', error)
    alert('Error checking system status. Please try again.')
  }
}


// Retry current playbook
const retryCurrentPlaybook = () => {
  // Clear the deployment error when retrying
  deploymentError.value = ''
  
  if (currentPlaybookExecutor.value && currentPlaybookExecutor.value.startExecution) {
    const sudoPassword = sessionStorage.getItem('sudoPassword')
    currentPlaybookExecutor.value.startExecution({
      environment: {
        ANSIBLE_BECOME_PASSWORD: sudoPassword,
        ANSIBLE_SSH_PASSWORD: sudoPassword
      },
      extra_vars: currentPlaybook.value?.extraVars || {}
    })
  }
}


// Reset deployment completely and go back to configuration
const resetDeployment = () => {
  deploymentState.clearState()
  deploymentError.value = ''
  deploymentComplete.value = false
  currentPlaybook.value = null
  currentPhase.value = null
  showRestartNotice.value = false
  router.push('/configuration')
}

// Retry failed playbooks
const retryDeployment = async () => {
  deploymentError.value = ''
  try {
    await deploymentState.resetFailed()
  } catch (e) {
    console.error('Failed to reset failed playbooks:', e)
    alert(`Failed to reset deployment state: ${e.message}`)
    return
  }
  executeNextPlaybook()
}

// Start deployment on mount
onMounted(async () => {
  console.log('Deploy component mounted')
  
  // First, check if we have a session backup (indicating a restart scenario)
  const hasBackup = localStorage.getItem('thinkube-session-backup') !== null
  
  if (hasBackup) {
    console.log('Found session backup, attempting restart recovery...')
    const sessionRestored = restoreSessionDataAfterRestart()
    if (!sessionRestored) {
      console.error('Failed to restore session data after restart')
      alert('Session data could not be restored. Please restart the installation.')
      router.push('/')
      return
    }
    console.log('Session data restored successfully')
  }
  
  // Check if we're coming from configuration screens (have session data)
  const cameFromConfig = sessionStorage.getItem('sudoPassword') !== null && 
                        sessionStorage.getItem('selectedServers') !== null
  
  console.log('Session check:', {
    cameFromConfig,
    hasBackup,
    sudoPassword: !!sessionStorage.getItem('sudoPassword'),
    selectedServers: !!sessionStorage.getItem('selectedServers')
  })
  
  // Load deployment state
  let savedState = await deploymentState.loadState()
  
  if (savedState && cameFromConfig && !hasBackup) {
    // User just configured everything but there's old state - clear it
    console.log('User completed configuration. Clearing old deployment state.')
    await deploymentState.clearState()
    savedState = null
  }
  
  if (savedState) {
    console.log('Resuming deployment from saved state')
    
    // If we have a saved state but no session data, try to restore from backup
    if (!sessionStorage.getItem('networkConfiguration')) {
      console.log('No session data found, checking for backup...')
      
      // First try backend persistence
      const restoredFromBackend = await restoreConfigurationFromBackend()
      
      if (!restoredFromBackend) {
        // Fall back to localStorage backup
        const backupExists = localStorage.getItem('thinkube-session-backup')
        if (backupExists) {
          console.log('Found session backup, restoring...')
          restoreSessionDataAfterRestart()
        } else {
          // If we can't restore, we need to clear the deployment state and start fresh
          console.error('No configuration found - clearing deployment state')
          await deploymentState.clearState()
          // Clear ALL stored data to ensure a clean start
          localStorage.clear()
          sessionStorage.clear()
          alert('Session configuration was lost. The deployment will need to be restarted from the beginning.')
          router.push('/')
          return
        }
      }
    }
    
    // Check if deployment is complete
    if (await deploymentState.isComplete()) {
      console.log('Deployment is already complete')
      deploymentComplete.value = true
      await updateProgress()
      return
    }
    
    // Update progress
    await updateProgress()
    
    // Continue deployment after a delay
    setTimeout(() => {
      executeNextPlaybook()
    }, hasBackup ? 5000 : 500)  // Longer delay after restart
    
  } else {
    // Fresh start - no saved state
    console.log('Starting fresh deployment')
    
    // Build the playbook queue
    const queue = buildPlaybookQueue()
    
    // Save session data before starting deployment (in case of failures)
    console.log('Saving session data before deployment starts...')
    saveSessionDataForRestart()
    
    // Also save to backend for proper persistence
    await saveConfigurationToBackend()
    
    // Initialize deployment state with the full queue
    try {
      await deploymentState.initializeDeployment(queue)
    } catch (e) {
      console.error('Failed to initialize deployment state:', e)
      alert(`Failed to initialize deployment: ${e.message}\n\nPlease check your system and try again.`)
      router.push('/configuration')
      return
    }
    
    // Update initial progress
    await updateProgress()
    
    // Start deployment
    setTimeout(() => {
      executeNextPlaybook()
    }, 500)
  }
  
  // Set up periodic progress updates
  const progressInterval = setInterval(async () => {
    if (!deploymentComplete.value && !deploymentError.value) {
      await updateProgress()
    }
  }, 2000)
  
  // Clean up interval on unmount
  onUnmounted(() => {
    clearInterval(progressInterval)
  })
})
</script>

<style scoped>
/* Custom styles for deployment view */
</style>