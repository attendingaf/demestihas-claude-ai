        elif any(word in text for word in ['persy', 'oldest', 'oldest kid']):
            return 'persy'
        elif any(word in text for word in ['stelios', 'middle', 'middle child']):
            return 'stelios'
        elif any(word in text for word in ['franci', 'youngest', 'baby']):
            return 'franci'
        else:
            return 'mene'
    
    def _create_parsing_prompt(self, text: str) -> str:
        return f"""You are an ADHD-optimized task parser for a family management system. Parse this natural language input into structured data.

INPUT: "{text}"

FAMILY CONTEXT:
- Mene: Primary user (ER physician with ADHD)
- Cindy: Wife (ER physician, inattentive ADHD)  
- Persy: 11yo daughter (loves reading, weather)
- Stelios: 8yo son (soccer, Arsenal fan)
- Franci: 5yo daughter (singing, dancing)
- Viola: Au pair from Germany

PARSING RULES:

1. RECORD_TYPE (choose one):
   - "Shopping" for grocery/store items (groceries, buy milk, add eggs to list, etc.)
   - "Task" for general to-dos
   - "Reminder" for time-based alerts
   - "Appointment" for scheduled events

2. STORE (if Shopping):
   - "Groceries" for generic grocery items
   - "Publix" if specifically mentioned
   - "Target", "Costco", etc. if mentioned
   - null for non-shopping

3. GROCERY_CATEGORY (if grocery item):
   - "Dairy" (milk, eggs, yogurt, cheese)
   - "Produce" (fruits, vegetables)
   - "Meat" (chicken, beef, fish)
   - "Pantry" (canned goods, spices)
   - "Frozen" (frozen foods)
   - "Bakery" (bread, pastries)

4. EISENHOWER_QUADRANT:
   - "🔥 Do Now" (urgent + important)
   - "📅 Schedule" (important, not urgent)
   - "👥 Delegate" (urgent, not important)
   - "🗄️ Someday/Maybe" (neither urgent nor important)
   - "🧠 Brain Dump" (unclear/default)

5. ENERGY_LEVEL:
   - "Low" (simple errands, quick tasks)
   - "Medium" (standard focus needed)
   - "High" (deep work, complex tasks)

6. TIME_ESTIMATE:
   - "⚡ Quick (<15m)" 
   - "🔍 Short (15-30m)"
   - "🎯 Deep (>30m)"
   - "📅 Multi-hour"

7. CONTEXT_TAGS (array):
   - ["Errand"] for shopping/errands
   - ["Family"] for family-related
   - ["Call"] for phone calls
   - ["Email"] for email tasks
   - ["Deep Work"] for focused work
   - ["Quick Win"] for easy tasks

8. ASSIGNED_TO:
   - "mene" (default)
   - "cindy" for wife references
   - "viola" for au pair tasks
   - "persy", "stelios", "franci" for kids

RESPOND WITH ONLY VALID JSON:
{{
  "record_type": "Shopping|Task|Reminder|Appointment",
  "title": "Clear, actionable title",
  "store": "Store name or null",
  "grocery_category": "Category or null",
  "eisenhower_quadrant": "Quadrant with emoji",
  "energy_level": "Low|Medium|High",
  "time_estimate": "Estimate with emoji",
  "context_tags": ["tag1", "tag2"],
  "assigned_to": "family_member",
  "due_date": "YYYY-MM-DD or null",
  "notes": "Additional context",
  "timestamp": "{datetime.now().strftime('%Y-%m-%d %H:%M')}"
}}"""
