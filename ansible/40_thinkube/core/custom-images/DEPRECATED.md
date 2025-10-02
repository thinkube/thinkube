# DEPRECATED: Custom Images Directory

**⚠️ This directory is deprecated as of September 28, 2025**

## Migration Notice

The image building functionality has been consolidated into the Harbor directory structure for better organization and faster iteration:

### Old Location (Deprecated)
```
ansible/40_thinkube/core/custom-images/
└── 10_build_jupyter_images.yaml
```

### New Location (Active)
```
ansible/40_thinkube/core/harbor/
├── 14_build_base_images.yaml        # Foundation images
├── 15_build_jupyter_images.yaml     # Jupyter notebook images
└── 16_build_codeserver_image.yaml   # code-server development image
```

## Benefits of New Structure

1. **Faster Iteration**: Separate playbooks mean you only rebuild what changed
2. **Logical Grouping**: All image building in one place (harbor/)
3. **Consistency**: Uses same patterns as base image building
4. **Better Performance**: Independent playbooks enable parallel execution

## Migration Guide

### If you were using:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/custom-images/10_build_jupyter_images.yaml
```

### Now use:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/harbor/15_build_jupyter_images.yaml
```

## Timeline

- **Now**: Both locations work (old redirects to new)
- **Phase 4.5**: Old location will be removed
- **Recommendation**: Update your workflows immediately

## Questions?

See `/home/thinkube/thinkube/ansible/40_thinkube/core/harbor/README.md` for documentation on the new structure.
