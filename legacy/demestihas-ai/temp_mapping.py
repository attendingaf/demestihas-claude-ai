
# Eisenhower mapping function for enhanced parser integration
def map_eisenhower_format(enhanced_analysis):
    """Map enhanced parser output to bot-expected format"""
    eisenhower_map = {
        "DO_NOW": "🔥 Do Now",
        "SCHEDULE": "📅 Schedule", 
        "DELEGATE": "👥 Delegate",
        "SOMEDAY": "🗄️ Someday/Maybe",
        "BRAIN_DUMP": "🧠 Brain Dump"
    }
    energy_map = {"Low": "Low", "Medium": "Medium", "High": "High"}
    time_map = {
        "Quick": "⚡ Quick (<15m)",
        "Short": "📝 Short (15-30m)",
        "Deep": "🎯 Deep (>30m)",
        "Multi-hour": "📅 Multi-hour"
    }
    
    if "tasks" in enhanced_analysis and enhanced_analysis["tasks"]:
        task = enhanced_analysis["tasks"][0]  # Take first task
        return {
            "parsed_task": task.get("name", "New Task"),
            "eisenhower": eisenhower_map.get(task.get("eisenhower"), "🧠 Brain Dump"),
            "energy": energy_map.get(task.get("energy"), "Medium"),
            "time_estimate": time_map.get(task.get("time_estimate"), "📝 Short (15-30m)"),
            "context": task.get("context", ["Quick Win"]),
            "assigned_to": task.get("assigned_to"),
            "due_date": task.get("due_date"),
            "adhd_notes": enhanced_analysis.get("reasoning", ""),
            "record_type": "Task"
        }
    else:
        return {
            "parsed_task": "Could not parse task",
            "eisenhower": "🧠 Brain Dump",
            "energy": "Medium",
            "time_estimate": "📝 Short (15-30m)",
            "context": ["Quick Win"],
            "assigned_to": None,
            "due_date": None,
            "adhd_notes": "Parsing failed - please review",
            "record_type": "Task"
        }

