#!/usr/bin/env python3
import asyncio
import sys
from datetime import datetime
from uuid import uuid4

# Add src to path
sys.path.append('src')

async def test_basic_imports():
    print('🧪 Testing Phase 3 Component Imports...')
    
    try:
        from skip_intelligence import SkipIntelligence, SkipAction
        print('   ✅ Skip Intelligence imported')
        
        from pattern_learner import PatternLearner
        print('   ✅ Pattern Learner imported')
        
        from weekly_review import WeeklyReview
        print('   ✅ Weekly Review imported')
        
        from models import Task
        print('   ✅ Task model imported')
        
        return True
        
    except Exception as e:
        print(f'❌ Import test failed: {e}')
        return False

async def main():
    print('🚀 Phase 3: Skip Intelligence Testing')
    print('=' * 50)
    
    result = await test_basic_imports()
    
    if result:
        print('')
        print('🎉 Phase 3 components are ready!')
        print('Next steps:')
        print('1. Apply database migration')
        print('2. Test with real database')
        print('3. Deploy and test skip functionality')
    else:
        print('')
        print('⚠️  Phase 3 needs fixes before deployment.')

if __name__ == '__main__':
    asyncio.run(main())
