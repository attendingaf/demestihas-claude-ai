#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema,
  ListToolsRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';
import crypto from 'crypto';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Import memory store adapters
import simpleMemoryStore from './simple-memory-store.js';
import ragMemoryAdapter from './rag-memory-adapter.js';
import DoneCommandHandler from './done-command-handler.js';

// Use RAG adapter if available, fallback to simple store
let memoryStore = ragMemoryAdapter;
let contextRetriever, patternDetector;
let doneHandler; // Handler for /done command

async function initializeMemorySystem() {
  try {
    // Try to initialize RAG adapter first
    try {
      await memoryStore.initialize();
      console.error('[MCP Memory] RAG memory system initialized successfully');
    } catch (ragError) {
      console.error('[MCP Memory] RAG initialization failed, falling back to simple store:', ragError.message);
      memoryStore = simpleMemoryStore;
      await memoryStore.initialize();
      console.error('[MCP Memory] Simple memory system initialized as fallback');
    }
    
    // Set up context retriever using the active memory store
    contextRetriever = {
      getContext: async (query, options = {}) => {
        const memories = await memoryStore.search(query, options);
        return {
          query,
          memories,
          patterns: [],
          timestamp: Date.now()
        };
      }
    };
    
    // Simple pattern detector
    patternDetector = {
      detectPattern: async (actions) => ({
        id: crypto.randomUUID(),
        pattern: actions.join(' -> '),
        confidence: 0.8,
        occurrences: 3
      }),
      getPatterns: async (query) => []
    };
    
    // Initialize /done command handler
    doneHandler = new DoneCommandHandler(memoryStore);
    
    return true;
  } catch (error) {
    console.error('[MCP Memory] Failed to initialize memory system:', error.message);
    throw error;
  }
}

// Analysis patterns for detecting valuable information
const ANALYSIS_PATTERNS = {
  solution: /(?:fixed|solved|solution|resolved|worked|working now)[\s\S]{0,200}/gi,
  configuration: /(?:config|setting|path|url|endpoint|token|key|variable|env)[\s\S]{0,200}/gi,
  discovery: /(?:discovered|found|realized|learned|turns out|noticed|observed)[\s\S]{0,200}/gi,
  decision: /(?:decided|chose|selected|will use|going with|opted for)[\s\S]{0,200}/gi,
  error_fix: /(?:error|failed|issue|problem|bug|crash)[\s\S]{0,200}(?:fixed|solved|resolved|workaround)/gi,
  command: /(?:run|execute|command|npm|yarn|docker|git|curl|bash)[\s\S]{0,100}/gi,
  workflow: /(?:step|process|procedure|workflow|sequence|order)[\s\S]{0,200}/gi,
  insight: /(?:important|critical|key|essential|remember|note)[\s\S]{0,200}/gi
};

// Memory state management
class MemoryManager {
  constructor() {
    this.pendingMemories = new Map();
    this.sessionMemories = [];
    this.conversationBuffer = [];
    this.sessionStartTime = Date.now();
  }

  addToPending(memory) {
    const id = crypto.randomUUID();
    this.pendingMemories.set(id, {
      ...memory,
      id,
      timestamp: Date.now(),
      status: 'pending'
    });
    return id;
  }

  getPending(id) {
    return this.pendingMemories.get(id);
  }

  confirmMemory(id) {
    const memory = this.pendingMemories.get(id);
    if (memory) {
      memory.status = 'confirmed';
      this.sessionMemories.push(memory);
      this.pendingMemories.delete(id);
      return memory;
    }
    return null;
  }

  addToConversation(text) {
    this.conversationBuffer.push({
      text,
      timestamp: Date.now()
    });
    // Keep only last 20 entries
    if (this.conversationBuffer.length > 20) {
      this.conversationBuffer.shift();
    }
  }

  getRecentConversation() {
    return this.conversationBuffer
      .map(entry => entry.text)
      .join('\n');
  }
}

const memoryManager = new MemoryManager();

