import winston from 'winston';
import contextRetriever from '../memory/context-retriever.js';
import memoryRanker from '../memory/memory-ranker.js';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class ContextInjector {
  constructor() {
    this.templates = new Map();
    this.loadDefaultTemplates();
  }

  /**
   * Load default injection templates
   */
  loadDefaultTemplates() {
    // Default context template
    this.templates.set('default', {
      prefix: '## Relevant Context\n',
      itemTemplate: '- {content}\n',
      suffix: '\n## Your Query\n',
      maxLength: 2000
    });

    // Code context template
    this.templates.set('code', {
      prefix: '## Related Code Context\n```\n',
      itemTemplate: '{content}\n---\n',
      suffix: '```\n\n## Your Request\n',
      maxLength: 3000
    });

    // Documentation context template
    this.templates.set('documentation', {
      prefix: '## Relevant Documentation\n',
      itemTemplate: '### {title}\n{content}\n\n',
      suffix: '## Your Question\n',
      maxLength: 2500
    });

    // Conversation context template
    this.templates.set('conversation', {
      prefix: '## Previous Context\n',
      itemTemplate: '**{type}**: {content}\n\n',
      suffix: '## Current Message\n',
      maxLength: 2000
    });
  }

  /**
   * Inject context into prompt
   */
  async injectContext(prompt, options = {}) {
    const {
      templateName = 'default',
      maxItems = 10,
      contextType = 'all',
      includePatterns = true
    } = options;

    try {
      // Retrieve context
      const context = await contextRetriever.retrieveWithPatterns(prompt, {
        maxItems: maxItems * 2, // Get more for ranking
        contextType,
        includeMetadata: true
      });

      // Rank and select best items
      const ranked = memoryRanker.rank(context.items, prompt);
      const selected = ranked.slice(0, maxItems);

      // Diversify to avoid redundancy
      const diverse = memoryRanker.diversify(selected, 0.85);

      // Format with template
      const formatted = this.formatWithTemplate(
        prompt,
        diverse,
        context.patterns,
        templateName
      );

      logger.info('Context injected', {
        prompt: prompt.substring(0, 50),
        contextItems: diverse.length,
        template: templateName
      });

      return {
        augmentedPrompt: formatted,
        metadata: {
          originalPrompt: prompt,
          contextItems: diverse.length,
          patterns: context.patterns?.length || 0,
          template: templateName
        }
      };
    } catch (error) {
      logger.error('Failed to inject context', { error: error.message });
      return {
        augmentedPrompt: prompt,
        metadata: {
          error: error.message
        }
      };
    }
  }

  /**
   * Format context with template
   */
  formatWithTemplate(prompt, items, patterns, templateName) {
    const template = this.templates.get(templateName) || this.templates.get('default');
    
    let result = '';
    let currentLength = 0;

    // Add prefix
    if (template.prefix) {
      result += template.prefix;
      currentLength += template.prefix.length;
    }

    // Add context items
    for (const item of items) {
      const formatted = this.formatItem(item, template.itemTemplate);
      
      if (currentLength + formatted.length > template.maxLength) {
        break;
      }

      result += formatted;
      currentLength += formatted.length;
    }

    // Add pattern suggestions if available
    if (patterns && patterns.length > 0) {
      const patternSection = this.formatPatterns(patterns);
      if (currentLength + patternSection.length <= template.maxLength) {
        result += patternSection;
        currentLength += patternSection.length;
      }
    }

    // Add suffix
    if (template.suffix) {
      result += template.suffix;
    }

    // Add original prompt
    result += prompt;

    return result;
  }

  /**
   * Format a single context item
   */
  formatItem(item, template) {
    let formatted = template;

    // Replace placeholders
    formatted = formatted.replace('{content}', item.content || '');
    formatted = formatted.replace('{title}', item.title || 'Context');
    formatted = formatted.replace('{type}', item.type || 'context');
    formatted = formatted.replace('{similarity}', (item.similarity || 0).toFixed(2));
    
    // Add metadata if present
    if (item.filePaths && item.filePaths.length > 0) {
      formatted = formatted.replace('{files}', item.filePaths.join(', '));
    }

    return formatted;
  }

  /**
   * Format pattern suggestions
   */
  formatPatterns(patterns) {
    if (!patterns || patterns.length === 0) return '';

    let result = '\n## Suggested Patterns\n';

    for (const pattern of patterns.slice(0, 3)) {
      result += `- **${pattern.pattern_name}**: `;
      result += `${pattern.occurrence_count} uses, `;
      result += `${(pattern.success_rate * 100).toFixed(0)}% success\n`;
    }

    result += '\n';
    return result;
  }

  /**
   * Create custom injection template
   */
  createTemplate(name, template) {
    this.templates.set(name, {
      prefix: template.prefix || '',
      itemTemplate: template.itemTemplate || '{content}\n',
      suffix: template.suffix || '',
      maxLength: template.maxLength || 2000
    });

    logger.info('Custom template created', { name });
  }

  /**
   * Inject inline context (for streaming)
   */
  async injectInline(prompt, options = {}) {
    const {
      position = 'prefix', // prefix, suffix, or inline
      marker = '[[CONTEXT]]',
      maxItems = 5
    } = options;

    try {
      // Get context quickly
      const context = await contextRetriever.retrieveContext(prompt, {
        maxItems,
        includeMetadata: false
      });

      // Format concisely
      const formatted = this.formatInline(context.items);

      // Inject based on position
      let result;
      switch (position) {
        case 'prefix':
          result = formatted + '\n\n' + prompt;
          break;
        
        case 'suffix':
          result = prompt + '\n\n' + formatted;
          break;
        
        case 'inline':
          result = prompt.replace(marker, formatted);
          break;
        
        default:
          result = prompt;
      }

      return result;
    } catch (error) {
      logger.error('Failed to inject inline context', { error: error.message });
      return prompt;
    }
  }

  /**
   * Format context for inline injection
   */
  formatInline(items) {
    if (!items || items.length === 0) {
      return '[No relevant context found]';
    }

    const formatted = items.map((item, index) => 
      `[${index + 1}] ${item.content.substring(0, 100)}...`
    ).join('\n');

    return `[Context: ${items.length} relevant items]\n${formatted}`;
  }

  /**
   * Inject context for specific file operations
   */
  async injectFileContext(prompt, filePath, options = {}) {
    const {
      includeRelated = true,
      maxRelated = 3
    } = options;

    try {
      // Get context specific to this file
      const fileContext = await contextRetriever.retrieveContext(
        `${prompt} file:${filePath}`,
        {
          maxItems: 5,
          contextType: 'code'
        }
      );

      let result = `## File: ${filePath}\n`;

      // Add file-specific context
      if (fileContext.items.length > 0) {
        result += '### Previous interactions with this file:\n';
        for (const item of fileContext.items) {
          result += `- ${item.content.substring(0, 100)}...\n`;
        }
        result += '\n';
      }

      // Add related files if requested
      if (includeRelated) {
        const related = await this.findRelatedFiles(filePath, maxRelated);
        if (related.length > 0) {
          result += '### Related files:\n';
          for (const file of related) {
            result += `- ${file}\n`;
          }
          result += '\n';
        }
      }

      result += '## Your request:\n' + prompt;

      return result;
    } catch (error) {
      logger.error('Failed to inject file context', { error: error.message });
      return prompt;
    }
  }

  /**
   * Find related files
   */
  async findRelatedFiles(filePath, maxFiles = 3) {
    // Simple implementation - would query memory store for files
    // mentioned together with this file
    return [];
  }

  /**
   * Get available templates
   */
  getTemplates() {
    return Array.from(this.templates.keys());
  }

  /**
   * Get template details
   */
  getTemplate(name) {
    return this.templates.get(name);
  }
}

export default new ContextInjector();