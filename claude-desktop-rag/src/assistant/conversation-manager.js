import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';
import { config } from '../../config/rag-config.js';
import memoryStoreV2 from '../memory/memory-store-v2.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class ConversationManager {
  constructor() {
    this.conversations = new Map();
    this.activeConversation = null;
    this.referenceResolver = new ReferenceResolver();
    this.contextWindow = 10; // Number of turns to maintain
    this.metrics = {
      totalConversations: 0,
      avgTurnsPerConversation: 0,
      contextPreservationRate: 1.0,
      referenceResolutionRate: 0
    };
  }

  async initialize() {
    try {
      // Load recent conversations
      await this.loadRecentConversations();
      
      // Initialize reference resolver
      await this.referenceResolver.initialize();
      
      logger.info('Conversation Manager initialized');
    } catch (error) {
      logger.error('Failed to initialize Conversation Manager', { 
        error: error.message 
      });
      throw error;
    }
  }

  async startConversation(initialContext = {}) {
    const conversationId = uuidv4();
    
    const conversation = {
      id: conversationId,
      startTime: Date.now(),
      turns: [],
      context: {
        ...initialContext,
        entities: new Map(),
        topics: [],
        references: new Map()
      },
      state: 'active',
      metadata: {
        userId: config.user.id,
        projectId: config.project.id
      }
    };
    
    this.conversations.set(conversationId, conversation);
    this.activeConversation = conversationId;
    this.metrics.totalConversations++;
    
    logger.debug('Conversation started', { id: conversationId });
    
    return conversationId;
  }

  async addTurn(input, response, conversationId = null) {
    const convId = conversationId || this.activeConversation;
    
    if (!convId) {
      // Start new conversation if none exists
      await this.startConversation();
    }
    
    const conversation = this.conversations.get(convId || this.activeConversation);
    
    if (!conversation) {
      throw new Error('No active conversation');
    }
    
    // Resolve references in input
    const resolvedInput = await this.resolveReferences(input, conversation);
    
    // Create turn object
    const turn = {
      id: uuidv4(),
      timestamp: Date.now(),
      input: {
        original: input,
        resolved: resolvedInput,
        entities: await this.extractEntities(resolvedInput)
      },
      response: response,
      context: await this.captureContext(conversation)
    };
    
    // Add turn to conversation
    conversation.turns.push(turn);
    
    // Update conversation context
    await this.updateContext(conversation, turn);
    
    // Maintain context window
    if (conversation.turns.length > this.contextWindow) {
      await this.compressOldTurns(conversation);
    }
    
    // Store turn in memory
    await this.storeTurn(turn, conversation);
    
    // Update metrics
    this.updateMetrics(conversation);
    
    logger.debug('Turn added to conversation', { 
      conversationId: conversation.id,
      turnNumber: conversation.turns.length 
    });
    
    return turn;
  }

  async resolveReferences(input, conversation) {
    const references = this.referenceResolver.findReferences(input);
    
    if (references.length === 0) {
      return input;
    }
    
    let resolved = input;
    
    for (const reference of references) {
      const resolution = await this.referenceResolver.resolve(
        reference,
        conversation
      );
      
      if (resolution) {
        resolved = resolved.replace(reference.text, resolution);
        
        // Track resolution
        conversation.context.references.set(reference.text, resolution);
      }
    }
    
    logger.debug('References resolved', { 
      original: input,
      resolved,
      references: references.length 
    });
    
    return resolved;
  }

  async extractEntities(input) {
    const entities = {
      files: [],
      functions: [],
      variables: [],
      concepts: []
    };
    
    // Extract file references
    const filePattern = /(?:file|in|from)\s+([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)/gi;
    let match;
    while ((match = filePattern.exec(input)) !== null) {
      entities.files.push(match[1]);
    }
    
    // Extract function references
    const funcPattern = /(?:function|method|def)\s+(\w+)/gi;
    while ((match = funcPattern.exec(input)) !== null) {
      entities.functions.push(match[1]);
    }
    
    // Extract variable references
    const varPattern = /(?:variable|const|let|var)\s+(\w+)/gi;
    while ((match = varPattern.exec(input)) !== null) {
      entities.variables.push(match[1]);
    }
    
    return entities;
  }

  async captureContext(conversation) {
    const recentTurns = conversation.turns.slice(-3);
    
    return {
      recentInputs: recentTurns.map(t => t.input.resolved),
      recentResponses: recentTurns.map(t => t.response?.content || ''),
      activeEntities: Array.from(conversation.context.entities.keys()),
      currentTopics: conversation.context.topics.slice(-3)
    };
  }

  async updateContext(conversation, turn) {
    // Update entities
    for (const file of turn.input.entities.files) {
      conversation.context.entities.set(file, {
        type: 'file',
        lastMentioned: turn.timestamp
      });
    }
    
    for (const func of turn.input.entities.functions) {
      conversation.context.entities.set(func, {
        type: 'function',
        lastMentioned: turn.timestamp
      });
    }
    
    // Update topics
    const topics = await this.extractTopics(turn.input.resolved);
    conversation.context.topics.push(...topics);
    
    // Keep only recent topics
    if (conversation.context.topics.length > 10) {
      conversation.context.topics = conversation.context.topics.slice(-10);
    }
    
    // Clean old entities
    const cutoff = Date.now() - (5 * 60 * 1000); // 5 minutes
    for (const [key, entity] of conversation.context.entities) {
      if (entity.lastMentioned < cutoff) {
        conversation.context.entities.delete(key);
      }
    }
  }

  async extractTopics(input) {
    // Simple topic extraction based on keywords
    const topics = [];
    
    const topicKeywords = {
      'testing': ['test', 'testing', 'spec', 'assertion'],
      'debugging': ['debug', 'error', 'bug', 'issue', 'problem'],
      'refactoring': ['refactor', 'improve', 'optimize', 'clean'],
      'documentation': ['document', 'docs', 'comment', 'readme'],
      'deployment': ['deploy', 'build', 'release', 'production'],
      'performance': ['performance', 'speed', 'optimize', 'slow']
    };
    
    const lowerInput = input.toLowerCase();
    
    for (const [topic, keywords] of Object.entries(topicKeywords)) {
      if (keywords.some(keyword => lowerInput.includes(keyword))) {
        topics.push(topic);
      }
    }
    
    return topics;
  }

  async compressOldTurns(conversation) {
    // Keep full detail for recent turns
    const recentTurns = conversation.turns.slice(-this.contextWindow);
    const oldTurns = conversation.turns.slice(0, -this.contextWindow);
    
    // Compress old turns
    const compressed = oldTurns.map(turn => ({
      id: turn.id,
      timestamp: turn.timestamp,
      summary: this.summarizeTurn(turn)
    }));
    
    // Store compressed history
    conversation.compressedHistory = compressed;
    conversation.turns = recentTurns;
    
    logger.debug('Compressed old turns', { 
      compressed: compressed.length,
      active: recentTurns.length 
    });
  }

  summarizeTurn(turn) {
    return {
      input: turn.input.original.substring(0, 50),
      response: turn.response?.type || 'unknown',
      entities: Object.keys(turn.input.entities).length
    };
  }

  async storeTurn(turn, conversation) {
    await memoryStoreV2.storeMemory(JSON.stringify(turn), {
      type: 'conversation_turn',
      conversationId: conversation.id,
      turnNumber: conversation.turns.length,
      timestamp: turn.timestamp
    });
  }

  async loadRecentConversations() {
    try {
      const conversations = await memoryStoreV2.searchMemories('conversation', {
        limit: 10,
        filter: { type: 'conversation_turn' }
      });
      
      // Group by conversation ID
      const grouped = {};
      
      for (const conv of conversations) {
        const convId = conv.metadata?.conversationId;
        
        if (convId) {
          if (!grouped[convId]) {
            grouped[convId] = [];
          }
          grouped[convId].push(JSON.parse(conv.content));
        }
      }
      
      // Reconstruct conversations
      for (const [convId, turns] of Object.entries(grouped)) {
        const conversation = {
          id: convId,
          turns: turns.sort((a, b) => a.timestamp - b.timestamp),
          context: {
            entities: new Map(),
            topics: [],
            references: new Map()
          },
          state: 'loaded'
        };
        
        this.conversations.set(convId, conversation);
      }
      
      logger.info('Loaded recent conversations', { 
        count: this.conversations.size 
      });
    } catch (error) {
      logger.error('Failed to load conversations', { 
        error: error.message 
      });
    }
  }

  updateMetrics(conversation) {
    // Update average turns
    let totalTurns = 0;
    for (const conv of this.conversations.values()) {
      totalTurns += conv.turns.length;
    }
    
    this.metrics.avgTurnsPerConversation = 
      totalTurns / this.conversations.size;
    
    // Calculate context preservation rate
    const resolved = conversation.context.references.size;
    const total = resolved + 
      conversation.turns.filter(t => 
        t.input.original !== t.input.resolved
      ).length;
    
    if (total > 0) {
      this.metrics.referenceResolutionRate = resolved / total;
    }
  }

  getConversation(conversationId = null) {
    const id = conversationId || this.activeConversation;
    return this.conversations.get(id);
  }

  getConversationHistory(conversationId = null, limit = 10) {
    const conversation = this.getConversation(conversationId);
    
    if (!conversation) return [];
    
    return conversation.turns.slice(-limit).map(turn => ({
      input: turn.input.original,
      response: turn.response?.content || '',
      timestamp: turn.timestamp
    }));
  }

  switchConversation(conversationId) {
    if (this.conversations.has(conversationId)) {
      this.activeConversation = conversationId;
      logger.debug('Switched to conversation', { id: conversationId });
      return true;
    }
    return false;
  }

  endConversation(conversationId = null) {
    const id = conversationId || this.activeConversation;
    const conversation = this.conversations.get(id);
    
    if (conversation) {
      conversation.state = 'ended';
      conversation.endTime = Date.now();
      
      // Clear from active if it was active
      if (this.activeConversation === id) {
        this.activeConversation = null;
      }
      
      logger.debug('Conversation ended', { id });
    }
  }

  getMetrics() {
    return {
      ...this.metrics,
      activeConversations: Array.from(this.conversations.values())
        .filter(c => c.state === 'active').length,
      totalTurns: Array.from(this.conversations.values())
        .reduce((sum, c) => sum + c.turns.length, 0)
    };
  }
}