// Initialize the MCP server
const server = new Server(
  {
    name: 'smart-memory',
    version: '2.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions
const TOOLS = [
  {
    name: 'analyze_for_memory',
    description: 'Analyzes conversation to find valuable information worth remembering',
    inputSchema: {
      type: 'object',
      properties: {
        conversation_context: {
          type: 'string',
          description: 'Recent conversation text to analyze'
        },
        focus_areas: {
          type: 'array',
          items: { type: 'string' },
          description: 'Specific areas to focus on (e.g., "solutions", "configurations", "decisions")'
        }
      },
      required: ['conversation_context']
    }
  },
  {
    name: 'propose_memory',
    description: 'Proposes specific information to store in memory (requires user confirmation)',
    inputSchema: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'The information to remember'
        },
        category: {
          type: 'string',
          enum: ['solution', 'configuration', 'error_fix', 'decision', 'workflow', 'insight', 'command', 'note'],
          description: 'Category of the memory'
        },
        importance: {
          type: 'string',
          enum: ['low', 'medium', 'high', 'critical'],
          description: 'Importance level'
        },
        metadata: {
          type: 'object',
          description: 'Additional metadata (tags, related topics, etc.)'
        },
        rationale: {
          type: 'string',
          description: 'Why this should be remembered'
        }
      },
      required: ['content', 'category', 'importance', 'rationale']
    }
  },
  {
    name: 'confirm_and_store',
    description: 'Stores memory after user confirmation',
    inputSchema: {
      type: 'object',
      properties: {
        memory_id: {
          type: 'string',
          description: 'ID of the pending memory'
        },
        user_confirmed: {
          type: 'boolean',
          description: 'Whether the user confirmed storage'
        },
        user_edits: {
          type: 'string',
          description: 'Any edits the user made to the memory'
        }
      },
      required: ['memory_id', 'user_confirmed']
    }
  },
  {
    name: 'detect_patterns_in_conversation',
    description: 'Identifies workflow patterns in the conversation',
    inputSchema: {
      type: 'object',
      properties: {
        actions_taken: {
          type: 'array',
          items: { type: 'string' },
          description: 'List of actions or steps taken'
        },
        tools_used: {
          type: 'array',
          items: { type: 'string' },
          description: 'Tools or commands used'
        },
        problem_solved: {
          type: 'string',
          description: 'The problem that was solved'
        }
      },
      required: ['actions_taken']
    }
  },
  {
    name: 'get_relevant_context',
    description: 'Retrieves relevant memories for the current topic',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'What to search for'
        },
        include_failures: {
          type: 'boolean',
          description: 'Include past failures and errors',
          default: true
        }
      },
      required: ['query']
    }
  },
  {
    name: 'track_decision',
    description: 'Records important decisions with reasoning',
    inputSchema: {
      type: 'object',
      properties: {
        decision: {
          type: 'string',
          description: 'The decision made'
        },
        reasoning: {
          type: 'string',
          description: 'Why this decision was made'
        },
        alternatives_considered: {
          type: 'array',
          items: { type: 'string' },
          description: 'Other options that were considered'
        },
        impact: {
          type: 'string',
          description: 'Expected impact or consequences'
        }
      },
      required: ['decision', 'reasoning']
    }
  },
  {
    name: 'remember_error_and_fix',
    description: 'Stores errors and their solutions for future reference',
    inputSchema: {
      type: 'object',
      properties: {
        error: {
          type: 'string',
          description: 'The error or problem encountered'
        },
        solution: {
          type: 'string',
          description: 'How it was fixed'
        },
        context: {
          type: 'string',
          description: 'Context where this occurred'
        },
        prevention: {
          type: 'string',
          description: 'How to prevent this in the future'
        }
      },
      required: ['error', 'solution']
    }
  },
  {
    name: 'session_summary',
    description: 'Creates a summary of the current session',
    inputSchema: {
      type: 'object',
      properties: {
        topics_covered: {
          type: 'array',
          items: { type: 'string' },
          description: 'Main topics discussed'
        },
        problems_solved: {
          type: 'array',
          items: { type: 'string' },
          description: 'Problems that were solved'
        },
        key_insights: {
          type: 'array',
          items: { type: 'string' },
          description: 'Important insights or learnings'
        },
        next_steps: {
          type: 'array',
          items: { type: 'string' },
          description: 'Planned next steps or TODOs'
        }
      },
      required: ['topics_covered']
    }
  },
  {
    name: 'check_memory_conflicts',
    description: 'Checks for conflicting information in memory',
    inputSchema: {
      type: 'object',
      properties: {
        new_information: {
          type: 'string',
          description: 'New information to check'
        },
        category: {
          type: 'string',
          description: 'Category to check within'
        }
      },
      required: ['new_information']
    }
  },
  {
    name: 'handle_done_command',
    description: 'Process /done command to review thread and extract memories',
    inputSchema: {
      type: 'object',
      properties: {
        conversation: {
          type: 'array',
          items: { type: 'string' },
          description: 'Array of conversation messages to analyze'
        },
        user_response: {
          type: 'string',
          description: 'User response to memory proposals (optional)'
        }
      },
      required: ['conversation']
    }
  }
];

