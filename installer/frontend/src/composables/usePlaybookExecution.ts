/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Composable for standardized Ansible playbook execution
 */

import { ref, type Ref } from 'vue'

interface PlaybookExecutionOptions {
  endpoint: string
  payload?: Record<string, any>
  timeout?: number
  onProgress?: (progress: PlaybookProgress) => void
  onComplete?: (result: PlaybookResult) => void
  onError?: (error: string) => void
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
  stdout?: string
  stderr?: string
}

export function usePlaybookExecution() {
  const isExecuting = ref(false)
  const currentExecution = ref<AbortController | null>(null)

  /**
   * Execute a playbook via API endpoint
   */
  const executePlaybook = async (options: PlaybookExecutionOptions): Promise<PlaybookResult> => {
    if (isExecuting.value) {
      throw new Error('Another playbook is already executing')
    }

    isExecuting.value = true
    const controller = new AbortController()
    currentExecution.value = controller

    try {
      // Send initial progress update
      if (options.onProgress) {
        options.onProgress({
          status: 'running',
          message: 'Starting playbook execution...',
          progress_percent: 0,
          current_task: 'Initializing'
        })
      }

      // Make API request
      const response = await fetch(options.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(options.payload || {}),
        signal: controller.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result: PlaybookResult = await response.json()

      // Send completion progress update
      if (options.onProgress) {
        options.onProgress({
          status: result.status,
          message: result.message,
          progress_percent: 100,
          details: result.details
        })
      }

      // Call completion callback
      if (options.onComplete) {
        options.onComplete(result)
      }

      return result

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      
      // Send error progress update
      if (options.onProgress) {
        options.onProgress({
          status: 'error',
          message: 'Execution failed',
          details: errorMessage
        })
      }

      // Call error callback
      if (options.onError) {
        options.onError(errorMessage)
      }

      // Return error result
      const errorResult: PlaybookResult = {
        status: 'error',
        message: 'Playbook execution failed',
        details: errorMessage
      }

      return errorResult

    } finally {
      isExecuting.value = false
      currentExecution.value = null
    }
  }

  /**
   * Cancel the current execution
   */
  const cancelExecution = () => {
    if (currentExecution.value) {
      currentExecution.value.abort()
      currentExecution.value = null
      isExecuting.value = false
    }
  }

  /**
   * Pre-configured execution methods for common playbooks
   */
  const executeSSHSetup = async (
    servers: any[], 
    username: string, 
    password: string,
    callbacks?: {
      onProgress?: (progress: PlaybookProgress) => void
      onComplete?: (result: PlaybookResult) => void
      onError?: (error: string) => void
    }
  ): Promise<PlaybookResult> => {
    return executePlaybook({
      endpoint: '/api/setup-ssh-keys',
      payload: {
        servers,
        username,
        password
      },
      timeout: 180000, // 3 minutes
      ...callbacks
    })
  }

  /**
   * Pre-configured execution method for MicroK8s setup
   */
  const executeMicroK8sSetup = async (
    servers: any[], 
    username: string, 
    password: string,
    callbacks?: {
      onProgress?: (progress: PlaybookProgress) => void
      onComplete?: (result: PlaybookResult) => void
      onError?: (error: string) => void
    }
  ): Promise<PlaybookResult> => {
    return executePlaybook({
      endpoint: '/api/playbooks/microk8s-setup',
      payload: {
        servers,
        username,
        password
      },
      timeout: 600000, // 10 minutes
      ...callbacks
    })
  }

  /**
   * Pre-configured execution method for Keycloak deployment
   */
  const executeKeycloakDeploy = async (
    adminUsername: string,
    adminPassword: string,
    domainName?: string,
    callbacks?: {
      onProgress?: (progress: PlaybookProgress) => void
      onComplete?: (result: PlaybookResult) => void
      onError?: (error: string) => void
    }
  ): Promise<PlaybookResult> => {
    return executePlaybook({
      endpoint: '/api/playbooks/keycloak-deploy',
      payload: {
        admin_username: adminUsername,
        admin_password: adminPassword,
        domain_name: domainName
      },
      timeout: 300000, // 5 minutes
      ...callbacks
    })
  }

  /**
   * Pre-configured execution method for Harbor deployment
   */
  const executeHarborDeploy = async (
    adminUsername: string,
    adminPassword: string,
    domainName?: string,
    callbacks?: {
      onProgress?: (progress: PlaybookProgress) => void
      onComplete?: (result: PlaybookResult) => void
      onError?: (error: string) => void
    }
  ): Promise<PlaybookResult> => {
    return executePlaybook({
      endpoint: '/api/playbooks/harbor-deploy',
      payload: {
        admin_username: adminUsername,
        admin_password: adminPassword,
        domain_name: domainName
      },
      timeout: 600000, // 10 minutes
      ...callbacks
    })
  }

  return {
    isExecuting: isExecuting as Readonly<Ref<boolean>>,
    executePlaybook,
    cancelExecution,
    executeSSHSetup,
    executeMicroK8sSetup,
    executeKeycloakDeploy,
    executeHarborDeploy
  }
}

/**
 * Utility function to create a standardized playbook execution handler
 */
export function createPlaybookHandler(
  executor: ReturnType<typeof usePlaybookExecution>,
  playbookExecutorRef: Ref<any>
) {
  return async (
    executionFn: () => Promise<PlaybookResult>,
    title: string = 'Executing Playbook'
  ) => {
    if (!playbookExecutorRef.value) {
      console.error('PlaybookExecutor component ref not available')
      return
    }

    // Start the execution UI
    playbookExecutorRef.value.startExecution()

    try {
      // Execute the playbook
      const result = await executionFn()

      // Complete the execution UI
      playbookExecutorRef.value.completeExecution(result)

      return result
    } catch (error) {
      // Handle execution error
      const errorResult: PlaybookResult = {
        status: 'error',
        message: 'Execution failed',
        details: error instanceof Error ? error.message : 'Unknown error'
      }

      playbookExecutorRef.value.completeExecution(errorResult)
      return errorResult
    }
  }
}