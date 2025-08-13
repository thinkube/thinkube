/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

import { ref, Ref } from 'vue'

export interface StreamMessage {
  type: 'start' | 'play' | 'task' | 'ok' | 'changed' | 'failed' | 'output' | 'complete' | 'error'
  message?: string
  task_name?: string
  task_number?: number
  task?: string
  status?: 'success' | 'error'
  return_code?: number
  playbook?: string
}

export interface PlaybookStreamState {
  isConnected: Ref<boolean>
  isExecuting: Ref<boolean>
  messages: Ref<StreamMessage[]>
  currentTask: Ref<string>
  taskCount: Ref<number>
  error: Ref<string | null>
}

export function usePlaybookStream() {
  const isConnected = ref(false)
  const isExecuting = ref(false)
  const messages = ref<StreamMessage[]>([])
  const currentTask = ref('Initializing...')
  const taskCount = ref(0)
  const error = ref<string | null>(null)
  
  let ws: WebSocket | null = null
  let resolveExecution: ((value: any) => void) | null = null
  let rejectExecution: ((reason?: any) => void) | null = null
  
  const connect = (playbookName: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const wsUrl = `ws://localhost:8000/ws/playbook/${playbookName}`
      ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        isConnected.value = true
        resolve()
      }
      
      ws.onerror = (event) => {
        error.value = 'WebSocket connection failed'
        reject(new Error('WebSocket connection failed'))
      }
      
      ws.onmessage = (event) => {
        try {
          const message: StreamMessage = JSON.parse(event.data)
          messages.value.push(message)
          
          switch (message.type) {
            case 'start':
              isExecuting.value = true
              break
              
            case 'task':
              currentTask.value = message.task_name || 'Unknown task'
              taskCount.value = message.task_number || 0
              break
              
            case 'complete':
              isExecuting.value = false
              if (message.status === 'success') {
                resolveExecution?.({ status: 'success', return_code: message.return_code })
              } else {
                rejectExecution?.(new Error(message.message || 'Playbook execution failed'))
              }
              break
              
            case 'error':
              error.value = message.message || 'Unknown error'
              isExecuting.value = false
              rejectExecution?.(new Error(message.message))
              break
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }
      
      ws.onclose = () => {
        isConnected.value = false
        isExecuting.value = false
      }
    })
  }
  
  const execute = (params: { environment?: Record<string, string>, extra_vars?: Record<string, any> }): Promise<any> => {
    return new Promise((resolve, reject) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'))
        return
      }
      
      resolveExecution = resolve
      rejectExecution = reject
      
      // Clear previous messages
      messages.value = []
      error.value = null
      
      // Send execution parameters
      ws.send(JSON.stringify(params))
    })
  }
  
  const disconnect = () => {
    if (ws) {
      ws.close()
      ws = null
    }
    isConnected.value = false
    isExecuting.value = false
  }
  
  return {
    // State
    isConnected,
    isExecuting,
    messages,
    currentTask,
    taskCount,
    error,
    
    // Methods
    connect,
    execute,
    disconnect
  }
}

// Helper function to execute SSH setup with streaming
export async function streamSSHSetup(
  servers: Array<{ hostname: string, ip: string }>,
  username: string,
  password: string
): Promise<any> {
  const stream = usePlaybookStream()
  
  try {
    // Connect to WebSocket
    await stream.connect('setup-ssh-keys')
    
    // Execute playbook
    const result = await stream.execute({
      environment: {
        ANSIBLE_BECOME_PASSWORD: password,
        ANSIBLE_SSH_PASSWORD: password
      },
      extra_vars: {
        ansible_user: username,
        ansible_ssh_pass: password,
        ansible_become_pass: password
      }
    })
    
    return result
  } finally {
    // Always disconnect
    stream.disconnect()
  }
}