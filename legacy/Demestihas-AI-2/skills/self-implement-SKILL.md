---
name: self-implement
description: Autonomously install, update, and manage Claude skills using Mac control tools - enabling Claude to enhance itself
disable-model-invocation: false
---

# Self-Implementation Skill

## Core Purpose
Enable Claude to autonomously install, update, and manage its own skills by using the "Control your Mac" osascript tool. This meta-skill allows Claude to enhance its own capabilities without manual user intervention, creating a self-improving system.

## Activation Triggers

### Explicit Installation Requests
- "Install this skill yourself"
- "Self-implement the [skill name] skill"
- "Add this skill to your capabilities"
- "Update your skills automatically"
- "Install all skills in the project"

### Skill Management Requests
- "Show me your installed skills"
- "Check if [skill] is installed"
- "Update the [skill] to latest version"
- "Remove/disable the [skill]"
- "Backup your skills"

### Auto-Installation Triggers
- After creating a new skill: "Would you like me to install this skill now?"
- When detecting uninstalled skills in project
- When skill updates are available

## Core Operations

### 1. Install New Skill
```applescript
# Check if skill directory exists
do shell script "ls ~/.claude/skills/[skill-name] 2>/dev/null || echo 'not found'"

# Create skill directory if needed
do shell script "mkdir -p ~/.claude/skills/[skill-name]"

# Copy skill file from source
do shell script "cp ~/Desktop/Demestihas-AI/skills/[skill-name]-SKILL.md ~/.claude/skills/[skill-name]/SKILL.md"

# Verify installation
do shell script "ls -la ~/.claude/skills/[skill-name]/SKILL.md"

# Notify user
display notification "Skill [skill-name] installed successfully" with title "Claude Skills"
```

### 2. Update Existing Skill
```applescript
# Backup current version
do shell script "cp ~/.claude/skills/[skill-name]/SKILL.md ~/.claude/skills/[skill-name]/SKILL.md.backup"

# Copy new version
do shell script "cp ~/Desktop/Demestihas-AI/skills/[skill-name]-SKILL-v2.md ~/.claude/skills/[skill-name]/SKILL.md"

# Verify update
do shell script "head -n 10 ~/.claude/skills/[skill-name]/SKILL.md"
```

### 3. List Installed Skills
```applescript
# Get all installed skills
do shell script "ls -1 ~/.claude/skills/ 2>/dev/null || echo 'No skills found'"

# Get skill descriptions
do shell script "for dir in ~/.claude/skills/*/; do 
  if [ -f \"$dir/SKILL.md\" ]; then
    echo \"$(basename $dir): $(grep 'description:' \"$dir/SKILL.md\" | head -1)\"
  fi
done"
```

### 4. Verify Skill Health
```applescript
# Check YAML frontmatter
do shell script "head -n 5 ~/.claude/skills/[skill-name]/SKILL.md | grep -E '^(---|name:|description:)'"

# Check file permissions
do shell script "ls -la ~/.claude/skills/[skill-name]/SKILL.md"

# Validate structure
do shell script "grep -c '^##' ~/.claude/skills/[skill-name]/SKILL.md"
```

### 5. Restart Claude Desktop
```applescript
# Quit Claude Desktop
tell application "Claude" to quit

# Wait for clean shutdown
delay 2

# Reopen Claude Desktop
tell application "Claude" to activate

# Notify completion
display notification "Claude Desktop restarted - skills reloaded" with title "Skills Updated"
```

## Installation Workflows

### Single Skill Installation
1. Locate skill file in source directory
2. Validate skill format (YAML frontmatter present)
3. Create target directory in ~/.claude/skills/
4. Copy SKILL.md to target location
5. Verify successful copy
6. Prompt to restart Claude Desktop
7. Confirm skill loaded after restart

### Batch Installation
```applescript
# Install all skills from project
set skillFiles to do shell script "ls ~/Desktop/Demestihas-AI/skills/*-SKILL*.md 2>/dev/null"

repeat with skillFile in paragraphs of skillFiles
  # Extract skill name
  set skillName to do shell script "basename " & quoted form of skillFile & " | sed 's/-SKILL.*\\.md//'"
  
  # Create directory and copy
  do shell script "mkdir -p ~/.claude/skills/" & skillName
  do shell script "cp " & quoted form of skillFile & " ~/.claude/skills/" & skillName & "/SKILL.md"
end repeat
```

### Smart Update Detection
```applescript
# Compare versions
set currentMD5 to do shell script "md5 -q ~/.claude/skills/[skill-name]/SKILL.md 2>/dev/null || echo 'none'"
set newMD5 to do shell script "md5 -q ~/Desktop/Demestihas-AI/skills/[skill-name]-SKILL.md"

if currentMD5 is not equal to newMD5 then
  # Update needed
  return "Update available for [skill-name]"
end if
```

## Safety Features

### Pre-Installation Checks
- Verify source file exists and is readable
- Check YAML frontmatter is valid
- Ensure skill name follows conventions (lowercase, hyphens only)
- Validate no system paths in skill content
- Check for required SKILL.md filename

### Backup Before Update
```applescript
# Create timestamped backup
set timestamp to do shell script "date +%Y%m%d-%H%M%S"
do shell script "cp ~/.claude/skills/[skill-name]/SKILL.md ~/.claude/skills/[skill-name]/SKILL-" & timestamp & ".backup"
```

