from datetime import datetime, timedelta

def parse_relative_date(date_text):
    if not date_text:
        return None
    
    date_lower = date_text.lower().strip()
    today = datetime.now().date()
    
    # Test cases
    if date_lower in ['today', 'now']:
        return today.strftime('%Y-%m-%d')
    elif date_lower == 'tomorrow':
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'next week' in date_lower:
        return (today + timedelta(days=7)).strftime('%Y-%m-%d')
    else:
        return date_text

# Test the function
test_cases = ['today', 'tomorrow', 'next week', '2024-12-25']
for test in test_cases:
    result = parse_relative_date(test)
    print(f'{test:12} -> {result}')
