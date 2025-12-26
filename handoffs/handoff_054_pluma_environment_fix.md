# Handoff #053: Pluma Local Environment Fix - Python Import Issues
**From Thread:** Sonnet Beta Testing Implementation  
**Date:** September 7, 2025, 09:45 UTC  
**Target:** Claude Code for systematic environment resolution  
**Duration:** 30-45 minutes estimated  

## Problem Statement

Pluma Local email drafting agent has persistent Python import failures despite packages being installed. Multiple attempts to install dependencies have failed due to macOS Python environment conflicts.

**Current Error:**
```
❌ dotenv failed: No module named 'dotenv'
```

**Environment Context:**
- macOS system with Python 3.9
- Packages install successfully but imports fail
- Multiple Python environments likely causing conflicts
- Gmail OAuth already working (credentials configured)
- Anthropic API key configured in .env file

## Root Cause Analysis

**Python Environment Issues:**
- Multiple Python installations (system/homebrew/user)
- Package installation scattered across different site-packages
- Import path conflicts between environments
- User vs system package installation conflicts

**Evidence:**
- `pip install` succeeds but `import` fails
- Packages show as "already satisfied" but not importable
- Force reinstall completes without errors
- Same pattern across multiple packages (dotenv, redis, etc.)

## Technical Requirements

### 1. Environment Diagnostics
- Identify all Python installations on system
- Map package installation locations
- Detect import path conflicts
- Verify which Python executable is being used

### 2. Clean Environment Setup
- Create isolated Python environment for Pluma Local
- Install all dependencies cleanly in single environment
- Ensure consistent Python/pip pairing
- Verify import resolution

### 3. Dependency Management
- Use virtual environment or ensure consistent user installation
- Install from requirements.txt with proper Python targeting
- Verify each critical import individually
- Create fallback import patterns where needed

### 4. Beta Testing Preparation
- Ensure all imports work correctly
- Verify Gmail OAuth integration functional
- Confirm Anthropic API connectivity
- Validate test interface launches successfully

## Implementation Plan

### Phase 1: Environment Diagnosis (10 minutes)
```bash
# Identify Python environments
which python3
python3 --version
python3 -m site --user-site
python3 -c "import sys; print(sys.path)"

# Check package locations
python3 -m pip show python-dotenv
python3 -m pip list | grep -E "(dotenv|anthropic|google)"

# Test imports systematically
python3 -c "import dotenv"
python3 -c "import anthropic" 
python3 -c "import google.auth"
```

### Phase 2: Clean Environment Setup (15 minutes)
**Option A: Virtual Environment (Recommended)**
```bash
# Create clean virtual environment
python3 -m venv pluma-env
source pluma-env/bin/activate
pip install --upgrade pip

# Install dependencies in clean environment
pip install -r requirements.txt

# Test imports in virtual environment
python -c "import dotenv; import anthropic; print('Success')"
```

**Option B: User Installation Fix**
```bash
# Clear conflicting installations
python3 -m pip uninstall -y python-dotenv anthropic google-auth google-auth-oauthlib google-api-python-client

# Clean install to user directory
python3 -m pip install --user --no-cache-dir python-dotenv anthropic google-auth google-auth-oauthlib google-api-python-client

# Verify installation paths
python3 -m pip show python-dotenv
```

### Phase 3: Pluma Integration (10 minutes)
```bash
# Test core imports
python3 quick_test.py

# Launch test interface
python3 test_interface.py

# Verify Gmail integration
# Expected: Menu with email fetch/draft options
```

### Phase 4: Beta Testing Validation (10 minutes)
```bash
# Run interactive test scenarios
python3 test_interface.py
# 1. Fetch recent emails
# 2. Generate draft reply
# 3. Test different email scenarios
# 4. Monitor performance metrics
```

## Success Criteria

### Environment Fixed ✅
- [ ] All Python imports work correctly
- [ ] No "ModuleNotFoundError" exceptions
- [ ] `python3 quick_test.py` shows all ✓ checkmarks
- [ ] Consistent package resolution

### Pluma Functional ✅  
- [ ] `test_interface.py` launches successfully
- [ ] Gmail OAuth connection verified
- [ ] Anthropic API responding to draft requests
- [ ] Email fetch and parse working

### Beta Testing Ready ✅
- [ ] Interactive menu functional
- [ ] Can fetch latest emails from Gmail
- [ ] Can generate draft replies with Claude
- [ ] Performance metrics available
- [ ] Ready for 5-scenario testing protocol

## Files and Locations

**Project Directory:** `~/Projects/demestihas-ai/pluma-local/`

**Key Files:**
- `requirements.txt` - Dependency specifications
- `pluma_local.py` - Main agent (already configured for optional Redis)
- `test_interface.py` - Interactive testing interface  
- `quick_test.py` - Environment validation script
- `.env` - API keys (Anthropic configured, valid)
- `credentials/` - Gmail OAuth (working, authenticated)

**Current Status:**
- Gmail OAuth: ✅ Working (menelaos4@gmail.com connected)
- API Configuration: ✅ Working (Anthropic key valid)
- Environment: ❌ Import failures preventing testing
- Testing Protocol: ⏳ Ready to execute once imports fixed

## Post-Fix Beta Testing Protocol

Once environment is fixed, execute **Phase 3: Interactive Testing**:

### Scenario 1: Simple Reply Draft
1. Fetch recent emails
2. Select email needing simple response
3. Generate draft reply
4. Evaluate tone, context, professionalism

### Scenario 2: Complex Email Draft  
1. Find email with multiple questions/topics
2. Generate draft addressing all points
3. Verify logical flow and completeness

### Scenario 3: Meeting Request Response
1. Locate meeting invitation email
2. Generate appropriate scheduling response
3. Check availability language

### Scenario 4: Performance Testing
1. Generate multiple drafts
2. Monitor response times (<3 seconds target)
3. Check cache behavior (if available)

### Scenario 5: Quality Assessment
Rate draft quality across:
- Tone matching: ⭐⭐⭐⭐⭐
- Context understanding: ⭐⭐⭐⭐⭐
- Professional language: ⭐⭐⭐⭐⭐
- Action item handling: ⭐⭐⭐⭐⭐

## Expected Outcome

**Environment Resolution:** Python imports working consistently across all dependencies

**Pluma Beta Testing:** Complete interactive testing of email drafting capabilities to validate it can replace Fyxer AI with 83% cost reduction

**Strategic Impact:** Successful local testing enables VPS deployment and integration with multi-agent family system

## Troubleshooting Fallbacks

If virtual environment approach fails:
1. Try conda environment: `conda create -n pluma python=3.9`
2. Use system Python with explicit paths
3. Docker container approach for complete isolation
4. Homebrew Python as alternative base

If specific imports still fail:
1. Install packages individually with verbose output
2. Check for conflicting package versions
3. Use `pip install --force-reinstall --no-deps`
4. Manual PYTHONPATH configuration

**Ready for Claude Code systematic environment resolution and beta testing execution.**