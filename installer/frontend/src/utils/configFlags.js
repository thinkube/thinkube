/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

import { invoke } from '@tauri-apps/api/core'

let cachedFlags = null

export async function getConfigFlags() {
  if (cachedFlags === null) {
    try {
      const [skipConfig, cleanState] = await invoke('get_config_flags')
      cachedFlags = { skipConfig, cleanState }
    } catch (error) {
      console.error('Failed to get config flags:', error)
      cachedFlags = { skipConfig: false, cleanState: false }
    }
  }
  return cachedFlags
}

export async function shouldSkipConfig() {
  const flags = await getConfigFlags()
  return flags.skipConfig
}

export async function shouldCleanState() {
  const flags = await getConfigFlags()
  return flags.cleanState
}