#!/bin/bash
# Archive organization script

echo "Starting file organization..."

# Move documentation files
mv ~/Projects/demestihas-ai/*INSTRUCTIONS*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/*STATUS*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/*HANDOFF*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/*UPDATE*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/*REPORT*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/*GUIDE*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/*DEPLOYMENT*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/*IMPLEMENTATION*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/thread_*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/deployment_*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/handoff_*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/README*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/architecture.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/bootstrap.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/cache.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/current_state.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/execution-log.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/family.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/family_context.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/gmail_setup_guide.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/monitoring.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/quickstart.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/routing.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/state.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/templates.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/thread_log.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/BETA_*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/CRITICAL_*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/ENHANCEMENT_*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/PROJECT_MAP.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/FULL_STACK_AI_ROLE.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null

# Move book files
mv ~/Projects/demestihas-ai/BOOK_*.md ~/Projects/demestihas-ai/book/ 2>/dev/null
mv ~/Projects/demestihas-ai/CHAPTER_*.md ~/Projects/demestihas-ai/book/ 2>/dev/null
mv ~/Projects/demestihas-ai/VISION_BOOK.md ~/Projects/demestihas-ai/book/ 2>/dev/null
mv ~/Projects/demestihas-ai/DEVELOPMENT_JOURNEY.md ~/Projects/demestihas-ai/book/ 2>/dev/null

# Move scripts
mv ~/Projects/demestihas-ai/fix_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/fix_*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/test_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/test_*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/test-*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/check_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/diagnose*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/diagnose*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/verify_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/activate_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/add_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/audit_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/complete_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/compress_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/download_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/emergency_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/health_check_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/initialize.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/integrate_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/make_executable.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/monitor-*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/process_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/quick_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/restart-*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/setup-*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/show_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/start-*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/stress-*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/transcribe_*.sh ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/batch_*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/process_*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/quick_*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/simple_*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/status.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null

# Move deployment files
mv ~/Projects/demestihas-ai/deploy_*.sh ~/Projects/demestihas-ai/archive/deployments/ 2>/dev/null
mv ~/Projects/demestihas-ai/VPS_*.md ~/Projects/demestihas-ai/archive/deployments/ 2>/dev/null

# Move legacy/duplicates
mv ~/Projects/demestihas-ai/Dockerfile.* ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/docker-compose-*.yml ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/"docker-compose copy.yml" ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/requirements-*.txt ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/"requirements copy.txt" ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/"IMPLEMENTATION_STATUS copy.md" ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/mcp-server-*.js ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/env-*.txt ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/.env.example ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null

# Move audio/hermes related files
mv ~/Projects/demestihas-ai/*audio*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/*AUDIO*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/*hermes*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/*HERMES*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/hermes_*.yml ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null

# Move integration/patch files
mv ~/Projects/demestihas-ai/*_patch.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/*_integration.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/*_integrator.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/*_enhancement.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null

# Move calendar/pluma/yanay specific files
mv ~/Projects/demestihas-ai/calendar_*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/pluma*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/yanay_*.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/*YANAY*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/*PLUMA*.md ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null

# Move miscellaneous files
mv ~/Projects/demestihas-ai/bot_minimal.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/conversation_manager.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/gdrive_processor.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/google_drive_audio_processor.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/huata.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/token_manager.py ~/Projects/demestihas-ai/archive/scripts/ 2>/dev/null
mv ~/Projects/demestihas-ai/execution.log ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/audio_processor.log ~/Projects/demestihas-ai/archive/legacy/ 2>/dev/null
mv ~/Projects/demestihas-ai/"MEMORY COMMANDS REFERENCE CARD" ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/0-MD2-DIRECTORY ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null
mv ~/Projects/demestihas-ai/PM-DEV_INSTRUCTIONS_v2 ~/Projects/demestihas-ai/archive/documentation/ 2>/dev/null

# Keep EMERGENCY_RECOVERY.md and EA_AI_QUICK_REFERENCE.md in root
# Keep smart-memory.md in root
# Keep main docker-compose.yml, Dockerfile, requirements.txt, bootstrap.js in root
# Keep .env in root
# Keep deploy.sh in root

echo "File organization complete!"
echo "Checking what remains in root..."
ls -la ~/Projects/demestihas-ai/ | grep -v "^d" | wc -l
echo "files remain in root directory"