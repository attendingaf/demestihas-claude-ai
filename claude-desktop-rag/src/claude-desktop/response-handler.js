import winston from 'winston';
import memoryStore from '../memory/memory-store.js';
import patternDetector from '../patterns/pattern-detector.js';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class ResponseHandler {
  constructor() {
    this.processors = new Map();
    this.metrics = {
      processed: 0,
      errors: 0,
      patterns: 0
    };
    this.loadDefaultProcessors();
  }

  /**
   * Load default response processors
   */
  loadDefaultProcessors() {
    // Code response processor
    this.processors.set('code', async (response) => {
      return this.processCodeResponse(response);
    });

    // Error response processor
    this.processors.set('error', async (response) => {
      return this.processErrorResponse(response);
    });

    // Documentation processor
    this.processors.set('documentation', async (response) => {
      return this.processDocumentationResponse(response);
    });

    // General processor
    this.processors.set('general', async (response) => {
      return this.processGeneralResponse(response);
    });
  }

  /**
   * Handle Claude's response
   */
  async handleResponse(response, context = {}) {
    const {
      prompt,
      type = 'general',
      metadata = {},
      storeInMemory = true
    } = context;

    try {
      this.metrics.processed++;

      // Determine response type if not specified
      const responseType = type || this.detectResponseType(response);

      // Process with appropriate processor
      const processor = this.processors.get(responseType) || this.processors.get('general');
      const processed = await processor(response);

      // Extract metadata
      const extracted = this.extractMetadata(response, processed);

      // Store in memory if enabled
      if (storeInMemory) {
        await this.storeResponse(response, {
          ...extracted,
          prompt,
          type: responseType,
          metadata
        });
      }

      // Check for patterns
      await this.checkForPatterns(response, prompt, extracted);

      logger.info('Response handled', {
        type: responseType,
        length: response.length,
        extracted: Object.keys(extracted)
      });

      return {
        response,
        processed,
        extracted,
        type: responseType
      };
    } catch (error) {
      this.metrics.errors++;
      logger.error('Failed to handle response', { error: error.message });
      
      return {
        response,
        error: error.message
      };
    }
  }

  /**
   * Process code response
   */
  async processCodeResponse(response) {
    const processed = {
      codeBlocks: [],
      languages: [],
      files: [],
      commands: []
    };

    // Extract code blocks
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    let match;
    
    while ((match = codeBlockRegex.exec(response)) !== null) {
      const language = match[1] || 'plain';
      const code = match[2];
      
      processed.codeBlocks.push({
        language,
        code,
        position: match.index
      });

      if (!processed.languages.includes(language)) {
        processed.languages.push(language);
      }
    }

    // Extract file paths
    const fileRegex = /(?:^|\s)((?:\/|\.\/|\.\.\/)?[\w.-]+(?:\/[\w.-]+)*\.\w+)/gm;
    while ((match = fileRegex.exec(response)) !== null) {
      if (!processed.files.includes(match[1])) {
        processed.files.push(match[1]);
      }
    }

    // Extract commands
    const commandRegex = /^\$ (.+)$/gm;
    while ((match = commandRegex.exec(response)) !== null) {
      processed.commands.push(match[1]);
    }

    return processed;
  }

  /**
   * Process error response
   */
  async processErrorResponse(response) {
    const processed = {
      errorType: null,
      errorMessage: null,
      stackTrace: null,
      suggestions: []
    };

    // Detect error patterns
    const errorPatterns = [
      /Error:\s*(.+)/i,
      /Exception:\s*(.+)/i,
      /Failed:\s*(.+)/i,
      /Warning:\s*(.+)/i
    ];

    for (const pattern of errorPatterns) {
      const match = response.match(pattern);
      if (match) {
        processed.errorMessage = match[1];
        break;
      }
    }

    // Extract stack trace if present
    const stackMatch = response.match(/Stack trace:?\n([\s\S]+?)(?:\n\n|$)/i);
    if (stackMatch) {
      processed.stackTrace = stackMatch[1];
    }

    // Extract suggestions
    const suggestionRegex = /(?:Try|Consider|You (?:can|should|might)):\s*(.+)/gi;
    let match;
    while ((match = suggestionRegex.exec(response)) !== null) {
      processed.suggestions.push(match[1]);
    }

    return processed;
  }

  /**
   * Process documentation response
   */
  async processDocumentationResponse(response) {
    const processed = {
      sections: [],
      links: [],
      examples: [],
      reference_ids: []
    };

    // Extract sections (markdown headers)
    const sectionRegex = /^(#{1,6})\s+(.+)$/gm;
    let match;
    while ((match = sectionRegex.exec(response)) !== null) {
      processed.sections.push({
        level: match[1].length,
        title: match[2],
        position: match.index
      });
    }

    // Extract links
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    while ((match = linkRegex.exec(response)) !== null) {
      processed.links.push({
        text: match[1],
        url: match[2]
      });
    }

    // Extract examples
    const exampleRegex = /(?:Example|Sample):\s*\n([\s\S]+?)(?:\n\n|```|$)/gi;
    while ((match = exampleRegex.exec(response)) !== null) {
      processed.examples.push(match[1].trim());
    }

    // Extract references
    const refRegex = /(?:See|Ref|Reference):\s*(.+)/gi;
    while ((match = refRegex.exec(response)) !== null) {
      processed.reference_ids.push(match[1]);
    }

    return processed;
  }

  /**
   * Process general response
   */
  async processGeneralResponse(response) {
    const processed = {
      sentences: [],
      keywords: [],
      entities: [],
      sentiment: 'neutral'
    };

    // Split into sentences
    processed.sentences = response
      .split(/[.!?]+/)
      .map(s => s.trim())
      .filter(s => s.length > 0);

    // Extract potential keywords (simple approach)
    const words = response.toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length > 4);

    const wordCounts = {};
    for (const word of words) {
      wordCounts[word] = (wordCounts[word] || 0) + 1;
    }

    processed.keywords = Object.entries(wordCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([word]) => word);

    // Simple sentiment detection
    const positiveWords = ['good', 'great', 'excellent', 'success', 'perfect'];
    const negativeWords = ['bad', 'error', 'fail', 'wrong', 'issue'];

    const lowerResponse = response.toLowerCase();
    const positiveCount = positiveWords.filter(w => lowerResponse.includes(w)).length;
    const negativeCount = negativeWords.filter(w => lowerResponse.includes(w)).length;

    if (positiveCount > negativeCount) {
      processed.sentiment = 'positive';
    } else if (negativeCount > positiveCount) {
      processed.sentiment = 'negative';
    }

    return processed;
  }

  /**
   * Detect response type
   */
  detectResponseType(response) {
    // Check for code blocks
    if (response.includes('```')) {
      return 'code';
    }

    // Check for error indicators
    if (/error|exception|failed|warning/i.test(response)) {
      return 'error';
    }

    // Check for documentation indicators
    if (/^#+ /m.test(response) || /\[.+\]\(.+\)/.test(response)) {
      return 'documentation';
    }

    return 'general';
  }

  /**
   * Extract metadata from response
   */
  extractMetadata(response, processed) {
    const metadata = {
      length: response.length,
      type: this.detectResponseType(response),
      timestamp: new Date().toISOString()
    };

    // Add processed data
    if (processed.codeBlocks) {
      metadata.codeBlocks = processed.codeBlocks.length;
      metadata.languages = processed.languages;
    }

    if (processed.files) {
      metadata.files = processed.files;
    }

    if (processed.commands) {
      metadata.commands = processed.commands;
    }

    if (processed.errorMessage) {
      metadata.hasError = true;
      metadata.errorMessage = processed.errorMessage;
    }

    if (processed.links) {
      metadata.links = processed.links.length;
    }

    if (processed.sentiment) {
      metadata.sentiment = processed.sentiment;
    }

    return metadata;
  }

  /**
   * Store response in memory
   */
  async storeResponse(response, context) {
    try {
      await memoryStore.store(response, {
        interactionType: 'assistant_response',
        filePaths: context.files || [],
        toolChain: context.commands || [],
        metadata: {
          ...context.metadata,
          responseType: context.type,
          prompt: context.prompt,
          processed: true
        },
        successScore: context.hasError ? 0.5 : 1.0
      });
    } catch (error) {
      logger.error('Failed to store response', { error: error.message });
    }
  }

  /**
   * Check for patterns in response
   */
  async checkForPatterns(response, prompt, extracted) {
    try {
      await patternDetector.recordInteraction({
        content: `Q: ${prompt}\nA: ${response}`,
        filePaths: extracted.files || [],
        toolChain: extracted.commands || [],
        success: !extracted.hasError,
        metadata: extracted
      });

      this.metrics.patterns++;
    } catch (error) {
      logger.error('Failed to check for patterns', { error: error.message });
    }
  }

  /**
   * Post-process response for output
   */
  async postProcess(response, options = {}) {
    const {
      format = 'text', // text, markdown, json
      maxLength = null,
      highlight = []
    } = options;

    let processed = response;

    // Apply format
    switch (format) {
      case 'markdown':
        processed = this.formatAsMarkdown(processed);
        break;
      
      case 'json':
        processed = this.formatAsJson(processed);
        break;
      
      default:
        // Keep as text
        break;
    }

    // Apply highlighting
    if (highlight.length > 0) {
      processed = this.applyHighlighting(processed, highlight);
    }

    // Truncate if needed
    if (maxLength && processed.length > maxLength) {
      processed = processed.substring(0, maxLength) + '...';
    }

    return processed;
  }

  /**
   * Format as markdown
   */
  formatAsMarkdown(text) {
    // Ensure proper markdown formatting
    // This is a simple implementation
    return text;
  }

  /**
   * Format as JSON
   */
  formatAsJson(text) {
    try {
      // Try to extract JSON if present
      const jsonMatch = text.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.stringify(JSON.parse(jsonMatch[0]), null, 2);
      }
    } catch (error) {
      // Not valid JSON
    }
    
    return JSON.stringify({ content: text }, null, 2);
  }

  /**
   * Apply highlighting
   */
  applyHighlighting(text, keywords) {
    let highlighted = text;
    
    for (const keyword of keywords) {
      const regex = new RegExp(`(${keyword})`, 'gi');
      highlighted = highlighted.replace(regex, '**$1**');
    }

    return highlighted;
  }

  /**
   * Get metrics
   */
  getMetrics() {
    return { ...this.metrics };
  }

  /**
   * Reset metrics
   */
  resetMetrics() {
    this.metrics = {
      processed: 0,
      errors: 0,
      patterns: 0
    };
  }
}

export default new ResponseHandler();