/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="playbook-executor">
    <!-- Progress Modal -->
    <div v-if="isExecuting" class="modal modal-open">
      <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-lg mb-4">{{ title }}</h3>
        
        <!-- Progress Bar -->
        <div class="mb-4">
          <div class="flex justify-between text-sm mb-1">
            <span>{{ currentStatus }}</span>
            <span v-if="progressPercent !== null">{{ progressPercent }}%</span>
          </div>
          <progress 
            class="progress progress-primary w-full" 
            :value="progressPercent || 0" 
            max="100"
          ></progress>
        </div>
        
        <!-- Current Task -->
        <div v-if="currentTask" class="mb-4">
          <div class="text-sm text-gray-600 mb-1">Current Task:</div>
          <div class="text-sm font-mono bg-base-200 p-2 rounded">{{ currentTask }}</div>
        </div>
        
        <!-- Details -->
        <div v-if="details" class="mb-4">
          <div class="text-sm text-gray-600 mb-1">Details:</div>
          <div class="text-sm bg-base-200 p-2 rounded max-h-32 overflow-y-auto">{{ details }}</div>
        </div>
        
        <!-- Loading Animation -->
        <div v-if="status === 'running'" class="flex items-center justify-center py-4">
          <span class="loading loading-spinner loading-lg text-primary"></span>
          <span class="ml-3">Executing playbook...</span>
        </div>
        
        <!-- Cancel Button (only during execution) -->
        <div v-if="status === 'running'" class="modal-action">
          <button class="btn btn-outline" @click="cancelExecution" :disabled="isCancelling">
            <span v-if="isCancelling" class="loading loading-spinner loading-sm"></span>
            {{ isCancelling ? 'Cancelling...' : 'Cancel' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Result Modal -->
    <div v-if="showResult" class="modal modal-open">
      <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-lg mb-4">{{ title }}</h3>
        
        <!-- Success Result -->
        <div v-if="status === 'success'" class="alert alert-success mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ message }}</span>
        </div>
        
        <!-- Error Result -->
        <div v-if="status === 'error'" class="alert alert-error mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ message }}</span>
        </div>
        
        <!-- Execution Details -->
        <div v-if="details" class="mb-4">
          <div class="text-sm text-gray-600 mb-2">Details:</div>
          <div class="text-sm bg-base-200 p-3 rounded font-mono max-h-40 overflow-y-auto whitespace-pre-wrap">{{ details }}</div>
        </div>
        
        <!-- Execution Stats -->
        <div v-if="duration" class="mb-4">
          <div class="text-sm text-gray-600">
            Execution completed in {{ formatDuration(duration) }}
          </div>
        </div>
        
        <!-- Actions -->
        <div class="modal-action">
          <button class="btn btn-primary" @click="closeResult">
            {{ status === 'success' ? 'Continue' : 'Close' }}
          </button>
          <button v-if="status === 'error' && onRetry" class="btn btn-outline" @click="retry">
            Retry
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface PlaybookExecutorProps {
  title: string
  onRetry?: () => void
}

interface PlaybookProgress {
  status: 'pending' | 'running' | 'success' | 'error' | 'cancelled'
  message: string
  progress_percent?: number
  current_task?: string
  details?: string
}

interface PlaybookResult {
  status: 'success' | 'error'
  message: string
  details?: string
  duration?: number
  return_code?: number
}

const props = defineProps<PlaybookExecutorProps>()

// Reactive state
const isExecuting = ref(false)
const showResult = ref(false)
const status = ref<'pending' | 'running' | 'success' | 'error' | 'cancelled'>('pending')
const message = ref('')
const details = ref('')
const progressPercent = ref<number | null>(null)
const currentTask = ref('')
const duration = ref<number | null>(null)
const isCancelling = ref(false)

// Computed properties
const currentStatus = computed(() => {
  switch (status.value) {
    case 'pending': return 'Preparing...'
    case 'running': return 'Executing playbook...'
    case 'success': return 'Completed successfully'
    case 'error': return 'Execution failed'
    case 'cancelled': return 'Execution cancelled'
    default: return ''
  }
})

// Methods
const startExecution = () => {
  isExecuting.value = true
  showResult.value = false
  status.value = 'running'
  message.value = ''
  details.value = ''
  progressPercent.value = 0
  currentTask.value = 'Initializing...'
  duration.value = null
  isCancelling.value = false
}

const updateProgress = (progress: PlaybookProgress) => {
  status.value = progress.status
  message.value = progress.message
  if (progress.progress_percent !== undefined) {
    progressPercent.value = progress.progress_percent
  }
  if (progress.current_task) {
    currentTask.value = progress.current_task
  }
  if (progress.details) {
    details.value = progress.details
  }
}

const completeExecution = (result: PlaybookResult) => {
  isExecuting.value = false
  showResult.value = true
  status.value = result.status
  message.value = result.message
  details.value = result.details || ''
  duration.value = result.duration
  progressPercent.value = 100
}

const cancelExecution = () => {
  isCancelling.value = true
  // In a real implementation, this would send a cancel request to the backend
  setTimeout(() => {
    status.value = 'cancelled'
    message.value = 'Execution was cancelled'
    isExecuting.value = false
    showResult.value = true
    isCancelling.value = false
  }, 1000)
}

const closeResult = () => {
  showResult.value = false
  // Reset state
  status.value = 'pending'
  message.value = ''
  details.value = ''
  progressPercent.value = null
  currentTask.value = ''
  duration.value = null
}

const retry = () => {
  if (props.onRetry) {
    closeResult()
    props.onRetry()
  }
}

const formatDuration = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds.toFixed(1)} seconds`
  } else {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return `${minutes}m ${remainingSeconds}s`
  }
}

// Expose methods to parent component
defineExpose({
  startExecution,
  updateProgress,
  completeExecution,
  cancelExecution
})
</script>

<style scoped>
.playbook-executor {
  /* Component-specific styles if needed */
}

/* Ensure modals appear above other content */
.modal {
  z-index: 1000;
}

/* Custom scrollbar for details sections */
.max-h-32::-webkit-scrollbar,
.max-h-40::-webkit-scrollbar {
  width: 6px;
}

.max-h-32::-webkit-scrollbar-track,
.max-h-40::-webkit-scrollbar-track {
  background: transparent;
}

.max-h-32::-webkit-scrollbar-thumb,
.max-h-40::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
}

.max-h-32::-webkit-scrollbar-thumb:hover,
.max-h-40::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.5);
}
</style>