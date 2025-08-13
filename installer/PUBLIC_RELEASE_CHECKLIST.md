# Public Release Checklist for Thinkube

This checklist must be completed before making the thinkube repository public.

## Legal Requirements
- [ ] Add copyright headers to all source files using COPYRIGHT_HEADER.md format
  - [ ] Python files (~450 files)
  - [ ] YAML playbooks (~213 files)
  - [ ] JavaScript/TypeScript files
  - [ ] Shell scripts
  - [ ] Dockerfiles
- [ ] Verify LICENSE file exists at repository root (Apache 2.0)
- [ ] Verify NOTICE file exists with third-party attributions
- [ ] Update COPYRIGHT_HEADER.md if needed

## Security Audit
- [ ] Remove all hardcoded credentials
  - [ ] Check for passwords in YAML files
  - [ ] Check for API tokens in code
  - [ ] Check for SSH keys in repository
- [ ] Replace sensitive domains
  - [ ] Replace example.com with example.com or variables
  - [ ] Remove references to private infrastructure
- [ ] Clean sensitive data from git history
  - [ ] Use BFG Repo-Cleaner or git-filter-branch if needed
  - [ ] Verify with `git log --all --full-history --grep="password"`
- [ ] Review configuration files
  - [ ] inventory/group_vars/all.yml
  - [ ] All files in inventory/
  - [ ] .env files (should be in .gitignore)
- [ ] Audit private IP addresses
  - [ ] Remove or parameterize private IPs
  - [ ] Use example ranges (192.0.2.0/24, 198.51.100.0/24)

## Documentation Updates
- [ ] Update README.md
  - [ ] Remove references to private repository
  - [ ] Add public installation instructions
  - [ ] Add badges (license, version, etc.)
- [ ] Create CONTRIBUTING.md
  - [ ] Contribution guidelines
  - [ ] Development setup
  - [ ] Pull request process
- [ ] Create CODE_OF_CONDUCT.md
  - [ ] Use standard template (Contributor Covenant)
- [ ] Create SECURITY.md
  - [ ] Vulnerability reporting process
  - [ ] Security contact information
- [ ] Update installer/README.md
  - [ ] Public download URLs
  - [ ] Installation from releases

## Repository Configuration
- [ ] GitHub repository settings
  - [ ] Transfer to public organization OR
  - [ ] Change visibility to public
  - [ ] Enable Issues
  - [ ] Enable Discussions
  - [ ] Enable Wiki (optional)
- [ ] Create issue templates
  - [ ] Bug report
  - [ ] Feature request
  - [ ] Documentation improvement
- [ ] Configure branch protection
  - [ ] Protect main branch
  - [ ] Require PR reviews
- [ ] Set up GitHub Actions
  - [ ] CI/CD for testing
  - [ ] Automated builds for releases
  - [ ] License header checks

## Code Cleanup
- [ ] Remove development/debug code
  - [ ] Console.log statements
  - [ ] Debug print statements
  - [ ] Temporary test code
- [ ] Update import statements
  - [ ] Change from private to public GitHub URLs
- [ ] Review comments
  - [ ] Remove internal/private references
  - [ ] Clean up TODO comments
- [ ] Update package.json/requirements.txt
  - [ ] Ensure all dependencies are public
  - [ ] Update repository URLs

## Release Preparation
- [ ] Create release branch
- [ ] Version tagging strategy
  - [ ] Semantic versioning (v1.0.0)
  - [ ] Tag current state before changes
- [ ] Build release artifacts
  - [ ] Debian packages (amd64, arm64)
  - [ ] SHA256 checksums
- [ ] Prepare release notes
  - [ ] Features list
  - [ ] Known issues
  - [ ] Installation instructions

## Final Verification
- [ ] Fresh clone test
  - [ ] Clone repository
  - [ ] Follow installation instructions
  - [ ] Verify everything works
- [ ] Security scan
  - [ ] Run git-secrets or similar
  - [ ] Check for exposed credentials
- [ ] License compliance
  - [ ] All files have headers
  - [ ] Third-party licenses documented
- [ ] Documentation review
  - [ ] All links work
  - [ ] Instructions are clear
  - [ ] Examples use public URLs

## Post-Release Tasks
- [ ] Monitor initial issues
- [ ] Respond to community questions
- [ ] Set up community channels
  - [ ] Discord/Slack (optional)
  - [ ] Mailing list (optional)
- [ ] Create project website (optional)
- [ ] Submit to package repositories
  - [ ] Homebrew (future)
  - [ ] APT repository (future)

## Notes
- This checklist should be reviewed by multiple team members
- Each item should be verified independently
- Keep a backup of the private repository before making public
- Consider a soft launch with limited announcement first

---
*Last updated: January 2025*