// Handler for listing available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: TOOLS
  };
});

// Handler for tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  try {
    switch (name) {
      case 'handle_done_command': {
        const { conversation, user_response } = args;
        
        // If user_response is provided, process it
        if (user_response && doneHandler.pendingMemories.size > 0) {
          const proposals = Array.from(doneHandler.pendingMemories.values());
          const result = await doneHandler.processUserResponse(user_response, proposals);
          return {
            content: [{
              type: 'text',
              text: result
            }]
          };
        }
        
        // Otherwise, analyze the conversation
        const result = await doneHandler.handleDoneCommand(conversation);
        return {
          content: [{
            type: 'text',
            text: result
          }]
        };
      }
      
      case 'analyze_for_memory': {
        const { conversation_context, focus_areas = [] } = args;
        memoryManager.addToConversation(conversation_context);
        
        const findings = [];
        const text = conversation_context.toLowerCase();
        
        // Check each pattern
        for (const [category, pattern] of Object.entries(ANALYSIS_PATTERNS)) {
          if (focus_areas.length > 0 && !focus_areas.includes(category)) {
            continue;
          }
          
          const matches = conversation_context.match(pattern);
          if (matches) {
            matches.forEach(match => {
              // Calculate importance based on keywords
              let importance = 'medium';
              if (match.match(/critical|essential|important|must/i)) {
                importance = 'high';
              } else if (match.match(/fixed|solved|resolved/i)) {
                importance = 'high';
              }
              
              findings.push({
                category,
                content: match.trim(),
                importance,
                confidence: 0.7 + (match.length > 100 ? 0.2 : 0)
              });
            });
          }
        }
        
        // Deduplicate and sort by importance
        const unique = findings.reduce((acc, curr) => {
          const exists = acc.find(f => f.content === curr.content);
          if (!exists) acc.push(curr);
          return acc;
        }, []);
        
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              findings: unique.sort((a, b) => {
                const importanceOrder = { critical: 4, high: 3, medium: 2, low: 1 };
                return importanceOrder[b.importance] - importanceOrder[a.importance];
              }),
              analyzed_length: conversation_context.length,
              patterns_checked: Object.keys(ANALYSIS_PATTERNS).length,
              recommendation: unique.length > 0 
                ? `Found ${unique.length} valuable pieces of information. Use 'propose_memory' to store the most important ones.`
                : 'No significant information found that needs to be remembered.'
            }, null, 2)
          }]
        };
      }

      case 'propose_memory': {
        const { content, category, importance, metadata = {}, rationale } = args;
        
        const memory = {
          content,
          type: category,
          importance,
          metadata: {
            ...metadata,
            rationale,
            proposed_at: new Date().toISOString(),
            session_id: memoryManager.sessionStartTime
          }
        };
        
        const id = memoryManager.addToPending(memory);
        
        const proposal = `
📝 **MEMORY PROPOSAL** (ID: ${id})

**Category:** ${category}
**Importance:** ${importance}
**Content:** 
${content}

**Rationale:** ${rationale}

**Metadata:**
${JSON.stringify(metadata, null, 2)}

---
To store this memory, use: confirm_and_store with memory_id: "${id}"
To edit before storing, provide user_edits parameter.
`;
        
        return {
          content: [{
            type: 'text',
            text: proposal
          }]
        };
      }

      case 'confirm_and_store': {
        const { memory_id, user_confirmed, user_edits } = args;
        
        if (!user_confirmed) {
          memoryManager.pendingMemories.delete(memory_id);
          return {
            content: [{
              type: 'text',
              text: '❌ Memory storage cancelled by user.'
            }]
          };
        }
        
        const memory = memoryManager.getPending(memory_id);
        if (!memory) {
          return {
            content: [{
              type: 'text',
              text: `⚠️ No pending memory found with ID: ${memory_id}`
            }]
          };
        }
        
        // Apply user edits if provided
        if (user_edits) {
          memory.content = user_edits;
          memory.metadata.user_edited = true;
        }
        
        // Store in memory system
        const result = await memoryStore.store({
          content: memory.content,
          type: memory.type,
          category: memory.type || 'general',
          importance: memory.importance || 'medium',
          metadata: memory.metadata,
          projectId: 'mcp-smart-memory',
          userId: 'claude-desktop'
        });
        
        memoryManager.confirmMemory(memory_id);
        
        return {
          content: [{
            type: 'text',
            text: `✅ Memory stored successfully!\n\nID: ${result.id}\nCategory: ${memory.type}\nImportance: ${memory.importance}`
          }]
        };
      }

      case 'detect_patterns_in_conversation': {
        const { actions_taken, tools_used = [], problem_solved = '' } = args;
        
        const pattern = await patternDetector.detectPattern(actions_taken);
        
        if (pattern) {
          const patternMemory = {
            content: `Workflow Pattern: ${problem_solved || 'Unnamed Task'}`,
            type: 'workflow',
            importance: 'high',
            metadata: {
              steps: actions_taken,
              tools: tools_used,
              pattern_id: pattern.id,
              problem: problem_solved
            },
            rationale: 'Detected repeatable workflow pattern'
          };
          
          const id = memoryManager.addToPending(patternMemory);
          
          return {
            content: [{
              type: 'text',
              text: `🔄 Pattern detected! This workflow appears to be repeatable.

**Steps:** ${actions_taken.join(' → ')}
**Tools Used:** ${tools_used.join(', ') || 'None specified'}
**Problem Solved:** ${problem_solved}

Pattern has been proposed as memory ID: ${id}
Use confirm_and_store to save this workflow.`
            }]
          };
        }
        
        return {
          content: [{
            type: 'text',
            text: 'No clear pattern detected yet. Continue documenting workflows to identify patterns.'
          }]
        };
      }

      case 'get_relevant_context': {
        const { query, include_failures = true } = args;
        
        const context = await contextRetriever.getContext(query, {
          includeFailures: include_failures,
          limit: 5
        });
        
        if (!context.memories || context.memories.length === 0) {
          return {
            content: [{
              type: 'text',
              text: `No relevant memories found for: "${query}"`
            }]
          };
        }
        
        const formatted = context.memories.map((mem, i) => {
          return `**[${i + 1}]** ${mem.type || 'note'}
${mem.content}
*Relevance: ${(mem.similarity * 100).toFixed(1)}%*`;
        }).join('\n\n---\n\n');
        
        return {
          content: [{
            type: 'text',
            text: `📚 **Relevant Context for: "${query}"**

${formatted}

${context.patterns?.length > 0 ? `\n**Related Patterns:** ${context.patterns.length} found` : ''}`
          }]
        };
      }

      case 'track_decision': {
        const { decision, reasoning, alternatives_considered = [], impact = '' } = args;
        
        const decisionMemory = {
          content: `Decision: ${decision}\n\nReasoning: ${reasoning}\n\nAlternatives: ${alternatives_considered.join(', ')}\n\nExpected impact: ${impact}`,
          type: 'decision',
          category: 'decision',
          importance: 'high',
          metadata: {
            alternatives: alternatives_considered,
            impact,
            timestamp: new Date().toISOString()
          },
          rationale: 'Important decision with documented reasoning'
        };
        
        const id = memoryManager.addToPending(decisionMemory);
        
        return {
          content: [{
            type: 'text',
            text: `🎯 **Decision Tracked** (ID: ${id})

**Decision:** ${decision}
**Reasoning:** ${reasoning}
**Alternatives:** ${alternatives_considered.join(', ') || 'None listed'}
**Expected Impact:** ${impact}

This decision has been proposed for storage. Confirm with memory_id: "${id}"`
          }]
        };
      }

      case 'remember_error_and_fix': {
        const { error, solution, context = '', prevention = '' } = args;
        
        const errorMemory = {
          content: `Error: ${error}\n\nSolution: ${solution}\n\nContext: ${context}\n\nPrevention: ${prevention}`,
          type: 'error_fix',
          category: 'error_fix',
          importance: 'high',
          metadata: {
            error_message: error,
            solution_applied: solution,
            context,
            prevention_tips: prevention,
            timestamp: new Date().toISOString()
          },
          rationale: 'Error and solution for future reference'
        };
        
        const id = memoryManager.addToPending(errorMemory);
        
        return {
          content: [{
            type: 'text',
            text: `🔧 **Error & Fix Recorded** (ID: ${id})

**Error:** ${error}
**Solution:** ${solution}
${context ? `**Context:** ${context}` : ''}
${prevention ? `**Prevention:** ${prevention}` : ''}

This error/fix pair has been proposed for storage. Confirm with memory_id: "${id}"`
          }]
        };
      }

      case 'session_summary': {
        const { topics_covered, problems_solved = [], key_insights = [], next_steps = [] } = args;
        
        const duration = Date.now() - memoryManager.sessionStartTime;
        const durationMinutes = Math.floor(duration / 60000);
        
        const summaryContent = `Session Summary (${new Date().toISOString()})

Duration: ${durationMinutes} minutes
Topics: ${topics_covered.join(', ')}
${problems_solved.length > 0 ? `\nProblems Solved:\n${problems_solved.map(p => `- ${p}`).join('\n')}` : ''}
${key_insights.length > 0 ? `\nKey Insights:\n${key_insights.map(i => `- ${i}`).join('\n')}` : ''}
${next_steps.length > 0 ? `\nNext Steps:\n${next_steps.map(s => `- ${s}`).join('\n')}` : ''}`;
        
        const summaryMemory = {
          content: summaryContent,
          type: 'note',
          category: 'summary',
          importance: 'medium',
          metadata: {
            session_type: 'summary',
            duration_minutes: durationMinutes,
            topics: topics_covered,
            problems_solved,
            insights: key_insights,
            next_steps,
            memories_created: memoryManager.sessionMemories.length
          },
          rationale: 'Session summary for future reference'
        };
        
        const id = memoryManager.addToPending(summaryMemory);
        
        return {
          content: [{
            type: 'text',
            text: `📋 **Session Summary Created** (ID: ${id})

**Duration:** ${durationMinutes} minutes
**Topics:** ${topics_covered.length}
**Problems Solved:** ${problems_solved.length}
**Key Insights:** ${key_insights.length}
**Memories Created:** ${memoryManager.sessionMemories.length}

Summary has been proposed for storage. Confirm with memory_id: "${id}"`
          }]
        };
      }

      case 'check_memory_conflicts': {
        const { new_information, category = null } = args;
        
        // Search for similar memories
        const results = await memoryStore.search(new_information, {
          limit: 5,
          threshold: 0.7
        });
        
        const conflicts = results.filter(mem => {
          if (category && mem.type !== category) return false;
          
          // Check for potential conflicts (simplified logic)
          const memLower = mem.content.toLowerCase();
          const newLower = new_information.toLowerCase();
          
          // Look for contradictory terms
          const contradictions = [
            ['always', 'never'],
            ['required', 'optional'],
            ['must', 'should not'],
            ['enabled', 'disabled'],
            ['true', 'false']
          ];
          
          for (const [term1, term2] of contradictions) {
            if ((memLower.includes(term1) && newLower.includes(term2)) ||
                (memLower.includes(term2) && newLower.includes(term1))) {
              return true;
            }
          }
          
          return false;
        });
        
        if (conflicts.length === 0) {
          return {
            content: [{
              type: 'text',
              text: '✅ No conflicting information found. Safe to store.'
            }]
          };
        }
        
        const conflictList = conflicts.map((mem, i) => {
          return `**[${i + 1}]** ${mem.type}
${mem.content}
*Stored: ${new Date(mem.timestamp).toLocaleDateString()}*`;
        }).join('\n\n---\n\n');
        
        return {
          content: [{
            type: 'text',
            text: `⚠️ **Potential Conflicts Found**

New Information: "${new_information}"

Potentially Conflicting Memories:

${conflictList}

Consider updating or clarifying the existing memories before storing new information.`
          }]
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    console.error(`[MCP Memory] Error executing tool ${name}:`, error);
    return {
      content: [{
        type: 'text',
        text: `Error: ${error.message}`
      }]
    };
  }
});

// Initialize and start the server
async function main() {
  console.error('[MCP Memory] Starting Smart Memory Server v2.0.0');
  
  // Initialize memory system
  await initializeMemorySystem();
  
  // Start the server
  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  console.error('[MCP Memory] Server running on stdio');
}

main().catch((error) => {
  console.error('[MCP Memory] Fatal error:', error);
  process.exit(1);
});