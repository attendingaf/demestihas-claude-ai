# Claude Desktop Tools Reference

## Overview
This document provides a comprehensive list of tools available in Claude Desktop for use in LLM prompts and instructions.

## Available Tools by Category

### 🌐 Web & Search Tools
- **web_search** - Search the internet for current information, news, and general web content
- **web_fetch** - Retrieve and read content from specific URLs/web pages

### 📁 Google Workspace Integration
#### Google Drive
- **google_drive_search** - Search through Google Drive files and documents
- **google_drive_fetch** - Retrieve content from specific Google Drive documents

#### Gmail
- **read_gmail_profile** - Get the Gmail profile of the authenticated user
- **search_gmail_messages** - Search and list Gmail messages with query filters
- **read_gmail_thread** - Read a complete Gmail thread by ID
- **read_gmail_message** - Read a specific Gmail message (use thread instead for context)

#### Google Calendar
- **list_gcal_calendars** - List all available Google calendars
- **list_gcal_events** - List/search events from Google Calendar
- **fetch_gcal_event** - Retrieve a specific calendar event
- **find_free_time** - Find free time periods across calendars

### 💻 File System Operations
- **Filesystem:read_file** - Read contents of a file
- **Filesystem:read_multiple_files** - Read multiple files simultaneously
- **Filesystem:write_file** - Create or overwrite a file with content
- **Filesystem:edit_file** - Make line-based edits to text files
- **Filesystem:create_directory** - Create new directories
- **Filesystem:list_directory** - List contents of a directory
- **Filesystem:directory_tree** - Get recursive tree view of directories
- **Filesystem:move_file** - Move or rename files and directories
- **Filesystem:search_files** - Search for files matching patterns
- **Filesystem:get_file_info** - Get metadata about files/directories
- **Filesystem:list_allowed_directories** - List directories with access permissions

### 🔧 Development Tools

#### Git Version Control
- **git:git_status** - Show working tree status
- **git:git_diff_unstaged** - Show unstaged changes
- **git:git_diff_staged** - Show staged changes
- **git:git_diff** - Show differences between branches/commits
- **git:git_commit** - Commit changes to repository
- **git:git_add** - Stage files for commit
- **git:git_reset** - Unstage all staged changes
- **git:git_log** - Show commit history
- **git:git_create_branch** - Create new branch
- **git:git_checkout** - Switch branches
- **git:git_show** - Show commit contents
- **git:git_init** - Initialize new repository
- **git:git_branch** - List branches

#### n8n Workflow Automation
- **n8n-mcp:tools_documentation** - Get n8n tool documentation
- **n8n-mcp:list_nodes** - List available n8n nodes
- **n8n-mcp:get_node_info** - Get detailed node schema
- **n8n-mcp:search_nodes** - Search nodes by keywords
- **n8n-mcp:list_ai_tools** - List AI-optimized nodes
- **n8n-mcp:get_node_documentation** - Get readable node docs
- **n8n-mcp:get_node_essentials** - Get key node properties
- **n8n-mcp:validate_node_operation** - Validate node configuration
- **n8n-mcp:n8n_create_workflow** - Create new workflow
- **n8n-mcp:n8n_get_workflow** - Retrieve workflow by ID
- **n8n-mcp:n8n_update_full_workflow** - Update entire workflow
- **n8n-mcp:n8n_delete_workflow** - Delete workflow
- **n8n-mcp:n8n_list_workflows** - List all workflows
- **n8n-mcp:n8n_trigger_webhook_workflow** - Trigger workflow via webhook
- **n8n-mcp:n8n_list_executions** - List workflow executions

#### Analysis Tool
- **repl** - JavaScript REPL for calculations, data analysis, and file processing (supports lodash, papaparse, sheetjs, mathjs, d3)

### 🍎 Apple Ecosystem Integration
- **apple-mcp:contacts** - Search and retrieve Apple Contacts
- **apple-mcp:notes** - Create, search, and list Apple Notes
- **apple-mcp:messages** - Send, read, schedule Messages
- **apple-mcp:mail** - Read, search, send Apple Mail
- **apple-mcp:reminders** - Create and manage Reminders
- **apple-mcp:calendar** - Search and create Calendar events
- **apple-mcp:maps** - Search locations, get directions in Apple Maps
- **apple-mcp:webSearch** - Web search via DuckDuckGo
- **Control your Mac:osascript** - Execute AppleScript commands

