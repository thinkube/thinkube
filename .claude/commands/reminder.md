# Context Reminder & Guidelines

This command re-establishes project context and guidelines after conversation compacting or multiple iterations.

## Project Context

You are working on the **Thinkube Project** - a home-based Kubernetes platform built for AI applications and agents.

## Current Location & Important Files

- **Working Directory**: `/home/thinkube/thinkube`
- **Inventory**: `/home/thinkube/thinkube/inventory/inventory.yaml`
- **Group Variables**: `/home/thinkube/thinkube/inventory/group_vars/`
- **CLAUDE.md**: `/home/thinkube/thinkube/CLAUDE.md` (master documentation)
- **START_HERE.md**: `/home/thinkube/thinkube/START_HERE.md` (task tracking)
- **Architecture Docs**: `/home/thinkube/thinkube/docs/architecture-k8s/`

## Critical Guidelines

### Variable Management
- Installation-specific variables MUST be in inventory, NEVER in playbooks
- Use snake_case for all variable names
- **Application Admin**: ALWAYS use `admin_username` and `admin_password`
  - MUST be used for ALL applications (Harbor, Keycloak, PostgreSQL, etc.)
  - When migrating, MUST replace component-specific admin users with `admin_username`
  - NEVER use component-specific variants like `harbor_admin_user` or `keycloak_admin_user`
- **SSO/Realm Users**: Use `auth_realm_username` and `auth_realm_password`
  - For end users authenticated via SSO/realm
- **System Users**: Use `system_username`
  - For OS-level users and service accounts
- **Environment Variables**:
  - Use `ADMIN_PASSWORD` for admin passwords, never component-specific like `HARBOR_ADMIN_PASS`
  - Use `AUTH_REALM_PASSWORD` for realm passwords
- **Default Values**:
  - `admin_username`: `tkadmin` (MUST be used for ALL application admin access)
  - `auth_realm_username`: `thinkube` (SSO user)
  - `system_username`: `thinkube` (OS user)

### Playbook Structure
- Follow numbering convention: 10-17 (setup), 18 (test), 19 (rollback)
- Use FQCN for modules (ansible.builtin.*, kubernetes.core.*)
- Never use `become: true` at playbook level
- Always verify required variables before proceeding

### Testing & Deployment Order
1. Run `19_rollback_[component].yaml` (if cleaning up)
2. Run `10_deploy_[component].yaml` (main deployment)
3. Run `15_configure_[component].yaml` (if exists)
4. Run `18_test_[component].yaml` (verification)

### Migration Rules (from thinkube-core)
- Preserve ALL original functionality
- Make ONLY minimum changes for compliance
- Replace hardcoded values with inventory variables:
  - `example.com` → `{{ domain_name }}`
  - `10.0.191.100` → `{{ primary_ingress_ip }}`
  - `admin` → `{{ auth_realm_username }}` (SSO user)
  - Application admin usernames → `{{ admin_username }}` (used for ALL applications)
  - Component-specific admin users (`HARBOR_ADMIN_USER`, `admin`, etc.) → `{{ admin_username }}`
  - Application admin passwords → `{{ admin_password }}`
- Update host groups: `gato-p` → `k8s-control-node`
- Change module names to FQCN
- If uncertain about a change, preserve the original approach

### Certificate & Secret Handling
- If original uses manual cert copying → Keep the same approach
- If original creates Certificate resources → Migrate to Cert-Manager
- Wildcard certs are copied from default namespace as: `thinkube-com-tls`
- Use the same certificate names/domains as the original

### AI-Assisted Work
- Mark all AI-generated content with 🤖 emoji
- Document in AI_CONTRIBUTIONS.md
- Add `[AI-assisted]` to commit messages

## Current Session Status

Please review the conversation history above to understand:
- What component/issue we're working on
- What stage of implementation we're at
- Any specific problems we're troubleshooting

**Continue with the current task...**