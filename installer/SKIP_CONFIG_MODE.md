# Skip Configuration Mode

The installer now supports two command-line options for faster re-runs:

## Usage

```bash
# Clean deployment state but keep inventory
./test-dev.sh --clean-state

# Skip configuration screens and reuse existing inventory
./test-dev.sh --skip-config

# Both options together - start fresh deployment with existing configuration
./test-dev.sh --clean-state --skip-config
```

## How it works

### --clean-state
- Removes the Tauri app data directory (`~/.config/thinkube-installer`)
- Clears localStorage and sessionStorage (deployment progress, etc.)
- **Preserves `inventory.yaml`** so configuration can be reused
- Allows starting a fresh deployment without re-entering all configuration

### --skip-config
1. On startup, checks if `inventory.yaml` exists
2. If found, loads it via the backend API
3. Skips all configuration screens
4. Still prompts for sudo password (required for operations)
5. Still runs tools installation if needed
6. After tools installation, goes directly to deployment

## Implementation Details

1. **Backend**: Added `/api/system/check-inventory` endpoint to read existing inventory
2. **Frontend**: 
   - Modified Welcome.vue to check for skip-config mode
   - Updated SudoPassword.vue to route correctly after verification
   - Updated Installation.vue to route to deployment in skip-config mode
3. **Tauri**: Added command to check environment variables
4. **Script**: Updated test-dev.sh to parse command-line arguments

## Notes

- The inventory is automatically saved when generated during normal runs
- Skip-config mode requires at least one successful configuration run
- Tools installation is still performed if needed, even in skip-config mode