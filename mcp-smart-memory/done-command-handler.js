/**
 * /done Command Handler for Claude Desktop
 * Integrates with smart-memory MCP server for thread completion and memory extraction
 */

class DoneCommandHandler {
  constructor(memoryStore) {
    this.memoryStore = memoryStore;
    this.pendingMemories = new Map();
  }

  /**
   * Check if a message is the /done command
   */
  isDoneCommand(message) {
    return message && message.trim().toLowerCase() === '/done';
  }

  /**
   * Check for quick options like /done all or /done skip
   */
  parseQuickCommand(message) {
    const lower = message.trim().toLowerCase();
    if (lower === '/done all') return { command: 'all' };
    if (lower === '/done skip') return { command: 'skip' };
    if (lower.startsWith('/done ')) {
      const args = lower.substring(6).trim();
      return { command: 'custom', args };
    }
    return { command: 'review' };
  }

  /**
   * Analyze conversation for valuable information
   */
  async analyzeConversation(conversation) {
    const patterns = {
      solution: /(?:fixed|solved|solution|resolved|worked|working now)[\s\S]{0,200}/gi,
      configuration: /(?:config|setting|path|url|endpoint|token|key|variable|env)[\s\S]{0,200}/gi,
      decision: /(?:decided|chose|selected|will use|going with|opted for)[\s\S]{0,200}/gi,
      error_fix: /(?:error|failed|issue|problem|bug|crash)[\s\S]{0,200}(?:fixed|solved|resolved|workaround)/gi,
      workflow: /(?:step|process|procedure|workflow|sequence|order)[\s\S]{0,200}/gi,
      insight: /(?:important|critical|key|essential|remember|note)[\s\S]{0,200}/gi
    };

    const findings = [];
    const text = conversation.join('\n');
    
    for (const [category, pattern] of Object.entries(patterns)) {
      const matches = text.match(pattern);
      if (matches) {
        matches.forEach(match => {
          // Calculate importance
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
      const exists = acc.find(f => 
        f.content.substring(0, 50) === curr.content.substring(0, 50)
      );
      if (!exists) acc.push(curr);
      return acc;
    }, []);
    
    // Return top 5 most important findings
    return unique
      .sort((a, b) => {
        const importanceOrder = { critical: 4, high: 3, medium: 2, low: 1 };
        return importanceOrder[b.importance] - importanceOrder[a.importance];
      })
      .slice(0, 5);
  }

  /**
   * Generate memory proposals from findings
   */
  generateProposals(findings) {
    return findings.map((finding, index) => {
      const id = `done-${Date.now()}-${index}`;
      const proposal = {
        id,
        category: finding.category,
        content: finding.content,
        importance: finding.importance,
        rationale: this.getRationale(finding.category, finding.content)
      };
      this.pendingMemories.set(id, proposal);
      return proposal;
    });
  }

  /**
   * Get rationale for a finding based on category
   */
  getRationale(category, content) {
    const rationales = {
      solution: 'Working solution for future reference',
      configuration: 'Important configuration to remember',
      decision: 'Strategic decision with context',
      error_fix: 'Error and fix for troubleshooting',
      workflow: 'Repeatable process or workflow',
      insight: 'Key insight or learning'
    };
    return rationales[category] || 'Valuable information to remember';
  }

  /**
   * Format proposals for display
   */
  formatProposals(proposals) {
    if (!proposals || proposals.length === 0) {
      return "📝 No significant information found to save from this thread.";
    }

    let output = "📝 **Thread Review Complete**\n\n";
    output += `Found ${proposals.length} items worth remembering:\n\n`;
    
    proposals.forEach((prop, index) => {
      output += `**${index + 1}. [${prop.importance.toUpperCase()}] ${this.formatCategory(prop.category)}**\n`;
      output += `\`\`\`\n${prop.content.substring(0, 200)}${prop.content.length > 200 ? '...' : ''}\n\`\`\`\n`;
      output += `*${prop.rationale}*\n`;
      output += `→ **Save?** (Y/n/edit) | ID: \`${prop.id.substring(0, 8)}\`\n\n`;
    });
    
    output += "---\n";
    output += "**Quick Options:**\n";
    output += "- `all` - Save all memories\n";
    output += "- `1 2` - Save specific items (by number)\n";
    output += "- `edit 3` - Modify item 3 before saving\n";
    output += "- `none` - Skip all memories\n";
    
    return output;
  }

  /**
   * Format category name for display
   */
  formatCategory(category) {
    const formatted = {
      solution: 'Solution',
      configuration: 'Configuration',
      decision: 'Decision',
      error_fix: 'Error Fix',
      workflow: 'Workflow',
      insight: 'Insight'
    };
    return formatted[category] || category;
  }

  /**
   * Process user response to proposals
   */
  async processUserResponse(response, proposals) {
    const lower = response.toLowerCase().trim();
    
    // Handle quick responses
    if (lower === 'all') {
      return await this.saveAllProposals(proposals);
    }
    
    if (lower === 'none' || lower === 'skip') {
      return "⏭️ All memories skipped.";
    }
    
    // Handle numbered selections (e.g., "1 2 4")
    const numbers = lower.match(/\d+/g);
    if (numbers) {
      const selected = numbers
        .map(n => parseInt(n) - 1)
        .filter(i => i >= 0 && i < proposals.length)
        .map(i => proposals[i]);
      
      if (selected.length > 0) {
        return await this.saveSelectedProposals(selected);
      }
    }
    
    // Handle edit command
    if (lower.startsWith('edit ')) {
      const num = parseInt(lower.substring(5)) - 1;
      if (num >= 0 && num < proposals.length) {
        return this.requestEdit(proposals[num]);
      }
    }
    
    return "❓ Unrecognized response. Please use: all, none, numbers (1 2), or edit N";
  }

  /**
   * Save all proposals
   */
  async saveAllProposals(proposals) {
    const results = [];
    for (const proposal of proposals) {
      try {
        const result = await this.memoryStore.store({
          content: proposal.content,
          type: proposal.category,
          category: proposal.category,
          importance: proposal.importance,
          metadata: {
            source: 'done_command',
            rationale: proposal.rationale,
            timestamp: new Date().toISOString()
          }
        });
        results.push({ success: true, category: proposal.category });
      } catch (error) {
        results.push({ success: false, error: error.message });
      }
    }
    
    const saved = results.filter(r => r.success).length;
    return `✅ Saved ${saved}/${proposals.length} memories successfully!`;
  }

  /**
   * Save selected proposals
   */
  async saveSelectedProposals(selected) {
    const results = [];
    for (const proposal of selected) {
      try {
        await this.memoryStore.store({
          content: proposal.content,
          type: proposal.category,
          category: proposal.category,
          importance: proposal.importance,
          metadata: {
            source: 'done_command',
            rationale: proposal.rationale,
            timestamp: new Date().toISOString()
          }
        });
        results.push({ success: true, category: proposal.category });
      } catch (error) {
        results.push({ success: false, error: error.message });
      }
    }
    
    const saved = results.filter(r => r.success).length;
    return `✅ Saved ${saved} memories successfully!`;
  }

  /**
   * Request edit for a proposal
   */
  requestEdit(proposal) {
    return `📝 **Editing Memory**\n\nCurrent content:\n\`\`\`\n${proposal.content}\n\`\`\`\n\nPlease provide your edited version:`;
  }

  /**
   * Generate session summary
   */
  generateSessionSummary(conversation, proposals, savedCount) {
    const duration = this.estimateDuration(conversation);
    const problemsSolved = proposals.filter(p => 
      p.category === 'solution' || p.category === 'error_fix'
    ).length;
    
    return `
## ✅ **Thread Complete**

### 📊 **Session Statistics**
- **Duration**: ~${duration} minutes
- **Problems Solved**: ${problemsSolved}
- **Memories Saved**: ${savedCount}
- **Categories**: ${[...new Set(proposals.map(p => p.category))].join(', ')}

### 🎯 **Success!**
Your /done command has successfully extracted and saved valuable information from this thread.
`;
  }

  /**
   * Estimate conversation duration
   */
  estimateDuration(conversation) {
    // Rough estimate: 150 words per minute reading, 40 words per minute typing
    const totalWords = conversation.join(' ').split(' ').length;
    return Math.max(5, Math.round(totalWords / 100));
  }

  /**
   * Main handler for /done command
   */
  async handleDoneCommand(conversation) {
    try {
      // Analyze conversation
      const findings = await this.analyzeConversation(conversation);
      
      if (findings.length === 0) {
        return "📝 Thread review complete. No significant information found to save.";
      }
      
      // Generate proposals
      const proposals = this.generateProposals(findings);
      
      // Return formatted proposals for user review
      return this.formatProposals(proposals);
      
    } catch (error) {
      console.error('Error in /done command handler:', error);
      return `❌ Error processing /done command: ${error.message}`;
    }
  }
}

export default DoneCommandHandler;