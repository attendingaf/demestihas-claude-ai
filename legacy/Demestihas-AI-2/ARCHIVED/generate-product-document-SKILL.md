---
name: generate-product-document
description: Generate complete, structured product documents directly as artifacts without conversational wrappers
disable-model-invocation: false
---

# Generate Product Document Skill

## Core Purpose
When you request a document while working in an artifact context, this skill ensures you receive a complete, well-structured document directly—not a conversational summary with "Here's what I created..." wrapper text.

## Activation Triggers

### Explicit Document Requests
- "Generate a [document type]..." (QA Plan, PRD, README, etc.)
- "Draft a [document type] for..."  
- "Write the [document type]..."
- "Create a full implementation plan for..."
- "Build me a [document type]"

### Implicit Document Needs  
- "Outline the architecture for..."
- "Document the API for..."
- "Spec out the feature for..."

## Document Templates

### Implementation Plan Template
```markdown
# Implementation Plan: [Project Name]

## Executive Summary
[2-3 sentence overview of what's being built and why]

## Objectives
- Primary: [Main goal]
- Secondary: [Supporting goals]
- Success Metrics: [How we measure completion]

## Technical Architecture
### Components
- [Component 1]: [Purpose]
- [Component 2]: [Purpose]

### Data Flow
[Describe how data moves through system]

### Technology Stack
- Frontend: [Technologies]
- Backend: [Technologies]  
- Database: [Technologies]

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
Deliverable: [What's complete at end of phase]

### Phase 2: Core Features (Week 2)
- [ ] Task 1
- [ ] Task 2  
- [ ] Task 3
Deliverable: [What's complete at end of phase]

### Phase 3: Polish & Deploy (Week 3)
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
Deliverable: [What's complete at end of phase]

## Risk Mitigation
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | [Strategy] |

## Testing Strategy
- Unit Tests: [Approach]
- Integration Tests: [Approach]
- User Acceptance: [Approach]

## Definition of Done
- [ ] All phases complete
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Deployed to production
```

### API Specification Template
```markdown
# API Specification: [Endpoint Name]

## Endpoint Overview
**Base URL**: `https://api.domain.com/v1`
**Authentication**: Bearer Token / API Key / OAuth2

## [GET/POST/PUT/DELETE] /endpoint/path

### Description
[What this endpoint does]

### Request

#### Headers
```http
Content-Type: application/json
Authorization: Bearer {token}
```

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| param1 | string | Yes | [Description] |
| param2 | integer | No | [Description] |

#### Body (POST/PUT only)
```json
{
  "field1": "value",
  "field2": 123,
  "field3": {
    "nested": "value"
  }
}
```

### Response

#### Success (200 OK)
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "created_at": "2024-11-11T10:00:00Z",
    "field": "value"
  }
}
```

#### Error Responses
| Code | Meaning | Response Body |
|------|---------|---------------|
| 400 | Bad Request | `{"error": "Invalid parameters"}` |
| 401 | Unauthorized | `{"error": "Invalid token"}` |
| 404 | Not Found | `{"error": "Resource not found"}` |
| 500 | Server Error | `{"error": "Internal server error"}` |

### Examples

#### cURL
```bash
curl -X GET "https://api.domain.com/v1/endpoint/path" \
  -H "Authorization: Bearer {token}"
```

#### JavaScript
```javascript
const response = await fetch('https://api.domain.com/v1/endpoint/path', {
  headers: {
    'Authorization': 'Bearer ' + token
  }
});
const data = await response.json();
```
```

### User Story Template
```markdown
# User Story: [Feature Name]

## Story
**As a** [type of user]
**I want to** [action/feature]  
**So that** [benefit/value]

## Acceptance Criteria
- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]

## Technical Notes
- [Implementation consideration]
- [Dependency or constraint]
- [Performance requirement]

## Design Mockups
[Describe UI/UX if applicable]

## Definition of Done
- [ ] Code complete and reviewed
- [ ] Unit tests written and passing
- [ ] Acceptance criteria verified
- [ ] Documentation updated
- [ ] Deployed to staging
```

### QA Test Plan Template
```markdown
# QA Test Plan: [Feature/Release Name]

## Test Overview
**Version**: 1.0
**Test Period**: [Start Date] - [End Date]
**Environment**: Staging / Production

## Test Scope

### In Scope
- [Feature/Component 1]
- [Feature/Component 2]

### Out of Scope  
- [What we're NOT testing]

## Test Cases

### TC001: [Test Case Name]
**Priority**: High/Medium/Low
**Type**: Functional/Integration/Performance

**Preconditions**:
- [Setup requirement]

**Steps**:
1. [Action]
2. [Action]
3. [Action]

**Expected Result**:
- [What should happen]

**Actual Result**: [To be filled during testing]
**Status**: Pass/Fail/Blocked

---

### TC002: [Test Case Name]
[Repeat structure]

## Test Data Requirements
- User accounts: [Types needed]
- Sample data: [What's needed]

## Bug Report Template
**ID**: BUG-[number]
**Severity**: Critical/High/Medium/Low
**Steps to Reproduce**: [List]
**Expected**: [Behavior]
**Actual**: [Behavior]
**Environment**: [Browser/OS/Version]
```

### README Template
```markdown
# [Project Name]

## Overview
[One paragraph description of what this project does]

## Features
- ✨ [Feature 1]
- 🚀 [Feature 2]  
- 🔧 [Feature 3]

## Installation

### Prerequisites
- [Requirement 1] (version X.X)
- [Requirement 2]

### Setup
\`\`\`bash
# Clone the repository
git clone https://github.com/user/project.git

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the application
npm start
\`\`\`

## Usage
[Basic usage examples]

## Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| API_KEY | Your API key | none |
| PORT | Server port | 3000 |

## Contributing
[How to contribute]

## License
[License type]
```

## Disambiguation Rules

### When Template Type is Unclear
If you say something like "Draft that doc for the new feature", I'll ask:
"What type of document would you like me to generate?
- Implementation Plan (technical roadmap)
- API Specification (endpoint documentation)
- User Stories (feature requirements)
- QA Test Plan (testing strategy)
- README (project documentation)
- Product Requirements Document (PRD)"

### When Context is Missing
If you say "Write the API spec", I'll ask:
"I'll generate that API spec. Please provide:
- Endpoint path (e.g., /api/v1/users)
- HTTP methods (GET, POST, etc.)
- Key parameters or data fields"

## Generation Rules

1. **No Conversational Wrappers**: Start directly with the document content
2. **Complete by Default**: Include all standard sections even if not explicitly requested
3. **Professional Format**: Use proper Markdown with headers, tables, code blocks
4. **Context-Aware**: Use all prior conversation and existing artifact content
5. **Template Selection**: Choose the most appropriate template based on request

## Anti-Patterns to Avoid

❌ Don't generate if the request is:
- A general question ("What is an API spec?")
- A debugging request ("Help me fix this")  
- An edit request ("Fix the typo above")
- A non-document query ("What's the weather?")

✅ Do generate for:
- Document creation requests
- Section additions to existing documents
- Complete rewrites of documents

## Progressive Disclosure

- **Level 1**: This description (100 tokens)
- **Level 2**: Core templates and rules (5K tokens)
- **Level 3**: Extended templates in /templates/ directory (unlimited)

## Notes for Document Generation

- Default to Markdown format unless specified otherwise
- Include example code/commands where relevant
- Use tables for structured data
- Add checkboxes for task lists
- Keep sections scannable with clear headers
