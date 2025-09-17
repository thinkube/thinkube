# Custom Images Module

This module handles building and managing custom Docker images for Thinkube, completely separated from service deployments for optimal development workflow.

## Architecture

### Separation of Concerns

```
┌─────────────────────────────────────────────────────┐
│                 custom-images module                  │
│  - Builds Docker images (20+ minutes)                │
│  - Pushes to Harbor registry                         │
│  - Updates thinkube-control database                 │
│  - Independent of service deployments                │
└─────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│                  Harbor Registry                     │
│  - Stores all custom images                         │
│  - Provides versioning and tagging                  │
│  - Serves images to all services                    │
└─────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│           Service Deployments (2 minutes)           │
│  - JupyterHub                                       │
│  - Other services                                   │
│  - Pull images from Harbor                          │
│  - No building during deployment                    │
└─────────────────────────────────────────────────────┘
```

## Benefits

1. **Fast Iteration**: Service deployments complete in 2 minutes
2. **Parallel Development**: Images can be built separately
3. **Version Control**: Pinned versions in requirements.txt files
4. **Reproducibility**: Same images across all installations
5. **Dynamic Discovery**: Services query thinkube-control for available images

## Jupyter Images

### Available Images

| Image Name | Description | GPU Required | Default Resources |
|------------|-------------|--------------|-------------------|
| jupyter-ml-cpu | ML Development (CPU) | No | 4 CPU, 8GB RAM |
| jupyter-ml-gpu | Deep Learning (GPU) | Yes | 8 CPU, 16GB RAM |
| jupyter-agent-dev | Agent Development | No | 4 CPU, 8GB RAM |
| jupyter-fine-tuning | Fine-tuning (Unsloth) | Yes | 8 CPU, 32GB RAM |

### Building Images

```bash
# Build all Jupyter images (takes 20+ minutes)
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/custom-images/10_build_jupyter_images.yaml
```

### Image Structure

```
images/
├── jupyter-ml-cpu/
│   ├── Dockerfile
│   └── requirements.txt    # Pinned versions
├── jupyter-ml-gpu/
│   ├── Dockerfile
│   └── requirements.txt
├── jupyter-agent-dev/
│   ├── Dockerfile
│   └── requirements.txt
└── jupyter-fine-tuning/
    ├── Dockerfile
    └── requirements.txt
```

## Version Management

All package versions are pinned in `requirements.txt` files to ensure reproducibility:

- **Python 3.12**: Base Python version (Ubuntu 24.04)
- **CUDA 12.6**: GPU runtime version
- **PyTorch 2.4.1**: Deep learning framework
- **JupyterLab 4.2.5**: Notebook interface

## Integration with thinkube-control

After building, images are registered with thinkube-control:

```python
# Metadata sent to thinkube-control API
{
    "name": "jupyter-ml-gpu",
    "display_name": "Deep Learning (GPU)",
    "description": "JupyterLab with PyTorch and GPU support",
    "category": "jupyter",
    "tags": ["jupyter-compatible"],
    "metadata": {
        "gpu_required": true,
        "cpu_limit": 8,
        "mem_limit": "16G"
    }
}
```

## Adding New Images

1. Create directory: `images/new-image-name/`
2. Add `Dockerfile` with ARG HARBOR_REGISTRY
3. Add `requirements.txt` with pinned versions
4. Update `10_build_jupyter_images.yaml` with build steps
5. Add metadata for thinkube-control integration

## Best Practices

1. **Always pin versions** in requirements.txt
2. **Use ARG** for registry, not Jinja templates
3. **Build sequentially** to avoid WebSocket issues
4. **Test locally** before pushing to Harbor
5. **Update thinkube-control** after successful builds

## Troubleshooting

### Build Failures

- Check Harbor accessibility
- Verify base image exists in Harbor
- Review package version conflicts
- Check disk space for build cache

### Push Failures

- Verify Harbor credentials
- Check network connectivity
- Ensure image size < Harbor limits

### API Update Failures

- thinkube-control may not have endpoint yet
- Check API is accessible on port 30080
- Verify metadata format matches API schema

## Future Enhancements

- [ ] Add CI/CD for automatic builds
- [ ] Implement version tagging strategy
- [ ] Add vulnerability scanning
- [ ] Create build cache optimization
- [ ] Add multi-architecture support

🤖 AI-assisted