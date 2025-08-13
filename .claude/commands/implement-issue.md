# Implement GitHub Issue #$ARGUMENTS

Please implement issue #$ARGUMENTS from the thinkube repository following this strict process:

## Project Structure Reference

Common paths and files you'll need:
- **Inventory**: `/home/thinkube/thinkube/inventory/inventory.yaml`
- **Group variables**: `/home/thinkube/thinkube/inventory/group_vars/`
- **Host variables**: `/home/thinkube/thinkube/inventory/host_vars/`
- **Reference playbooks**: `/home/thinkube/thinkube/thinkube-core/playbooks/`
- **40_thinkube directory**: `/home/thinkube/thinkube/ansible/40_thinkube/`
- **Architecture docs**: `/home/thinkube/thinkube/docs/architecture-k8s/`
- **CLAUDE.md**: `/home/thinkube/thinkube/CLAUDE.md` (project conventions)
- **Thinkube-core CLAUDE.md**: `/home/thinkube/thinkube/thinkube-core/CLAUDE.md` (reference conventions)

Common variables to check in inventory:
- `domain_name`, `k8s_domain`, `registry_domain`
- `system_username`, `admin_username` 
- `lan_ip`, `zerotier_ip`
- `ssl_cert_dir`, `tls_crt_path`, `tls_key_path`
- `vault_cf_token` (for Cloudflare)
- `kubectl_bin`, `helm_bin`, `kubeconfig`

**CRITICAL: Username and Password Guidelines**
- Application admin credentials: ALWAYS use `admin_username` and `admin_password`
  - This applies to ALL application components (Harbor, Keycloak, PostgreSQL, etc.)
  - When migrating, MUST replace component-specific admin users (e.g., `HARBOR_ADMIN_USER`) with `admin_username`
  - Environment variables: Use `ADMIN_PASSWORD` for admin passwords
- SSO/realm users: Use `auth_realm_username` and `auth_realm_password`
  - For end users authenticated via SSO/realm
  - Environment variables: Use `AUTH_REALM_PASSWORD` for realm passwords
- System users: Use `system_username`
  - For OS-level users and service accounts
- NEVER use component-specific variants (e.g., NO `keycloak_admin_username`, NO `harbor_admin_user`)
- NEVER keep hardcoded usernames like `admin`, `admin`, or custom usernames in playbooks
- Default values:
  - `admin_username`: `tkadmin` (MUST be used for ALL application admin access)
  - `auth_realm_username`: `thinkube` (SSO user)
  - `system_username`: `thinkube` (OS user)

## Implementation Process Checklist

1. **Issue Analysis**
   - [ ] Read the GitHub issue #$ARGUMENTS completely
   - [ ] Extract the exact reference implementation path/URL from the issue
   - [ ] List all stated requirements (NOT inferred requirements)
   - [ ] Identify which category this belongs to (core/optional)

2. **Migration Source Analysis** (CRITICAL for migrations)
   - [ ] Locate the exact source playbook in thinkube-core: `/home/thinkube/thinkube/thinkube-core/`
   - [ ] Create a checklist of EVERY feature in the original playbook
   - [ ] Identify all hardcoded values that must become variables:
     - Domain names (e.g., `example.com` → `{{ domain_name }}`)
     - IP addresses (e.g., `10.0.191.100` → `{{ primary_ingress_ip }}`)
     - SSO/realm usernames (e.g., `admin` → `{{ auth_realm_username }}`)
     - Application admin usernames → `{{ admin_username }}` (for ALL applications)
     - Component-specific admin users (`HARBOR_ADMIN_USER`, `admin`, etc.) → `{{ admin_username }}`
     - Application admin passwords → `{{ admin_password }}`
     - System usernames → `{{ system_username }}`
     - Paths and directories
   - [ ] List all Kubernetes resources being created (Secrets, ConfigMaps, Services, etc.)
   - [ ] Note any non-standard configurations or workarounds

3. **Environment Preparation**
   - [ ] Create component directory: `/home/thinkube/thinkube/ansible/40_thinkube/[category]/[component]/`
   - [ ] Check inventory for required variables
   - [ ] Note any missing environment variables (like CLOUDFLARE_TOKEN)
   - [ ] Verify dependencies are met (check issue dependencies section)

4. **Migration Implementation**
   - [ ] Start with the EXACT structure from thinkube-core
   - [ ] Make ONLY these required changes:
     - Replace hardcoded values with inventory variables
     - Update host groups (`gato-p` → `k8s-control-node`)
     - Change module names to FQCN
     - Fix authentication/authorization to use standard variables
   - [ ] DO NOT change:
     - Service configurations
     - Port mappings
     - Resource names
     - Logic flow
   - [ ] Create playbooks in this order:
     1. `19_rollback_[component].yaml` (cleanup)
     2. `10_deploy_[component].yaml` (main deployment)
     3. `15_configure_[component].yaml` (if needed for post-deploy config)
     4. `18_test_[component].yaml` (validation)

5. **Testing**
   - [ ] Test the implementation as specified
   - [ ] Fix any issues while maintaining reference compliance
   - [ ] Verify all tests pass
   - [ ] Check resource limits are configured
   - [ ] Follow correct playbook execution order:
     1. Run `19_rollback_[component].yaml` (if cleaning up)
     2. Run `10_deploy_[component].yaml` (main deployment)
     3. Run `15_configure_[component].yaml` (if exists - post-deployment config)
     4. Run `18_test_[component].yaml` (verify deployment)

6. **Documentation**
   - [ ] Update component README.md
   - [ ] Document any new variables needed
   - [ ] Note if environment variables are required
   - [ ] Update PR #37 if on infrastructure branch

## Certificate and Secret Handling

For TLS certificates:
- If original uses manual cert copying → Keep the same approach
- If original creates Certificate resources → Migrate to Cert-Manager
- Wildcard certs are copied from default namespace as: `thinkube-com-tls`
- Use the same certificate names/domains as the original

For authentication:
- Replace component-specific auth with standard variables
- Keycloak integration uses `auth_realm_username` for SSO users
- Basic auth uses `admin_username` and `admin_password`

## IMPORTANT RULES
- Always explicitly state: "Checking reference from [URL]" or "Checking reference from [FILE]"
- Always list: "Reference includes: [features]" and "Reference excludes: [features]" 
- Never add functionality not in the reference without explicit discussion
- If you think something is missing, ask: "Reference doesn't include X, should I add it?"
- Check both project CLAUDE.md files for conventions
- Maintain consistency with existing variable naming in inventory
- PRESERVE all functionality from the original - only change what's required for compliance

Begin by fetching and analyzing issue #$ARGUMENTS.