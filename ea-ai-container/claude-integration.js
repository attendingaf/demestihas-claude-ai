/**
 * Claude Desktop Integration Bridge for EA-AI Container
 * This file provides the interface between Claude Desktop and the containerized EA-AI agent
 */

const axios = require('axios');

class EAAIBridge {
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || 'http://localhost:8080';
    this.timeout = options.timeout || 5000;

    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  // Memory operations
  async memory(operation, key, value, metadata) {
    try {
      const response = await this.client.post('/memory', {
        operation,
        key,
        value,
        metadata
      });
      return response.data;
    } catch (error) {
      console.error(`Memory operation ${operation} failed:`, error.message);
      throw error;
    }
  }

  // Route to appropriate agent
  async route(agent, query) {
    try {
      const response = await this.client.post('/route', {
        agent,
        query
      });
      return response.data;
    } catch (error) {
      console.error(`Routing to ${agent} failed:`, error.message);
      throw error;
    }
  }

  // Get family context
  async family(member) {
    try {
      const response = await this.client.get(`/family/${member}`);
      return response.data;
    } catch (error) {
      console.error(`Family context for ${member} failed:`, error.message);
      throw error;
    }
  }

  // Calendar operations
  async calendar(operation, params) {
    try {
      const response = await this.client.post('/calendar/check', {
        operation,
        params
      });
      return response.data;
    } catch (error) {
      console.error(`Calendar operation ${operation} failed:`, error.message);
      throw error;
    }
  }

  // ADHD task management
  async taskADHD(operation, task) {
    try {
      const response = await this.client.post('/task/adhd', {
        operation,
        task
      });
      return response.data;
    } catch (error) {
      console.error(`ADHD task operation ${operation} failed:`, error.message);
      throw error;
    }
  }

  // Health check
  async health() {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error.message);
      return { status: 'unhealthy', error: error.message };
    }
  }
}

// Export for use in Claude Desktop MCP tools
module.exports = EAAIBridge;

// CLI interface for testing
if (require.main === module) {
  const bridge = new EAAIBridge();

  const command = process.argv[2];
  const args = process.argv.slice(3);

  const runCommand = async () => {
    try {
      switch (command) {
        case 'health':
          const health = await bridge.health();
          console.log('Health:', JSON.stringify(health, null, 2));
          break;

        case 'memory':
          const memOp = args[0];
          const memKey = args[1];
          const memValue = args[2];
          const memResult = await bridge.memory(memOp, memKey, memValue);
          console.log('Memory result:', JSON.stringify(memResult, null, 2));
          break;

        case 'route':
          const routeAgent = args[0] || 'auto';
          const routeQuery = args.slice(1).join(' ');
          const routeResult = await bridge.route(routeAgent, routeQuery);
          console.log('Routing result:', JSON.stringify(routeResult, null, 2));
          break;

        case 'family':
          const member = args[0] || 'auto';
          const familyResult = await bridge.family(member);
          console.log('Family context:', JSON.stringify(familyResult, null, 2));
          break;

        case 'task':
          const taskOp = args[0];
          const task = args.slice(1).join(' ');
          const taskResult = await bridge.taskADHD(taskOp, task);
          console.log('Task result:', JSON.stringify(taskResult, null, 2));
          break;

        default:
          console.log('Usage: node claude-integration.js <command> [args]');
          console.log('Commands:');
          console.log('  health                        - Check container health');
          console.log('  memory <op> <key> [value]     - Memory operations (set/get/search/persist)');
          console.log('  route [agent] <query>         - Route to agent (auto/pluma/huata/lyco/kairos)');
          console.log('  family [member]               - Get family context (auto/mene/cindy)');
          console.log('  task <op> <task>              - ADHD task operations (break_down/prioritize/energy_match)');
      }
    } catch (error) {
      console.error('Command failed:', error.message);
      process.exit(1);
    }
  };

  runCommand();
}
