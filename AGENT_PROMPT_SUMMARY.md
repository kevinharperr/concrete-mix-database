# Quick LLM Agent Prompt

**Repository:** https://github.com/kevinharperr/concrete-mix-database/tree/database-refresh

**Objective:** Perform spring cleaning analysis on Django project to identify unused files, duplicate code, and optimization opportunities.

**CRITICAL - NEVER REMOVE:**
- `concrete_mix_project/` directory (Essential Django config)
- `cdb_app/` directory (Main Django app)
- `refresh_status/` directory (Notification system)
- `templates/` and `static/` directories (Essential assets)
- `manage.py` (Django management)

**PRIMARY FOCUS for Cleanup:**
- 50+ root-level Python scripts (accumulated during development)
- Look for patterns: `import_*.py`, `validate_*.py`, `check_*.py`, `test_*.py`, `fix_*.py`, `cleanup_*.py`
- ETL directory may have old configuration files
- Documentation files for consistency

**Context:**
- Production-ready Django app with 1,764 concrete mixes
- Recent major changes: app consolidation, security hardening, successful DS1+DS2 imports
- Universal import system was removed (may have leftover files)

**Expected Output:**
1. List of safe-to-remove files with justification
2. Duplicate functionality identification  
3. Code quality improvements
4. Documentation cleanup suggestions
5. Risk level for each recommendation (low/medium/high)

**Safety:** Be conservative - prioritize obvious cleanup over aggressive refactoring. This is an active production project.

For full detailed prompt, see: `LLM_AGENT_ANALYSIS_PROMPT.md` in the repository. 