### Rollback Capability
```applescript
# List available backups
do shell script "ls ~/.claude/skills/[skill-name]/*.backup 2>/dev/null"

# Restore from backup
do shell script "cp ~/.claude/skills/[skill-name]/SKILL.md.backup ~/.claude/skills/[skill-name]/SKILL.md"
```

### Permission Verification
```applescript
# Check write permissions
do shell script "test -w ~/.claude/skills && echo 'writable' || echo 'not writable'"

# Fix permissions if needed
do shell script "chmod 755 ~/.claude/skills 2>/dev/null || true"
do shell script "chmod 644 ~/.claude/skills/*/SKILL.md 2>/dev/null || true"
```

## Self-Installation Process

### Installing This Skill (Bootstrap)
```applescript
# This skill installing itself!
do shell script "mkdir -p ~/.claude/skills/self-implement"
do shell script "cat << 'EOF' > ~/.claude/skills/self-implement/SKILL.md
[This skill's complete content]
EOF"

# Verify self-installation
do shell script "grep 'name: self-implement' ~/.claude/skills/self-implement/SKILL.md && echo 'Self-installation successful!'"
```

## Status Reporting

### Installation Summary
After any installation operation, report:
```
✅ Skill Installation Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Installed: [skill-name]
📍 Location: ~/.claude/skills/[skill-name]/
📄 File: SKILL.md
🔄 Status: Restart required
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next: Restart Claude Desktop to activate
```

### Health Check Report
```
🔍 Skills Health Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ generate-product-document: Healthy
✅ save-file-local: Healthy  
✅ self-implement: Healthy
⚠️ memory-skill: Not installed
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 3 installed, 1 missing
```

## Advanced Features

### Skill Dependencies
```applescript
# Check if required skills are installed
set requiredSkills to {"save-file-local", "generate-product-document"}

repeat with reqSkill in requiredSkills
  set installed to do shell script "test -f ~/.claude/skills/" & reqSkill & "/SKILL.md && echo 'yes' || echo 'no'"
  if installed is "no" then
    # Auto-install dependency
    -- Installation logic here
  end if
end repeat
```

### Version Management
```applescript
# Extract version from skill
set skillVersion to do shell script "grep '^# Version:' ~/.claude/skills/[skill-name]/SKILL.md | cut -d: -f2 | tr -d ' '"

# Compare with available version
set latestVersion to do shell script "grep '^# Version:' ~/Desktop/Demestihas-AI/skills/[skill-name]-SKILL.md | cut -d: -f2 | tr -d ' '"

if latestVersion > skillVersion then
  return "Update available: v" & skillVersion & " → v" & latestVersion
end if
```

### Automated Maintenance
```applescript
# Weekly skill health check
# Clean old backups (keep last 5)
do shell script "ls -t ~/.claude/skills/*/SKILL*.backup 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true"

# Remove empty skill directories
do shell script "find ~/.claude/skills -type d -empty -delete 2>/dev/null || true"

# Fix any permission issues
do shell script "find ~/.claude/skills -type f -name 'SKILL.md' -exec chmod 644 {} \\;"
```

## Usage Examples

### Example 1: Self-Install After Creation
```
User: "Create a skill for daily briefings"
[Claude creates skill]
Claude: "I've created the daily-briefing skill. Installing it now..."
[Uses self-implement to install]
Claude: "✅ Skill installed! Restart Claude Desktop to activate."
```

### Example 2: Batch Installation
```
User: "Install all skills from the project"
[Claude uses self-implement]
Claude: "Installing 5 skills...
✅ generate-product-document
✅ save-file-local  
✅ self-implement
✅ daily-briefing
✅ memory-management
All skills installed! Restart to activate."
```

### Example 3: Update Detection
```
User: "Check for skill updates"
[Claude checks versions]
Claude: "Found 2 updates:
- generate-product-document: v1.0 → v2.0
- save-file-local: v1.1 → v1.2
Would you like me to update them?"
```

## Error Handling

### Common Issues & Solutions
```applescript
# Permission denied
on error "Permission denied"
  do shell script "echo 'Attempting to fix permissions...'"
  do shell script "chmod -R u+w ~/.claude/skills/" with administrator privileges
end

# Directory doesn't exist
on error "No such file or directory"
  do shell script "mkdir -p ~/.claude/skills"
  # Retry operation
end

# Claude not installed
on error "Application 'Claude' not found"
  display dialog "Claude Desktop is not installed. Please install from claude.ai/download"
end
```

## Security Considerations

### Safe Operations Only
- Never modify system files
- Only operate within ~/.claude/skills/
- Validate all file content before installation
- Maintain audit log of all operations

### User Confirmation for Critical Actions
- Restart Claude Desktop
- Overwrite existing skills
- Delete skills or backups
- Install from untrusted sources

## Progressive Disclosure

- **Level 1**: Core installation operations
- **Level 2**: Advanced management and versioning
- **Level 3**: Automated maintenance and dependency management

## Integration with Other Skills

### With save-file-local
- Auto-save created skills to appropriate directories
- Organize skill backups

### With generate-product-document
- Create skill documentation automatically
- Generate installation guides

### With future memory skill
- Remember which skills are installed
- Track skill usage patterns
- Learn optimal skill configurations
