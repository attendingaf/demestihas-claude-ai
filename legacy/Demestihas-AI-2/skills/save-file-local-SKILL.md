---
name: save-file-local
description: Intelligently save generated content to organized local folders with auto-versioning and pattern learning
disable-model-invocation: false
---

# Save File to Local Workspace

## Core Purpose
Automatically organize and save AI-generated content to appropriate local directories, learning from context to determine the best location without interrupting workflow.

## Intelligent Workspace Mapping

### Learning Patterns
The skill learns where to save files based on content type and context:

```
~/Desktop/Demestihas-AI/
├── projects/                 # PRDs, implementation plans, project docs
│   ├── [project-name]/
│   │   ├── docs/
│   │   ├── specs/
│   │   └── plans/
├── code/                    # Scripts, configs, source files
│   ├── python/
│   ├── javascript/
│   └── configs/
├── documents/               # General documents
│   ├── api-specs/
│   ├── user-stories/
│   └── qa-plans/
├── skills/                  # Claude skills
├── daily/                   # Daily briefs, notes, summaries
│   └── 2024-11-11/
└── exports/                 # Quick exports, temporary files
```

### Content Type Detection
Based on document content and filename, automatically determine location:

| Content Pattern | Default Location | Example |
|----------------|------------------|---------|
| PRD, Implementation Plan | `projects/[name]/docs/` | `projects/demestihas-ai/docs/prd-v1.md` |
| API Specification | `projects/[name]/specs/` or `documents/api-specs/` | `specs/auth-api-20241111-1430.md` |
| User Stories | `projects/[name]/docs/` or `documents/user-stories/` | `user-stories-cart-feature.md` |
| Python/JS Code | `code/[language]/` | `code/python/memory-manager.py` |
| Claude Skills | `skills/[skill-name]/` | `skills/memory-skill/SKILL.md` |
| README files | `projects/[name]/` (root) | `projects/password-manager/README.md` |
| Daily Briefs | `daily/YYYY-MM-DD/` | `daily/2024-11-11/morning-brief.md` |
| Quick Notes | `exports/` | `exports/quick-note-20241111.md` |

## Auto-Versioning System

### Timestamp Pattern
When file exists, automatically version with timestamp:
```
filename.md → filename-20241111-1430.md
filename.py → filename-20241111-143052.py  # Includes seconds for code
```

### Version Tracking
Keep track of versions in memory:
```
{
  "original": "implementation-plan.md",
  "versions": [
    "implementation-plan-20241111-1000.md",
    "implementation-plan-20241111-1430.md"
  ],
  "latest": "implementation-plan-20241111-1430.md"
}
```

## Activation Patterns

### Explicit Requests
- "Save this to disk"
- "Export this document"
- "Create a file with this content"
- "Save all code blocks"

### Automatic Triggers
After generating content >50 lines with generate-product-document skill:
1. Detect content type
2. Determine best location
3. Save silently
4. Notify: "✅ Saved to `projects/[name]/docs/plan.md`"

### Batch Operations
- "Save each section as a separate file"
- "Export all today's documents"
- "Create project structure for [name]"

## Smart Behaviors

### Project Detection
Look for context clues to identify current project:
- Mentioned project names in conversation
- Recent file operations in specific folders
- Document headers and titles
- User's stated current focus

### Folder Creation
Automatically create necessary directory structure:
```python
# If saving "projects/new-app/docs/prd.md"
# Automatically creates:
# - projects/
# - projects/new-app/
# - projects/new-app/docs/
```

### Learning From Corrections
If user moves a file after saving:
- Remember: "User prefers API specs in /specs not /documents"
- Apply learning to future saves

## File Operations

### Save New File
```python
operation: write_file
parameters:
  path: [intelligent path based on content]
  content: [generated content]
  
# Silent save, then notify
response: "✅ Saved to projects/demestihas-ai/docs/plan-20241111-1430.md"
```

