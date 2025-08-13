/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-6">Installation Progress</h1>
    
    <!-- Progress Overview -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <div class="text-center mb-6">
          <div class="radial-progress text-primary" 
               :style="`--value:${status.progress}; --size:12rem; --thickness:1rem;`">
            <span class="text-4xl font-bold progress-text">{{ status.progress }}%</span>
          </div>
        </div>
        
        <div class="flex justify-center gap-2 mb-4">
          <div class="badge" :class="getPhaseClass(status.phase)">
            {{ status.phase }}
          </div>
        </div>
        
        <p class="text-center text-lg mb-4">{{ status.current_task }}</p>
        
        <progress class="progress progress-primary w-full" :value="status.progress" max="100"></progress>
      </div>
    </div>

    <!-- Installation Logs -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <div class="flex items-center justify-between mb-4">
          <h2 class="card-title">Installation Logs</h2>
          <button 
            class="btn btn-ghost btn-sm btn-circle"
            @click="autoScroll = !autoScroll"
            :class="{ 'btn-active': autoScroll }"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    :d="autoScroll ? 'M19 14l-7 7m0 0l-7-7m7 7V3' : 'M5 10l7-7m0 0l7 7m-7-7v18'"></path>
            </svg>
          </button>
        </div>
        
        <div ref="logContainer" class="log-container bg-base-200 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm">
          <div v-for="(log, index) in status.logs" :key="index" class="mb-1">
            <span class="text-base-content text-opacity-60">{{ formatTime(new Date()) }}</span>
            <span class="ml-2">{{ log }}</span>
          </div>
          
          <div v-if="status.errors.length > 0" class="mt-4 border-t border-error pt-4">
            <div v-for="(error, index) in status.errors" :key="`error-${index}`" class="text-error mb-1">
              <span class="text-error text-opacity-60">{{ formatTime(new Date()) }}</span>
              <span class="ml-2">ERROR: {{ error }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Completion Actions -->
    <div v-if="isComplete" class="mt-6">
      <div v-if="status.phase === 'failed'" class="alert alert-error mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>Installation failed. Please check the logs for details.</span>
      </div>
      
      <button 
        class="btn btn-primary btn-block btn-lg gap-2"
        @click="continueNext"
      >
        {{ skipConfigMode ? 'Continue to Deployment' : 'Continue to Server Discovery' }}
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// Check if we're in skip-config mode
const skipConfigMode = sessionStorage.getItem('skipConfigMode') === 'true'

const status = ref({
  phase: 'starting',
  progress: 0,
  current_task: 'Initializing installation...',
  logs: [],
  errors: []
})

const logContainer = ref(null)
const autoScroll = ref(true)
let ws = null

const isComplete = computed(() => 
  status.value.phase === 'completed' || status.value.phase === 'failed'
)

const getPhaseClass = (phase) => {
  const classes = {
    idle: 'badge-ghost',
    starting: 'badge-info',
    running: 'badge-primary',
    completed: 'badge-success',
    failed: 'badge-error'
  }
  return classes[phase] || 'badge-ghost'
}

const formatTime = (date) => {
  return date.toTimeString().split(' ')[0]
}

const connectWebSocket = () => {
  // In Tauri, we need to connect directly to localhost:8000
  const isTauri = window.__TAURI__ !== undefined
  const wsBase = isTauri || window.location.protocol === 'http:' && window.location.hostname === 'localhost'
    ? 'ws://localhost:8000'
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
  
  // Try /ws first, then /api/ws
  let wsUrl = `${wsBase}/ws`
  let retryWithApi = true
  
  const createConnection = (url) => {
    console.log('Connecting to WebSocket:', url)
    ws = new WebSocket(url)
    
    ws.onopen = () => {
      console.log('WebSocket connected successfully')
      retryWithApi = false
    }
    
    ws.onmessage = (event) => {
      console.log('WebSocket message received:', event.data)
      const data = JSON.parse(event.data)
      status.value = data
      console.log('Status updated:', status.value)
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      if (retryWithApi && url.endsWith('/ws')) {
        // Try /api/ws endpoint
        retryWithApi = false
        wsUrl = `${wsBase}/api/ws`
        createConnection(wsUrl)
      }
    }
    
    ws.onclose = () => {
      // Reconnect after 5 seconds if not complete
      if (!isComplete.value) {
        setTimeout(() => createConnection(wsUrl), 5000)
      }
    }
  }
  
  createConnection(wsUrl)
}

watch(() => status.value.logs.length, async () => {
  if (autoScroll.value && logContainer.value) {
    await nextTick()
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
})

const continueNext = () => {
  if (skipConfigMode) {
    router.push('/deploy')
  } else {
    router.push('/server-discovery')
  }
}

onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.progress-text {
  animation: fade-pulse 1.5s ease-in-out infinite;
}

@keyframes fade-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.log-container {
  font-family: 'Courier New', monospace;
}
</style>