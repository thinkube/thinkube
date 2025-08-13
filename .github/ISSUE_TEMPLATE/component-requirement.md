---
name: Component Requirement
about: Define a requirement for deploying a Thinkube component
title: '[CORE-XXX] Deploy [Component Name]'
labels: requirement, milestone-2
assignees: ''

---

## Component Requirement

### Description
<!-- Brief description of what needs to be deployed/configured -->

### Component Details
- **Component Name**: 
- **Namespace**: 
- **Source**: <!-- thinkube-core migration or new -->
- **Priority**: <!-- high/medium/low -->
- **Directory**: <!-- ansible/40_core_services/core/[component]/ or optional/[component]/ -->

### Migration Checklist
- [ ] Update host groups (`gato-p` → `k8s-control-node`)
- [ ] Move hardcoded values to inventory variables
- [ ] Replace TLS secrets with Cert-Manager certificates
- [ ] Update module names to FQCN
- [ ] Verify variable compliance

### Acceptance Criteria
- [ ] Component deployed successfully
- [ ] All tests passing (18_test_[component].yaml)
- [ ] SSO integration working (if applicable)
- [ ] Resource limits configured
- [ ] Documentation updated
- [ ] Rollback playbook created (19_rollback_[component].yaml)

### Dependencies
**Required Services:**
- 

**Required Configurations:**
- 

### Hardcoded Values to Migrate
<!-- List found during analysis -->
- [ ] IP addresses: 
- [ ] Domain names: 
- [ ] Usernames: 
- [ ] Paths: 

### TLS Certificate Changes
- [ ] Current method: 
- [ ] Cert-Manager resource needed: 
- [ ] Domains required: 

### Implementation Tasks
1. [ ] Create component directory structure
2. [ ] Analyze source playbook for compliance
3. [ ] Create test playbook first (TDD)
4. [ ] Migrate/create deployment playbook
5. [ ] Update TLS to use Cert-Manager
6. [ ] Test deployment
7. [ ] Create rollback playbook
8. [ ] Update documentation
9. [ ] Create PR

### Verification Steps
```bash
# 1. Check for hardcoded values
grep -n "gato-p\|gato-w1" ansible/40_core_services/*/[component]/*.yaml
grep -n "192\.168\." ansible/40_core_services/*/[component]/*.yaml

# 2. Run test playbook
./scripts/run_ansible.sh ansible/40_core_services/*/[component]/18_test.yaml

# 3. Verify certificate
kubectl get certificate -n [namespace]
```

### Resource Requirements
- CPU: 
- Memory: 
- Storage: 

### Edit History
<!-- Track significant changes to this issue -->
- YYYY-MM-DD: Initial creation
- YYYY-MM-DD: [What changed]