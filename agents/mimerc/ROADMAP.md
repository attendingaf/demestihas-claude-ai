# MiMerc Bot - Development Roadmap

## Current Sprint: ✅ State Persistence Fix - COMPLETE
**Goal**: Fix critical bug preventing grocery list persistence across messages

### Completed This Sprint
- [x] Applied state persistence patch
- [x] Created verification test script
- [x] Documented fix in REQUIREMENTS.md
- [x] Created deployment script

### Completed Features
✅ **Core Grocery Management** (v1.0)
- Natural language add/remove/view
- Quantity support  
- Case-insensitive matching

✅ **Telegram Integration** (v1.0)
- Conversational interface
- Emoji formatting
- Typing indicators

⏳ **State Persistence Fix** (v1.1) - TODAY
- Remove grocery_list initialization bug
- Ensure proper state return in tool_executor
- Add checkpoint verification

## Backlog (Prioritized)

### High Priority
**S** - Enhanced List Operations
- User Story: "As a user, I want to update quantities without removing/re-adding"
- Acceptance: Can say "Change milk to 2 gallons"

**M** - Category Support
- User Story: "As a user, I want items organized by store section"  
- Acceptance: Auto-categorize dairy, produce, meat, etc.

**S** - Smart Suggestions
- User Story: "As a user, I want reminders for commonly bought items"
- Acceptance: "You often buy milk, add it?"

### Medium Priority  
**M** - Multi-List Support
- User Story: "As a family, we want separate lists for different stores"
- Acceptance: "Add to Costco list" vs "Add to grocery list"

**L** - Recipe Integration
- User Story: "As a cook, I want to add all ingredients from a recipe"
- Acceptance: "Add ingredients for chicken tikka masala"

**S** - Export Functionality
- User Story: "As a shopper, I want to share my list"
- Acceptance: Export as text or image

### Low Priority
**S** - Undo/History
- User Story: "As a user, I want to undo recent changes"
- Acceptance: "Undo last" or "Show history"

**M** - Voice Messages
- User Story: "As a driver, I want to add items via voice"
- Acceptance: Process Telegram voice messages

## Success Metrics
- Response time < 2 seconds
- State persistence 100% reliable
- Zero message duplication
- Thread isolation verified

## Technical Debt
- Add comprehensive logging
- Implement retry logic for DB connections
- Add health check endpoint
- Create backup/restore functionality

## Notes
- Focus on reliability over features
- Each feature must include tests
- Document all state changes
- Maintain backward compatibility