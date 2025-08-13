# Ansible Playbook Execution Pattern

This document explains the standardized pattern for executing Ansible playbooks in the thinkube installer with consistent UI feedback.

## Architecture Overview

The pattern consists of three main components:

1. **Backend Service** (`app/services/ansible_executor.py`) - Reusable Ansible execution service
2. **Frontend Component** (`components/PlaybookExecutor.vue`) - Standardized UI for playbook execution
3. **Frontend Composable** (`composables/usePlaybookExecution.ts`) - API interaction and state management

## Backend Implementation

### 1. Create API Endpoint

```python
# app/api/your_service.py
from ..services.ansible_executor import ansible_executor

@router.post("/your-playbook")
async def execute_your_playbook(request: Dict[str, Any]):
    """Execute your custom playbook"""
    # Extract parameters from request
    param1 = request.get("param1")
    param2 = request.get("param2")
    
    # Define playbook path (relative to thinkube root)
    playbook_path = "ansible/path/to/your/playbook.yaml"
    
    # Set up extra variables (optional)
    extra_vars = {
        "param1": param1,
        "param2": param2
    }
    
    # Set up environment variables (optional)
    environment = {}
    if password := request.get("password"):
        environment["ANSIBLE_BECOME_PASSWORD"] = password
    
    # Execute the playbook
    result = await ansible_executor.execute_playbook(
        playbook_path=playbook_path,
        extra_vars=extra_vars,
        environment=environment,
        timeout=300  # 5 minutes
    )
    
    # Return standardized response
    return ansible_executor.format_result_for_api(result)
```

### 2. Register Router

```python
# main.py
from app.api.your_service import router as your_service_router

app.include_router(your_service_router)
```

## Frontend Implementation

### 1. Add Method to Composable

```typescript
// composables/usePlaybookExecution.ts
const executeYourPlaybook = async (
  param1: string,
  param2: string,
  callbacks?: {
    onProgress?: (progress: PlaybookProgress) => void
    onComplete?: (result: PlaybookResult) => void
    onError?: (error: string) => void
  }
): Promise<PlaybookResult> => {
  return executePlaybook({
    endpoint: '/api/your-playbook',
    payload: {
      param1,
      param2
    },
    timeout: 300000, // 5 minutes
    ...callbacks
  })
}

// Export in return statement
return {
  // ... other exports
  executeYourPlaybook
}
```

### 2. Use in Vue Component

```vue
<template>
  <div>
    <!-- Your existing UI -->
    
    <!-- Playbook execution button -->
    <button 
      class="btn btn-primary" 
      @click="runPlaybook"
      :disabled="playbookExecution.isExecuting.value"
    >
      Execute Playbook
    </button>
    
    <!-- Standardized Playbook Executor -->
    <PlaybookExecutor 
      ref="playbookExecutor" 
      title="Your Playbook Execution"
      :on-retry="runPlaybook"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import PlaybookExecutor from '@/components/PlaybookExecutor.vue'
import { usePlaybookExecution, createPlaybookHandler } from '@/composables/usePlaybookExecution'

const playbookExecutor = ref()
const playbookExecution = usePlaybookExecution()
const executePlaybook = createPlaybookHandler(playbookExecution, playbookExecutor)

const runPlaybook = async () => {
  const result = await executePlaybook(
    () => playbookExecution.executeYourPlaybook(
      "param1_value",
      "param2_value"
    ),
    'Your Playbook Execution'
  )
  
  if (result?.status === 'success') {
    // Handle success
    console.log('Playbook completed successfully')
  } else {
    // Handle error
    console.error('Playbook failed:', result?.details)
  }
}
</script>
```

## Features

### Backend Features

- **Standardized Error Handling**: Consistent error responses across all playbooks
- **Timeout Management**: Configurable timeouts with graceful handling
- **Environment Variables**: Easy setup of Ansible environment variables
- **Extra Variables**: Support for passing variables to playbooks
- **Progress Tracking**: Foundation for progress callbacks
- **Logging**: Comprehensive logging of execution details

### Frontend Features

- **Consistent UI**: Standardized modal dialogs for all playbook executions
- **Progress Indicators**: Visual progress bars and status updates
- **Error Display**: Formatted error messages with details
- **Retry Functionality**: Built-in retry capability for failed executions
- **Cancellation**: Ability to cancel running playbooks
- **Duration Tracking**: Execution time display

## Example Usage

### SSH Setup (Already Implemented)

```typescript
// Usage in component
const setupSSH = async () => {
  const result = await executePlaybook(
    () => playbookExecution.executeSSHSetup(
      servers.value,
      currentUser.value,
      sudoPassword
    ),
    'SSH Key Setup'
  )
  
  if (result?.status === 'success') {
    router.push('/next-step')
  }
}
```

### Additional Playbooks

The pattern is already set up for:

- **MicroK8s Setup**: `executeMicroK8sSetup()`
- **Keycloak Deployment**: `executeKeycloakDeploy()`
- **Harbor Deployment**: `executeHarborDeploy()`

## Benefits

1. **Code Reusability**: Single service handles all playbook executions
2. **Consistent UX**: Uniform experience across all playbook operations
3. **Maintainability**: Changes to execution logic apply to all playbooks
4. **Error Handling**: Standardized error responses and user feedback
5. **Extensibility**: Easy to add new playbooks following the same pattern
6. **Testing**: Simplified testing with consistent interfaces

## Best Practices

1. **Timeout Configuration**: Set appropriate timeouts based on playbook complexity
2. **Error Messages**: Provide meaningful error messages for users
3. **Progress Updates**: Use progress callbacks for long-running operations
4. **Parameter Validation**: Validate required parameters before execution
5. **Environment Setup**: Properly configure environment variables for Ansible
6. **Logging**: Include comprehensive logging for debugging

## Future Enhancements

- **WebSocket Integration**: Real-time progress updates via WebSocket
- **Parallel Execution**: Support for running multiple playbooks concurrently
- **Execution History**: Track and display playbook execution history
- **Dynamic Progress**: Parse Ansible output for more detailed progress tracking
- **Rollback Support**: Integration with rollback playbooks for failed executions