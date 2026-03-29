# Upgrade project dependencies

1. **Switch to upgrade branch**: `git checkout feat/upg-dependencies`
2. **Verify current branch**: `git branch --show-current` (should show `feat/upg-dependencies`)
3. **Reset to main**: `git reset --hard main` (this ensures a clean start from main)
4. **Check for outdated dependencies**: `pnpm outdated -r` to see current vs available versions
5. **Research significant updates**: For packages with major/minor version changes, research changelogs for new features and breaking changes that could affect your specific codebase
6. **Update dependencies**: `pnpm up -r -L` (recursive update with latest versions)
7. **Run full test suite**: `bin/run-all-tasks.sh`
   - **CRITICAL**: If any tests fail or errors occur, **STOP IMMEDIATELY** and fix issues before proceeding
8. **Commit and create PR**:
   ```bash
   git add .
   git commit -m "chore: upgrade all dependencies"
   git push -u origin feat/upg-dependencies
   # Create PR through your preferred method (gh cli, web interface, etc.)
   # Include changelog highlights for significant updates in PR description
   ```
