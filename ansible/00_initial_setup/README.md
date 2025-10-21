# Initial Setup Playbooks

This directory contains playbooks for initial system setup and configuration.

## Playbooks

### 30_reserve_gpus.yaml - GPU Passthrough Configuration

Configures GPU passthrough by binding specific GPUs to VFIO-PCI for VM passthrough.

#### Features

- Detects all GPUs in the system (NVIDIA, AMD, Intel)
- Identifies IOMMU groups and passthrough eligibility
- Supports explicit PCI slot assignment via inventory
- Handles identical GPUs intelligently
- Configures VFIO-PCI binding for passthrough

#### GPU Passthrough Eligibility

**Important**: Not all GPUs can be passed through. A GPU is only eligible for passthrough if:
- IOMMU is enabled and working
- The GPU is in an IOMMU group that contains ONLY:
  - The GPU itself
  - Its associated audio controller (if present)
  
GPUs that share IOMMU groups with other devices (USB controllers, network cards, etc.) CANNOT be passed through without passing through all devices in the group, which would break host functionality.

In practice, this means:
- Discrete GPUs in PCIe slots are often eligible
- Integrated GPUs (like AMD APU graphics) typically remain with the host for display
- Some motherboard PCIe slots may have better IOMMU isolation than others

#### Handling Identical GPUs

**Enhancement implemented to handle systems with multiple identical GPUs (e.g., two RTX 3090s):**

The playbook now detects when assigned GPUs have PCI IDs that match other GPUs in the system. When duplicate PCI IDs are found:

1. **Skips PCI ID-based binding** - Does NOT add PCI IDs to `/etc/modprobe.d/vfio-pci-ids.conf`
2. **Uses driver override method** - Relies on systemd services that bind specific PCI addresses
3. **Shows informational warning** - Notifies that identical GPUs were detected and handled

This prevents the issue where all GPUs with the same PCI ID would be bound to VFIO when only specific ones should be passed through.

#### Example Scenarios

**Scenario 1: Different GPUs (RTX 3090 + RTX 4080)**
- Uses PCI ID method for efficiency
- Adds `options vfio-pci ids=10de:2204,10de:2684` to modprobe

**Scenario 2: Identical GPUs (Two RTX 3090s)**
- Detects duplicate PCI ID `10de:2204`
- Uses systemd service to bind only the assigned PCI slot (e.g., `01:00.0`)
- Leaves other identical GPU (e.g., `08:00.0`) for host use

**Scenario 3: Mixed cluster**
- bcn1: RTX 3090 + RTX 5090 → Uses PCI ID method
- bcn2: Two RTX 4090s → Uses address-based method
- Each host gets appropriate configuration

#### Real-World Example

In the bcn1 system:
- **01:00.0** - RTX 3090 (IOMMU group 12) - ✅ Eligible for passthrough
- **08:00.0** - RTX 3090 (IOMMU group 16 with other devices) - ❌ Not eligible
- **11:00.0** - AMD Raphael APU Graphics - Used for host display output

The installer correctly identifies that only 01:00.0 can be passed through, while 08:00.0 must remain with the host due to IOMMU group constraints.

#### Configuration

In your inventory, specify which GPUs to pass through:

```yaml
baremetal:
  hosts:
    bcn1:
      configure_gpu_passthrough: true
      assigned_pci_slots:
        - "01:00.0"  # Only this GPU will be passed through
```

#### 🤖 AI Enhancement Notes

The duplicate GPU detection logic was added to handle cases where multiple identical GPUs exist in a system. The playbook checks all system GPUs against assigned GPUs to detect when PCI IDs would match multiple devices, ensuring only the intended GPUs are bound for passthrough.

### Other Playbooks

- **10_setup_ssh_keys.yaml** - Configure SSH key-based authentication
- **20_setup_env.yaml** - Set up environment variables and shell configuration
- **40_setup_github_cli.yaml** - Install and configure GitHub CLI
- **38_test_gpu_reservation.yaml** - Verify GPU passthrough configuration
- **39_rollback_gpu_reservation.yaml** - Rollback GPU passthrough changes