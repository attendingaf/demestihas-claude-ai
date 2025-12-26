import winston from 'winston';
import { parse } from '@babel/parser';
import traverse from '@babel/traverse';
import generate from '@babel/generator';
import * as t from '@babel/types';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class CodeIntelligence {
  constructor() {
    this.astCache = new Map();
    this.codePatterns = new Map();
    this.refactoringTemplates = new Map();
    this.metrics = {
      totalAnalyses: 0,
      successfulModifications: 0,
      refactoringSuggestions: 0,
      astCacheHits: 0
    };
  }

  async initialize() {
    try {
      // Load refactoring templates
      this.loadRefactoringTemplates();
      
      // Load common code patterns
      this.loadCodePatterns();
      
      logger.info('Code Intelligence initialized');
    } catch (error) {
      logger.error('Failed to initialize Code Intelligence', { 
        error: error.message 
      });
      throw error;
    }
  }

  async analyzeCode(code, language = 'javascript') {
    const startTime = Date.now();
    
    try {
      // Check cache
      const cacheKey = this.generateCacheKey(code);
      if (this.astCache.has(cacheKey)) {
        this.metrics.astCacheHits++;
        return this.astCache.get(cacheKey);
      }
      
      // Parse code to AST
      const ast = await this.parseCode(code, language);
      
      // Extract information
      const analysis = {
        ast,
        language,
        structure: this.extractStructure(ast),
        complexity: this.calculateComplexity(ast),
        dependencies: this.extractDependencies(ast),
        patterns: this.identifyPatterns(ast),
        suggestions: await this.generateSuggestions(ast, code)
      };
      
      // Cache result
      this.astCache.set(cacheKey, analysis);
      
      // Update metrics
      this.metrics.totalAnalyses++;
      
      logger.debug('Code analyzed', {
        language,
        time: Date.now() - startTime,
        complexity: analysis.complexity
      });
      
      return analysis;
    } catch (error) {
      logger.error('Failed to analyze code', { 
        error: error.message 
      });
      throw error;
    }
  }

  async parseCode(code, language) {
    if (language !== 'javascript' && language !== 'typescript') {
      // For other languages, return a simplified structure
      return {
        type: 'Program',
        body: [],
        language,
        raw: code
      };
    }
    
    try {
      const ast = parse(code, {
        sourceType: 'module',
        plugins: [
          'jsx',
          'typescript',
          'decorators-legacy',
          'classProperties',
          'asyncGenerators',
          'dynamicImport'
        ]
      });
      
      return ast;
    } catch (error) {
      logger.warn('Failed to parse code', { error: error.message });
      
      // Return partial AST on error
      return {
        type: 'Program',
        body: [],
        error: error.message,
        raw: code
      };
    }
  }

  extractStructure(ast) {
    const structure = {
      imports: [],
      exports: [],
      functions: [],
      classes: [],
      variables: [],
      components: []
    };
    
    if (!ast || !ast.program) return structure;
    
    traverse.default(ast, {
      ImportDeclaration(path) {
        structure.imports.push({
          source: path.node.source.value,
          specifiers: path.node.specifiers.map(s => ({
            type: s.type,
            name: s.local?.name || s.imported?.name
          }))
        });
      },
      
      ExportDeclaration(path) {
        structure.exports.push({
          type: path.node.type,
          declaration: path.node.declaration?.type
        });
      },
      
      FunctionDeclaration(path) {
        structure.functions.push({
          name: path.node.id?.name,
          params: path.node.params.length,
          async: path.node.async,
          generator: path.node.generator
        });
      },
      
      ClassDeclaration(path) {
        structure.classes.push({
          name: path.node.id?.name,
          superClass: path.node.superClass?.name,
          methods: []
        });
      },
      
      VariableDeclaration(path) {
        path.node.declarations.forEach(decl => {
          if (decl.id?.name) {
            structure.variables.push({
              name: decl.id.name,
              kind: path.node.kind,
              initialized: !!decl.init
            });
          }
        });
      },
      
      JSXElement(path) {
        const name = path.node.openingElement?.name?.name;
        if (name && /^[A-Z]/.test(name)) {
          if (!structure.components.includes(name)) {
            structure.components.push(name);
          }
        }
      }
    });
    
    return structure;
  }

  calculateComplexity(ast) {
    let complexity = 1; // Base complexity
    
    if (!ast || !ast.program) return complexity;
    
    traverse.default(ast, {
      IfStatement() { complexity++; },
      ConditionalExpression() { complexity++; },
      LogicalExpression(path) {
        if (path.node.operator === '&&' || path.node.operator === '||') {
          complexity++;
        }
      },
      ForStatement() { complexity++; },
      WhileStatement() { complexity++; },
      DoWhileStatement() { complexity++; },
      SwitchCase() { complexity++; },
      CatchClause() { complexity++; }
    });
    
    return complexity;
  }

  extractDependencies(ast) {
    const dependencies = {
      internal: [],
      external: [],
      missing: []
    };
    
    if (!ast || !ast.program) return dependencies;
    
    const structure = this.extractStructure(ast);
    
    for (const imp of structure.imports) {
      if (imp.source.startsWith('.') || imp.source.startsWith('/')) {
        dependencies.internal.push(imp.source);
      } else {
        dependencies.external.push(imp.source);
      }
    }
    
    // Detect potentially missing imports
    const definedIdentifiers = new Set([
      ...structure.functions.map(f => f.name),
      ...structure.classes.map(c => c.name),
      ...structure.variables.map(v => v.name)
    ]);
    
    traverse.default(ast, {
      Identifier(path) {
        if (path.isReferencedIdentifier() && 
            !path.scope.hasBinding(path.node.name) &&
            !definedIdentifiers.has(path.node.name)) {
          if (!dependencies.missing.includes(path.node.name)) {
            dependencies.missing.push(path.node.name);
          }
        }
      }
    });
    
    return dependencies;
  }

  identifyPatterns(ast) {
    const patterns = [];
    
    if (!ast || !ast.program) return patterns;
    
    // Check for common patterns
    traverse.default(ast, {
      // React hooks pattern
      CallExpression(path) {
        if (path.node.callee?.name?.startsWith('use')) {
          patterns.push({
            type: 'react_hook',
            name: path.node.callee.name
          });
        }
      },
      
      // Async/await pattern
      AwaitExpression() {
        if (!patterns.find(p => p.type === 'async_await')) {
          patterns.push({ type: 'async_await' });
        }
      },
      
      // Promise pattern
      NewExpression(path) {
        if (path.node.callee?.name === 'Promise') {
          if (!patterns.find(p => p.type === 'promise')) {
            patterns.push({ type: 'promise' });
          }
        }
      },
      
      // Arrow function pattern
      ArrowFunctionExpression() {
        if (!patterns.find(p => p.type === 'arrow_function')) {
          patterns.push({ type: 'arrow_function' });
        }
      }
    });
    
    return patterns;
  }

  async generateSuggestions(ast, code) {
    const suggestions = [];
    
    if (!ast || !ast.program) return suggestions;
    
    const complexity = this.calculateComplexity(ast);
    const structure = this.extractStructure(ast);
    
    // Complexity suggestion
    if (complexity > 10) {
      suggestions.push({
        type: 'refactor',
        message: `High complexity (${complexity}). Consider breaking into smaller functions.`,
        priority: 'high'
      });
    }
    
    // Missing exports suggestion
    if (structure.functions.length > 0 && structure.exports.length === 0) {
      suggestions.push({
        type: 'export',
        message: 'No exports found. Consider exporting public functions.',
        priority: 'medium'
      });
    }
    
    // Async improvement suggestion
    let hasCallbacks = false;
    traverse.default(ast, {
      CallExpression(path) {
        if (path.node.arguments.some(arg => 
          t.isFunctionExpression(arg) || t.isArrowFunctionExpression(arg)
        )) {
          hasCallbacks = true;
        }
      }
    });
    
    if (hasCallbacks) {
      suggestions.push({
        type: 'modernize',
        message: 'Consider using async/await instead of callbacks.',
        priority: 'low'
      });
    }
    
    this.metrics.refactoringSuggestions += suggestions.length;
    
    return suggestions;
  }

  async modifyCode(code, modifications, language = 'javascript') {
    try {
      const ast = await this.parseCode(code, language);
      
      if (!ast || !ast.program) {
        throw new Error('Failed to parse code for modification');
      }
      
      // Apply modifications
      for (const mod of modifications) {
        await this.applyModification(ast, mod);
      }
      
      // Generate modified code
      const result = generate.default(ast, {
        retainLines: true,
        comments: true
      });
      
      this.metrics.successfulModifications++;
      
      return {
        success: true,
        code: result.code,
        modifications: modifications.length
      };
    } catch (error) {
      logger.error('Failed to modify code', { 
        error: error.message 
      });
      
      return {
        success: false,
        error: error.message,
        original: code
      };
    }
  }

  async applyModification(ast, modification) {
    switch (modification.type) {
      case 'rename':
        await this.renameIdentifier(ast, modification.target, modification.newName);
        break;
        
      case 'add_function':
        await this.addFunction(ast, modification.function);
        break;
        
      case 'remove_function':
        await this.removeFunction(ast, modification.target);
        break;
        
      case 'add_import':
        await this.addImport(ast, modification.import);
        break;
        
      default:
        logger.warn('Unknown modification type', { type: modification.type });
    }
  }

  async renameIdentifier(ast, oldName, newName) {
    traverse.default(ast, {
      Identifier(path) {
        if (path.node.name === oldName) {
          path.node.name = newName;
        }
      }
    });
  }

  async addFunction(ast, functionDef) {
    const funcAst = parse(`function ${functionDef.name}(${functionDef.params || ''}) {
      ${functionDef.body || '// TODO: Implement'}
    }`);
    
    ast.program.body.push(funcAst.program.body[0]);
  }

  async removeFunction(ast, functionName) {
    traverse.default(ast, {
      FunctionDeclaration(path) {
        if (path.node.id?.name === functionName) {
          path.remove();
        }
      }
    });
  }

  async addImport(ast, importDef) {
    const importAst = parse(`import ${importDef.specifier} from '${importDef.source}';`);
    ast.program.body.unshift(importAst.program.body[0]);
  }

  async generateSemanticDiff(oldCode, newCode, language = 'javascript') {
    try {
      const oldAst = await this.parseCode(oldCode, language);
      const newAst = await this.parseCode(newCode, language);
      
      const oldStructure = this.extractStructure(oldAst);
      const newStructure = this.extractStructure(newAst);
      
      const diff = {
        added: {
          functions: newStructure.functions.filter(f => 
            !oldStructure.functions.find(of => of.name === f.name)
          ),
          classes: newStructure.classes.filter(c => 
            !oldStructure.classes.find(oc => oc.name === c.name)
          ),
          imports: newStructure.imports.filter(i => 
            !oldStructure.imports.find(oi => oi.source === i.source)
          )
        },
        removed: {
          functions: oldStructure.functions.filter(f => 
            !newStructure.functions.find(nf => nf.name === f.name)
          ),
          classes: oldStructure.classes.filter(c => 
            !newStructure.classes.find(nc => nc.name === c.name)
          ),
          imports: oldStructure.imports.filter(i => 
            !newStructure.imports.find(ni => ni.source === i.source)
          )
        },
        modified: []
      };
      
      // Detect modified functions
      for (const newFunc of newStructure.functions) {
        const oldFunc = oldStructure.functions.find(f => f.name === newFunc.name);
        
        if (oldFunc && (oldFunc.params !== newFunc.params || 
                       oldFunc.async !== newFunc.async)) {
          diff.modified.push({
            type: 'function',
            name: newFunc.name,
            changes: {
              params: { old: oldFunc.params, new: newFunc.params },
              async: { old: oldFunc.async, new: newFunc.async }
            }
          });
        }
      }
      
      return diff;
    } catch (error) {
      logger.error('Failed to generate semantic diff', { 
        error: error.message 
      });
      
      return {
        error: error.message,
        fallback: 'textual_diff'
      };
    }
  }

  async suggestRefactoring(code, language = 'javascript') {
    const analysis = await this.analyzeCode(code, language);
    const suggestions = [];
    
    // Extract long functions
    if (analysis.structure.functions) {
      for (const func of analysis.structure.functions) {
        // Simplified check - in production, analyze function body length
        if (analysis.complexity > 15) {
          suggestions.push({
            type: 'extract_function',
            target: func.name,
            reason: 'Function is too complex',
            example: this.generateExtractFunctionExample(func)
          });
        }
      }
    }
    
    // Suggest converting callbacks to async/await
    if (analysis.patterns.find(p => p.type === 'callback')) {
      suggestions.push({
        type: 'modernize_async',
        reason: 'Convert callbacks to async/await',
        example: this.generateAsyncExample()
      });
    }
    
    // Suggest extracting magic numbers
    const magicNumbers = this.findMagicNumbers(analysis.ast);
    if (magicNumbers.length > 0) {
      suggestions.push({
        type: 'extract_constants',
        targets: magicNumbers,
        reason: 'Extract magic numbers to named constants'
      });
    }
    
    return suggestions;
  }

  findMagicNumbers(ast) {
    const magicNumbers = [];
    
    if (!ast || !ast.program) return magicNumbers;
    
    traverse.default(ast, {
      NumericLiteral(path) {
        const value = path.node.value;
        
        // Ignore common values
        if (value !== 0 && value !== 1 && value !== -1) {
          magicNumbers.push({
            value,
            location: path.node.loc
          });
        }
      }
    });
    
    return magicNumbers;
  }

  generateExtractFunctionExample(func) {
    return `// Extract complex logic from ${func.name}
function extracted${func.name}Logic() {
  // Extracted logic here
}

function ${func.name}() {
  return extracted${func.name}Logic();
}`;
  }

  generateAsyncExample() {
    return `// Convert callback to async/await
// Before:
getData(callback);

// After:
const data = await getData();`;
  }

  loadRefactoringTemplates() {
    this.refactoringTemplates.set('extract_method', {
      pattern: 'function {name}({params}) { {extracted} }',
      description: 'Extract code into a new method'
    });
    
    this.refactoringTemplates.set('inline_variable', {
      pattern: 'return {expression}',
      description: 'Inline temporary variable'
    });
  }

  loadCodePatterns() {
    this.codePatterns.set('singleton', {
      identify: (ast) => {
        // Check for singleton pattern
        return false; // Simplified
      },
      description: 'Singleton pattern detected'
    });
    
    this.codePatterns.set('factory', {
      identify: (ast) => {
        // Check for factory pattern
        return false; // Simplified
      },
      description: 'Factory pattern detected'
    });
  }

  generateCacheKey(code) {
    // Simple hash for caching
    let hash = 0;
    for (let i = 0; i < code.length; i++) {
      const char = code.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return hash.toString();
  }

  getMetrics() {
    const cacheHitRate = this.metrics.totalAnalyses > 0 ?
      this.metrics.astCacheHits / this.metrics.totalAnalyses : 0;
    
    return {
      ...this.metrics,
      cacheHitRate,
      cacheSize: this.astCache.size
    };
  }
}

export default new CodeIntelligence();