class ReferenceResolver {
  constructor() {
    this.pronouns = ['it', 'this', 'that', 'these', 'those'];
    this.demonstratives = ['the', 'above', 'below', 'previous', 'last', 'current'];
  }

  async initialize() {
    // Load reference resolution patterns
    logger.debug('Reference resolver initialized');
  }

  findReferences(input) {
    const references = [];
    const words = input.toLowerCase().split(/\s+/);
    
    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      
      // Check pronouns
      if (this.pronouns.includes(word)) {
        references.push({
          type: 'pronoun',
          text: word,
          position: i,
          context: words.slice(Math.max(0, i - 2), i + 3).join(' ')
        });
      }
      
      // Check demonstratives with noun
      if (this.demonstratives.includes(word) && i < words.length - 1) {
        const phrase = `${word} ${words[i + 1]}`;
        references.push({
          type: 'demonstrative',
          text: phrase,
          position: i,
          noun: words[i + 1]
        });
      }
    }
    
    return references;
  }

  async resolve(reference, conversation) {
    if (!conversation || !conversation.turns.length) {
      return null;
    }
    
    const recentTurns = conversation.turns.slice(-3);
    
    switch (reference.type) {
      case 'pronoun':
        return this.resolvePronoun(reference, recentTurns, conversation);
        
      case 'demonstrative':
        return this.resolveDemonstrative(reference, recentTurns, conversation);
        
      default:
        return null;
    }
  }

  resolvePronoun(reference, recentTurns, conversation) {
    // Look for most recent entity
    const entities = Array.from(conversation.context.entities.entries())
      .sort((a, b) => b[1].lastMentioned - a[1].lastMentioned);
    
    if (entities.length > 0) {
      const [name, entity] = entities[0];
      
      if (reference.text === 'it' && entity.type === 'file') {
        return `the file ${name}`;
      }
      
      if (reference.text === 'it' && entity.type === 'function') {
        return `the function ${name}`;
      }
      
      return name;
    }
    
    // Look in recent responses
    for (let i = recentTurns.length - 1; i >= 0; i--) {
      const turn = recentTurns[i];
      
      if (turn.input.entities.files.length > 0) {
        return turn.input.entities.files[0];
      }
      
      if (turn.input.entities.functions.length > 0) {
        return turn.input.entities.functions[0];
      }
    }
    
    return null;
  }

  resolveDemonstrative(reference, recentTurns, conversation) {
    const noun = reference.noun;
    
    // Map common nouns to entity types
    const nounMap = {
      'file': 'files',
      'function': 'functions',
      'variable': 'variables',
      'error': 'errors',
      'code': 'code'
    };
    
    const entityType = nounMap[noun];
    
    if (!entityType) return null;
    
    // Find most recent mention of this type
    for (let i = recentTurns.length - 1; i >= 0; i--) {
      const turn = recentTurns[i];
      const entities = turn.input.entities[entityType];
      
      if (entities && entities.length > 0) {
        if (reference.text.includes('the')) {
          return entities[0];
        }
      }
    }
    
    return null;
  }
}

export default new ConversationManager();