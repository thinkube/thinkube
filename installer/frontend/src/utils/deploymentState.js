/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Robust deployment state management
 * Tracks both the full playbook list and execution status
 * Persists to backend for survival across system restarts
 */

import axios from './axios'

export class DeploymentStateManager {
  constructor() {
    this.STORAGE_KEY = 'thinkube-deployment-state-v2'
    this.COMPLETED_KEY = 'thinkube-completed-playbooks'
  }

  /**
   * Save state to backend and localStorage (as backup)
   * @throws {Error} If state cannot be saved to either backend or localStorage
   */
  async saveState(state) {
    let backendError = null
    let localStorageError = null
    
    try {
      // Save to backend first (primary storage)
      await axios.post('/api/system/deployment-state', { state })
    } catch (e) {
      console.error('Failed to save deployment state to backend:', e)
      backendError = e
    }
    
    try {
      // Always try to save to localStorage as backup
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state))
    } catch (e) {
      console.error('Failed to save to localStorage:', e)
      localStorageError = e
    }
    
    // If BOTH failed, throw error - state wasn't saved anywhere!
    if (backendError && localStorageError) {
      throw new Error(`Failed to save deployment state anywhere! Backend: ${backendError.message}, LocalStorage: ${localStorageError.message}`)
    }
    
    // If only backend failed, warn but continue (localStorage saved it)
    if (backendError && !localStorageError) {
      console.warn('Backend save failed, but localStorage backup succeeded. State may be lost on system restart!')
      // Could emit a warning event here for UI to show
    }
  }

  /**
   * Load state from backend or localStorage
   * @returns {Object|null} The loaded state or null if no state exists
   * @throws {Error} If state exists but cannot be loaded due to corruption
   */
  async loadState() {
    let backendState = null
    let localStorageState = null
    let backendError = null
    
    // Try to load from backend first
    try {
      const response = await axios.get('/api/system/deployment-state')
      if (response.data.exists && response.data.state) {
        const state = response.data.state
        
        // Validate state structure
        if (!state || !state.allPlaybooks || !Array.isArray(state.allPlaybooks)) {
          throw new Error('Backend state is corrupted: missing required fields')
        }
        
        backendState = state
      }
    } catch (e) {
      console.error('Failed to load deployment state from backend:', e)
      backendError = e
    }
    
    // Try to load from localStorage
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY)
      if (stored) {
        const state = JSON.parse(stored)
        
        // Validate state structure
        if (!state || !state.allPlaybooks || !Array.isArray(state.allPlaybooks)) {
          throw new Error('LocalStorage state is corrupted: missing required fields')
        }
        
        localStorageState = state
      }
    } catch (e) {
      console.error('Failed to load deployment state from localStorage:', e)
      // If localStorage is corrupted, remove it
      try {
        localStorage.removeItem(this.STORAGE_KEY)
      } catch (removeError) {
        console.error('Failed to remove corrupted localStorage:', removeError)
      }
    }
    
    // Decide which state to use
    if (backendState && localStorageState) {
      // Both exist - use the more recent one
      const backendTime = new Date(backendState.timestamp || 0).getTime()
      const localTime = new Date(localStorageState.timestamp || 0).getTime()
      
      if (backendTime >= localTime) {
        // Sync newer backend state to localStorage
        try {
          localStorage.setItem(this.STORAGE_KEY, JSON.stringify(backendState))
        } catch (e) {
          console.error('Failed to sync backend state to localStorage:', e)
        }
        return backendState
      } else {
        // LocalStorage is newer (maybe backend was down?) - sync it to backend
        try {
          await axios.post('/api/system/deployment-state', { state: localStorageState })
        } catch (e) {
          console.error('Failed to sync localStorage state to backend:', e)
        }
        return localStorageState
      }
    } else if (backendState) {
      // Only backend exists
      try {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(backendState))
      } catch (e) {
        console.error('Failed to sync backend state to localStorage:', e)
      }
      return backendState
    } else if (localStorageState) {
      // Only localStorage exists - try to save to backend
      if (!backendError) {
        // Backend was accessible but had no state - save localStorage state there
        try {
          await axios.post('/api/system/deployment-state', { state: localStorageState })
        } catch (e) {
          console.error('Failed to sync localStorage state to backend:', e)
        }
      }
      return localStorageState
    }
    
    // No state exists anywhere
    return null
  }

  /**
   * Clear all deployment state
   * @throws {Error} If state cannot be cleared
   */
  async clearState() {
    const errors = []
    
    try {
      // Clear from backend
      await axios.delete('/api/system/deployment-state')
    } catch (e) {
      console.error('Failed to clear deployment state from backend:', e)
      errors.push(`Backend: ${e.message}`)
    }
    
    try {
      // Clear from localStorage
      localStorage.removeItem(this.STORAGE_KEY)
      localStorage.removeItem(this.COMPLETED_KEY)
    } catch (e) {
      console.error('Failed to clear localStorage:', e)
      errors.push(`LocalStorage: ${e.message}`)
    }
    
    if (errors.length > 0) {
      throw new Error(`Failed to clear deployment state: ${errors.join(', ')}`)
    }
  }

  /**
   * Initialize a new deployment with the full playbook list
   * @throws {Error} If initialization fails
   */
  async initializeDeployment(playbooks) {
    if (!playbooks || !Array.isArray(playbooks) || playbooks.length === 0) {
      throw new Error('Cannot initialize deployment with empty or invalid playbook list')
    }
    
    const state = {
      version: 2,
      timestamp: new Date().toISOString(),
      allPlaybooks: playbooks.map(p => ({
        ...p,
        status: 'pending'
      })),
      currentIndex: 0,
      completedIds: [],
      failedIds: []
    }
    
    await this.saveState(state)
    return state
  }

  /**
   * Get the current deployment state
   */
  async getCurrentState() {
    try {
      const state = await this.loadState()
      if (!state) {
        return {
          hasState: false,
          allPlaybooks: [],
          completedIds: [],
          failedIds: [],
          currentIndex: 0
        }
      }

      return {
        hasState: true,
        ...state
      }
    } catch (e) {
      console.error('Error loading current state:', e)
      throw e
    }
  }

  /**
   * Mark a playbook as completed
   * @throws {Error} If state update fails
   */
  async markCompleted(playbookId) {
    if (!playbookId) {
      throw new Error('Cannot mark playbook as completed: invalid playbook ID')
    }
    
    const state = await this.loadState()
    if (!state) {
      throw new Error('Cannot mark playbook as completed: no deployment state found')
    }

    // Update playbook status
    const playbook = state.allPlaybooks.find(p => p.id === playbookId)
    if (!playbook) {
      throw new Error(`Cannot mark playbook as completed: playbook ${playbookId} not found in state`)
    }
    
    playbook.status = 'completed'

    // Add to completed list if not already there
    if (!state.completedIds.includes(playbookId)) {
      state.completedIds.push(playbookId)
    }

    // Remove from failed list if it was there
    state.failedIds = state.failedIds.filter(id => id !== playbookId)

    // Update current index
    const currentPlaybook = state.allPlaybooks[state.currentIndex]
    if (currentPlaybook && currentPlaybook.id === playbookId) {
      state.currentIndex++
    }

    await this.saveState(state)
  }

  /**
   * Mark a playbook as failed
   * @throws {Error} If state update fails
   */
  async markFailed(playbookId, error) {
    if (!playbookId) {
      throw new Error('Cannot mark playbook as failed: invalid playbook ID')
    }
    
    const state = await this.loadState()
    if (!state) {
      throw new Error('Cannot mark playbook as failed: no deployment state found')
    }

    // Update playbook status
    const playbook = state.allPlaybooks.find(p => p.id === playbookId)
    if (!playbook) {
      throw new Error(`Cannot mark playbook as failed: playbook ${playbookId} not found in state`)
    }
    
    playbook.status = 'failed'
    playbook.error = error || 'Unknown error'

    // Add to failed list if not already there
    if (!state.failedIds.includes(playbookId)) {
      state.failedIds.push(playbookId)
    }

    // DO NOT update current index - we should not skip failed playbooks!
    // The deployment should stop at the failed playbook until it's resolved

    await this.saveState(state)
  }

  /**
   * Get the next playbook to execute
   */
  async getNextPlaybook() {
    const state = await this.loadState()
    if (!state) return null

    // Check if we're still at a valid index
    if (state.currentIndex >= state.allPlaybooks.length) {
      return null
    }

    const currentPlaybook = state.allPlaybooks[state.currentIndex]
    
    // If current playbook is failed, return null (don't skip it)
    if (currentPlaybook.status === 'failed') {
      console.log('Current playbook is failed, deployment should stop here:', currentPlaybook.id)
      return null
    }
    
    // If current playbook is pending, return it
    if (currentPlaybook.status === 'pending') {
      return {
        playbook: currentPlaybook,
        index: state.currentIndex,
        total: state.allPlaybooks.length
      }
    }
    
    // If current playbook is completed, move to next
    if (currentPlaybook.status === 'completed') {
      // Find the next pending playbook
      for (let i = state.currentIndex + 1; i < state.allPlaybooks.length; i++) {
        const playbook = state.allPlaybooks[i]
        if (playbook.status === 'pending') {
          return {
            playbook,
            index: i,
            total: state.allPlaybooks.length
          }
        }
        // Stop at first failed playbook
        if (playbook.status === 'failed') {
          console.log('Found failed playbook in sequence, deployment should stop:', playbook.id)
          return null
        }
      }
    }

    // No more pending playbooks
    return null
  }

  /**
   * Reset failed playbooks for retry
   * @throws {Error} If state update fails
   */
  async resetFailed() {
    const state = await this.loadState()
    if (!state) {
      throw new Error('Cannot reset failed playbooks: no deployment state found')
    }

    // Reset status of failed playbooks
    state.allPlaybooks.forEach(p => {
      if (p.status === 'failed') {
        p.status = 'pending'
        delete p.error
      }
    })

    // Clear failed list
    state.failedIds = []
    
    // Reset current index to start checking from beginning
    state.currentIndex = 0

    await this.saveState(state)
  }

  /**
   * Get progress information
   */
  async getProgress() {
    try {
      const state = await this.loadState()
      if (!state) {
        return {
          completed: 0,
          failed: 0,
          total: 0,
          percentage: 0
        }
      }

      const completed = state.completedIds.length
      const failed = state.failedIds.length
      const total = state.allPlaybooks.length
      const percentage = total > 0 ? Math.round((completed / total) * 100) : 0

      return {
        completed,
        failed,
        total,
        percentage
      }
    } catch (e) {
      console.error('Error getting progress:', e)
      // Return safe defaults if there's an error
      return {
        completed: 0,
        failed: 0,
        total: 0,
        percentage: 0
      }
    }
  }

  /**
   * Check if deployment is complete
   */
  async isComplete() {
    try {
      const state = await this.loadState()
      if (!state) return false

      return state.completedIds.length === state.allPlaybooks.length
    } catch (e) {
      console.error('Error checking if deployment is complete:', e)
      return false
    }
  }

  /**
   * Get failed playbooks
   */
  async getFailedPlaybooks() {
    try {
      const state = await this.loadState()
      if (!state) return []

      return state.allPlaybooks.filter(p => p.status === 'failed')
    } catch (e) {
      console.error('Error getting failed playbooks:', e)
      return []
    }
  }
}

// Export a singleton instance
export const deploymentState = new DeploymentStateManager()