### 🎨 Design & Creative Tools

#### Canva Integration
- **Canva:search-designs** - Search Canva designs
- **Canva:get-design** - Get design details
- **Canva:get-design-pages** - Get design pages
- **Canva:get-design-content** - Get design content
- **Canva:import-design-from-url** - Import file as Canva design
- **Canva:export-design** - Export designs to various formats
- **Canva:create-folder** - Create Canva folders
- **Canva:move-item-to-folder** - Organize Canva items
- **Canva:list-folder-items** - List folder contents
- **Canva:comment-on-design** - Add design comments
- **Canva:generate-design** - Create designs with AI
- **Canva:resize-design** - Resize designs

### 📝 Productivity Tools

#### Notion Integration
- **notionApi:API-get-user** - Retrieve Notion user
- **notionApi:API-get-users** - List all users
- **notionApi:API-post-database-query** - Query Notion database
- **notionApi:API-post-search** - Search Notion by title
- **notionApi:API-get-block-children** - Get block children
- **notionApi:API-patch-block-children** - Append block children
- **notionApi:API-retrieve-a-block** - Retrieve specific block
- **notionApi:API-update-a-block** - Update block
- **notionApi:API-delete-a-block** - Delete block
- **notionApi:API-retrieve-a-page** - Retrieve page
- **notionApi:API-patch-page** - Update page properties
- **notionApi:API-post-page** - Create new page
- **notionApi:API-create-a-database** - Create database
- **notionApi:API-update-a-database** - Update database
- **notionApi:API-retrieve-a-database** - Retrieve database

### 🌐 Browser Control
- **Control Chrome:open_url** - Open URL in Chrome
- **Control Chrome:get_current_tab** - Get current tab info
- **Control Chrome:list_tabs** - List all open tabs
- **Control Chrome:close_tab** - Close specific tab
- **Control Chrome:switch_to_tab** - Switch to tab
- **Control Chrome:reload_tab** - Reload tab
- **Control Chrome:go_back** - Navigate back in history
- **Control Chrome:go_forward** - Navigate forward
- **Control Chrome:execute_javascript** - Execute JS in tab
- **Control Chrome:get_page_content** - Get page text content

### 💬 Conversation Management
- **conversation_search** - Search through past conversations with Claude
- **recent_chats** - Retrieve recent chat history
- **end_conversation** - Terminate current conversation

### 📄 Content Creation
- **artifacts** - Create and update persistent content (code, documents, visualizations) that can be referenced throughout conversation

## Usage Guidelines

### For LLM Prompting
When instructing an LLM to use these tools, you can reference them by their exact names as listed above. For example:

```
"Use the web_search tool to find current information about [topic]"
"Read the file at [path] using Filesystem:read_file"
"Search my Gmail for messages about [subject] using search_gmail_messages"
```

### Tool Categories Quick Reference
- **Research**: web_search, web_fetch, google_drive_search
- **File Management**: Filesystem:* tools
- **Development**: git:*, n8n-mcp:*, repl
- **Communication**: Gmail, Messages, Mail tools
- **Productivity**: Calendar, Reminders, Notion, Canva
- **System Control**: Chrome control, osascript

### Important Notes
1. Tool names are case-sensitive
2. Some tools require specific parameters or authentication
3. File system tools only work within allowed directories
4. Web fetch can only access public URLs or those returned by search
5. The repl tool executes JavaScript in a browser environment, not Node.js

## Common Use Cases

### Research & Information Gathering
- Combine web_search with web_fetch for comprehensive research
- Use google_drive_search for internal/company documents
- Search past conversations with conversation_search

### File & Code Management
- Use git tools for version control operations
- Filesystem tools for reading, writing, and organizing files
- repl for data analysis and calculations

### Communication & Scheduling
- Gmail tools for email management
- Calendar tools for scheduling and finding free time
- Messages/Mail for Apple ecosystem communication

### Automation & Workflows
- n8n tools for workflow automation
- Chrome control for browser automation
- osascript for Mac system automation

---
*Last Updated: August 25, 2025*
*This reference is designed for use in LLM prompts and instructions*