### Handle Existing Files
```python
1. Check if file exists
2. If yes: Generate timestamped version
3. Save with new name
4. Notify: "✅ Saved new version: [filename-timestamp]"
```

### Batch Save
```python
# For multiple code blocks or sections
for each content_block:
  - Determine appropriate filename
  - Check existence
  - Save with versioning if needed
  - Track all saved files
  
response: "✅ Saved 4 files to code/python/: 
  - utils-20241111-1430.py
  - main-20241111-1430.py
  - config-20241111-1430.json
  - requirements.txt"
```

## Integration with Other Skills

### After generate-product-document
```python
if content_lines > 50:
  auto_save = True
  location = determine_location(document_type, context)
  save_silently(content, location)
  notify_user(location)
```

### With memory skill (future)
```python
# Remember where user prefers different file types
memory.store({
  "file_preferences": {
    "api_specs": "always in projects/*/specs/",
    "daily_notes": "prefer daily/YYYY-MM-DD/",
    "code": "organize by language in code/"
  }
})
```

## Security Boundaries

### Allowed Paths
- User's Desktop and Documents folders
- Project-specific directories
- Explicitly requested paths

### Blocked Paths (Never Write)
```python
FORBIDDEN = [
  '/System/', '/Library/', '/etc/', '/usr/',     # System
  '.ssh/', '.aws/', '.config/',                   # Credentials  
  '/Applications/', '~/Library/',                 # Applications
  'node_modules/', '.git/objects/',               # Dependencies
]
```

### Size Limits
- Warn if file >10MB
- Refuse if file >100MB
- Suggest splitting large files

## Notifications

### Success Messages
- "✅ Saved to `[path]`"
- "✅ Created new version: `[filename-timestamp]`"
- "✅ Project structure created at `[path]`"

### Information Messages
- "📁 Created new folder: `[path]`"
- "📝 Detected [type] document, saving to `[location]`"
- "🔄 Previous version backed up as `[filename-timestamp]`"

### Error Recovery
- "⚠️ Cannot write to system directory, saving to exports/ instead"
- "⚠️ Disk full, cannot save file"
- "ℹ️ Path too long, using shortened version"

## Learning & Adaptation

### Pattern Recognition
Track and learn:
- Which projects are currently active
- Preferred locations for file types
- Naming conventions user follows
- Organization patterns

### Context Awareness
Consider:
- Time of day (morning = daily briefs)
- Recent activities (just created PRD = same project)
- Conversation topic (discussing API = likely API spec)
- User corrections (moved files = update preferences)

### Continuous Improvement
After each save:
- Record: location, type, context
- Analyze: patterns over time
- Adapt: future save locations
- Remember: user preferences

## Usage Examples

### Example 1: After PRD Generation
```
User: "Generate a PRD for a todo app"
[generate-product-document creates PRD]
[save-file-local automatically activates]

AI: ✅ Saved to projects/todo-app/docs/prd-20241111-1430.md
```

### Example 2: Code Block Save
```
User: "Save this code as the memory manager"
[detects Python code]

AI: ✅ Saved to code/python/memory-manager-20241111-1431.py
```

### Example 3: Batch Export
```
User: "Save all the API specs we created today"
[finds all API-related content from session]

AI: ✅ Saved 3 files to projects/api-gateway/specs/:
  - auth-endpoints-20241111-1432.md
  - user-endpoints-20241111-1432.md  
  - admin-endpoints-20241111-1432.md
```

## Progressive Disclosure

- **Level 1**: Core save functionality (this description)
- **Level 2**: Full patterns and learning logic
- **Level 3**: Advanced scripts in /scripts/ for complex operations

## Testing Patterns

```bash
# Test basic save
"Save this content as test.md"
# Should save to appropriate location based on content

# Test versioning
"Save this as README.md" (twice)
# Should create README-[timestamp].md on second save

# Test project detection
"This is for the Demestihas AI project. Save the implementation plan"
# Should save to projects/demestihas-ai/docs/

# Test batch operations
"Save each code block as a separate Python file"
# Should create multiple files in code/python/
```
