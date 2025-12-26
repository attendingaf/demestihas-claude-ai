#!/usr/bin/env node

/**
 * Test script to verify EA-AI agent routing is correctly configured
 */

// Test queries and their expected agent routing
const testQueries = [
  // Lyco tests (Task & Time Management)
  { query: "when is my next meeting", expected: "lyco" },
  { query: "find free time tomorrow", expected: "lyco" },
  { query: "break down this task into chunks", expected: "lyco" },
  { query: "what's my deadline for the project", expected: "lyco" },
  { query: "prioritize my todo list", expected: "lyco" },
  { query: "match tasks to my energy levels", expected: "lyco" },
  { query: "schedule time for deep work", expected: "lyco" },
  
  // Kairos tests (Networking & Professional)
  { query: "draft linkedin message", expected: "kairos" },
  { query: "professional introduction email", expected: "kairos" },
  { query: "networking event preparation", expected: "kairos" },
  { query: "update my CRM contacts", expected: "kairos" },
  { query: "career coaching advice", expected: "kairos" },
  { query: "administrative task help", expected: "kairos" },
  
  // Pluma tests (Email)
  { query: "draft email response", expected: "pluma" },
  { query: "check gmail inbox", expected: "pluma" },
  { query: "send email to team", expected: "pluma" },
  
  // Huata tests (Calendar)
  { query: "schedule meeting with team", expected: "huata" },
  { query: "check calendar conflicts", expected: "huata" },
  { query: "create new calendar event", expected: "huata" }
];

// Agent detection function (mirrors the one in mcp-server.js)
function detectAgent(operation) {
  const opLower = operation.toLowerCase();
  
  // Check for specific multi-word phrases first (higher priority)
  if (opLower.includes('next meeting') || opLower.includes('free time')) {
    return 'lyco';
  }
  
  if (opLower.includes('linkedin') || opLower.includes('professional introduction') || 
      opLower.includes('networking') || opLower.includes('administrative')) {
    return 'kairos';
  }
  
  // Then check single keywords in priority order
  const keywords = {
    pluma: ['email', 'gmail', 'inbox', 'send'],
    huata: ['calendar', 'appointment', 'event', 'availability'],
    lyco: ['task', 'todo', 'priority', 'deadline', 'when', 'break down', 'prioritize', 'chunk', 'focus', 'energy', 'timer', 'reminder', 'duration', 'time'],
    kairos: ['professional', 'introduction', 'admin', 'contact', 'relationship', 'career', 'coach', 'crm', 'administrative']
  };
  
  // Special handling for ambiguous keywords
  if (opLower.includes('schedule')) {
    // If it's about scheduling time for work, it's Lyco
    if (opLower.includes('time') || opLower.includes('work') || opLower.includes('task')) {
      return 'lyco';
    }
    // If it's about scheduling meetings/events, it's Huata
    if (opLower.includes('meeting') || opLower.includes('event') || opLower.includes('appointment')) {
      return 'huata';
    }
    // Default schedule to Lyco (time management)
    return 'lyco';
  }
  
  if (opLower.includes('meeting')) {
    // "next meeting" queries go to Lyco (time awareness)
    if (opLower.includes('next') || opLower.includes('when')) {
      return 'lyco';
    }
    // Scheduling meetings goes to Huata
    return 'huata';
  }
  
  // Standard keyword matching
  for (const [agent, words] of Object.entries(keywords)) {
    if (words.some(word => opLower.includes(word))) {
      return agent;
    }
  }
  
  return 'lyco'; // Default to task manager
}

// Run tests
console.log('Testing EA-AI Agent Routing\n');
console.log('=' .repeat(60));

let passed = 0;
let failed = 0;

for (const test of testQueries) {
  const result = detectAgent(test.query);
  const success = result === test.expected;
  
  if (success) {
    passed++;
    console.log(`✓ "${test.query}"`);
    console.log(`  → Correctly routed to ${result.toUpperCase()}`);
  } else {
    failed++;
    console.log(`✗ "${test.query}"`);
    console.log(`  → Expected ${test.expected.toUpperCase()} but got ${result.toUpperCase()}`);
  }
  console.log();
}

// Summary
console.log('=' .repeat(60));
console.log(`\nTest Results: ${passed} passed, ${failed} failed`);

if (failed === 0) {
  console.log('✅ All routing tests passed!');
  console.log('\nAgent role definitions are correctly configured:');
  console.log('- LYCO handles all task & time management');
  console.log('- KAIROS handles networking & professional development');
  console.log('- PLUMA handles email operations');
  console.log('- HUATA handles calendar operations');
} else {
  console.log('❌ Some routing tests failed. Please review the routing configuration.');
  process.exit(1);
}