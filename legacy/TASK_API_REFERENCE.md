# Task System API Reference (Active)

**Base URL**: `https://claude.beltlineconsulting.co`
**Auth**: `Authorization: Bearer <TASK_API_KEY>`

## Endpoints

### Tasks

- **List All Incomplete**: `GET /tasks`
- **List Task Lists**: `GET /tasks/lists`
- **Get Blocked Tasks**: `GET /tasks/blocked`
- **Create Task**: `POST /tasks`

  ```json
  {
    "listId": "Required",
    "title": "Required",
    "notes": "Optional",
    "due": "Optional (RFC 3339)"
  }
  ```

- **Update Task**: `PATCH /tasks/:taskId`
- **Complete Task**: `POST /tasks/:taskId/complete`
- **Delete Task**: `DELETE /tasks/:taskId`

### Briefing & Context

- **Morning Briefing**: `GET /briefing`
  - Returns JSON with calendar events + tasks + synthesized focus.
  - Query param: `?format=markdown` for raw text.
- **Trigger Email**: `POST /briefing/email`
  - Sends HTML briefing to <menelaos4@gmail.com>.

## Known List IDs

- **My Tasks**: `MDg1MDQwMDI4OTA5MDc4NjA0Mjc6MDow`
*(Run `GET /tasks/lists` to map @Metrias, @Beltline, etc.)*

## Architecture

- **Framework**: Express (Node.js) on VPS.
- **Integration**: Wraps Google Tasks API v1 & Google Calendar API v3.
- **Status**: Live & deployed.
