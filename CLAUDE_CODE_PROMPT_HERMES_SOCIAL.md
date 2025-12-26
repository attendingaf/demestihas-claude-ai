# BUILD HERMES-SOCIAL: Social Media Agent with Voice Cloning

Create a containerized social media orchestration agent that generates content in the user's specific CMO physician executive voice. Focus on LinkedIn as primary platform with expansion to others.

## STEP 1: Create Directory Structure
```bash
mkdir -p /Users/menedemestihas/Projects/demestihas-ai/agents/hermes-social/{src,data,config}
cd /Users/menedemestihas/Projects/demestihas-ai/agents/hermes-social
```

## STEP 2: Create package.json
```json
{
  "name": "hermes-social-agent",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node src/index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "axios": "^1.4.0",
    "dotenv": "^16.0.3"
  }
}
```

## STEP 3: Create Dockerfile
```dockerfile
FROM node:20-alpine
WORKDIR /app

# Install curl for healthcheck
RUN apk add --no-cache curl

COPY package*.json ./
RUN npm install --production

COPY . .

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8005/health || exit 1

CMD ["node", "src/index.js"]
```

## STEP 4: Create src/index.js - Main Server
```javascript
import express from 'express';
import cors from 'cors';
import { VoiceEngine } from './voice-engine.js';
import { RiskAnalyzer } from './risk-analyzer.js';
import { PlatformOptimizer } from './platform-optimizer.js';

const app = express();
app.use(cors());
app.use(express.json());

const voice = new VoiceEngine();
const risk = new RiskAnalyzer();
const optimizer = new PlatformOptimizer();

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    agent: 'hermes-social',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});

// Generate post endpoint
app.post('/generate', async (req, res) => {
  try {
    const { 
      topic, 
      platforms = ['linkedin'], 
      variations = 1,
      check_controversy = true 
    } = req.body;
    
    console.log(`Generating posts for topic: ${topic}`);
    const results = [];
    
    for (const platform of platforms) {
      // Generate content in user's voice
      const rawContent = await voice.generatePost(topic, platform);
      
      // Check for risks if enabled
      if (check_controversy) {
        const riskAnalysis = await risk.analyze(rawContent);
        if (!riskAnalysis.safe) {
          results.push({
            platform,
            status: 'blocked',
            risks: riskAnalysis.risks,
            suggestions: riskAnalysis.suggestions
          });
          continue;
        }
      }
      
      // Optimize for platform
      const optimized = optimizer.optimize(rawContent, platform);
      
      // Generate variations if requested
      const posts = [];
      if (variations > 1) {
        for (let i = 0; i < variations; i++) {
          posts.push(await voice.generateVariation(optimized, i));
        }
      } else {
        posts.push(optimized);
      }
      
      results.push({
        platform,
        status: 'success',
        posts,
        optimal_time: optimizer.getOptimalTime(platform)
      });
    }
    
    res.json({ success: true, results });
  } catch (error) {
    console.error('Generation error:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Analyze risk endpoint
app.post('/analyze-risk', async (req, res) => {
  try {
    const { content } = req.body;
    const analysis = await risk.analyze(content);
    res.json(analysis);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Learn from samples endpoint (placeholder for future)
app.post('/learn', async (req, res) => {
  const { source, samples } = req.body;
  // Future: Connect to Gmail/LinkedIn for learning
  res.json({ 
    success: true, 
    message: 'Learning endpoint ready for implementation',
    source,
    sampleCount: samples?.length || 0
  });
});

const PORT = process.env.PORT || 8005;
app.listen(PORT, () => {
  console.log(`Hermes-Social agent running on port ${PORT}`);
});
```

## STEP 5: Create src/voice-engine.js - Voice Replication
```javascript
export class VoiceEngine {
  constructor() {
    // User's specific writing patterns from examples
    this.voicePatterns = {
      hooks: [
        "Spicy take:",
        "Health tech companies rarely expect",
        "For years, I thought",
        "Here's what stuck out from",
        "Everyone thinks"
      ],
      
      bridges: [
        "clinical and business",
        "medicine and metrics", 
        "patient care and profitability",
        "patient-centered care and business-minded goals",
        "clinically credible and business strong"
      ],
      
      evidence: [
        "from the {conference} last week",
        "during an audience Q&A",
        "one of the memorable quotes was",
        "panel discussion revealed",
        "data shows"
      ],
      
      closers: [
        "Shoot me a DM if you want to chat more about this",
        "Let's talk about how",
        "That's the gap I fill",
        "If you're building in health tech",
        "The result isn't compromise. It's partnership"
      ],
      
      structure: {
        problem: 0.3,  // 30% problem framing
        insight: 0.4,  // 40% unique insight
        solution: 0.2, // 20% solution
        cta: 0.1      // 10% call to action
      }
    };
  }
  
  async generatePost(topic, platform) {
    // Select appropriate patterns for the topic
    const hook = this.selectHook(topic);
    const problem = this.frameProblem(topic);
    const insight = this.generateInsight(topic);
    const solution = this.proposeSolution(topic);
    const cta = this.selectCTA(platform);
    
    // Assemble in user's style
    const parts = [];
    
    // Always start with hook
    parts.push(hook);
    
    // Build narrative
    parts.push(problem);
    parts.push(insight);
    
    // Add bridge concept
    const bridge = this.selectRandom(this.voicePatterns.bridges);
    parts.push(`The key is understanding the bridge between ${bridge}.`);
    
    parts.push(solution);
    parts.push(cta);
    
    return parts.join(' ');
  }
  
  selectHook(topic) {
    const hooks = this.voicePatterns.hooks;
    const selected = this.selectRandom(hooks);
    
    if (selected === "Spicy take:") {
      return `Spicy take: The real value of ${topic} isn't what everyone thinks.`;
    } else if (selected.includes("rarely expect")) {
      return `Health tech companies rarely expect physician leaders to understand ${topic}.`;
    } else if (selected.includes("For years")) {
      return `For years, I thought ${topic} was just hype. I was wrong.`;
    }
    
    return selected;
  }
  
  frameProblem(topic) {
    const templates = [
      `Most people see ${topic} as a technology problem. They're missing the bigger picture.`,
      `The challenge with ${topic} isn't technical—it's cultural.`,
      `We're approaching ${topic} all wrong in healthcare.`
    ];
    
    return this.selectRandom(templates);
  }
  
  generateInsight(topic) {
    const templates = [
      `Two things became clear at the recent summit: First, ${topic} has negative margins. Second, the real asset is the DATA.`,
      `What everyone misses about ${topic}: it's not about efficiency. It's about clarity.`,
      `${topic} is creating a shared language between clinicians and executives.`
    ];
    
    return this.selectRandom(templates);
  }
  
  proposeSolution(topic) {
    const templates = [
      `Smart leaders are using ${topic} to bridge the gap between care quality and business metrics.`,
      `The solution: Use ${topic} as a translator, not a replacement.`,
      `Forward-thinking organizations leverage ${topic} for both clinical credibility AND business strength.`
    ];
    
    return this.selectRandom(templates);
  }
  
  selectCTA(platform) {
    if (platform === 'linkedin') {
      return this.selectRandom([
        "Shoot me a DM if you want to chat more about this.",
        "Let's talk about how this applies to your organization.",
        "That's the gap I fill. Message me to explore how."
      ]);
    } else if (platform === 'threads') {
      return "Thoughts? 👇";
    } else {
      return "Let's connect on this.";
    }
  }
  
  async generateVariation(content, index) {
    // Simple variation for now - change hook or CTA
    if (index === 0) return content;
    
    const variations = [
      content.replace("Spicy take:", "Unpopular opinion:"),
      content.replace("Shoot me a DM", "Drop a comment"),
      content.replace("The real value", "The hidden value")
    ];
    
    return variations[index % variations.length] || content;
  }
  
  selectRandom(array) {
    return array[Math.floor(Math.random() * array.length)];
  }
}
```

## STEP 6: Create src/risk-analyzer.js - Compliance Checking
```javascript
export class RiskAnalyzer {
  constructor() {
    this.hipaaPatterns = [
      /patient\s+name/i,
      /\b\d{3}-\d{2}-\d{4}\b/,  // SSN
      /\b\d{2}\/\d{2}\/\d{4}\b/, // Dates that could be PHI
      /medical\s+record\s+number/i,
      /MRN\s*#?\s*\d+/i,
      /specific\s+diagnosis/i,
      /\b(?:Mr|Mrs|Ms|Dr)\.\s+[A-Z][a-z]+\s+[A-Z][a-z]+/  // Patient names
    ];
    
    this.controversialTerms = [
      'always', 'never', 'cure', 'guaranteed',
      'breakthrough', 'revolutionary', 'miracle',
      'only solution', 'everyone should', 'proven to'
    ];
    
    this.medicalClaims = [
      'cure', 'treat', 'diagnose', 'prevent',
      'clinically proven', 'FDA approved', 'medical advice'
    ];
  }
  
  async analyze(content) {
    const results = {
      safe: true,
      risks: [],
      suggestions: []
    };
    
    // Check HIPAA compliance
    const hipaaCheck = this.checkHIPAA(content);
    if (hipaaCheck.violation) {
      results.safe = false;
      results.risks.push(hipaaCheck);
    }
    
    // Check controversial content
    const controversyScore = this.checkControversy(content);
    if (controversyScore > 0.7) {
      results.safe = false;
      results.risks.push({
        type: 'controversy',
        score: controversyScore,
        issue: 'High potential for misinterpretation'
      });
      results.suggestions.push('Consider softening absolute claims');
    }
    
    // Check medical claims
    const medicalCheck = this.checkMedicalClaims(content);
    if (medicalCheck.hasUnverifiedClaims) {
      results.risks.push(medicalCheck);
      results.suggestions.push('Add disclaimer or cite sources');
    }
    
    return results;
  }
  
  checkHIPAA(content) {
    for (const pattern of this.hipaaPatterns) {
      if (pattern.test(content)) {
        return {
          violation: true,
          type: 'HIPAA',
          issue: 'Potential PHI disclosure detected',
          pattern: pattern.toString()
        };
      }
    }
    
    return { violation: false };
  }
  
  checkControversy(content) {
    const lowerContent = content.toLowerCase();
    let score = 0;
    let matches = 0;
    
    for (const term of this.controversialTerms) {
      if (lowerContent.includes(term)) {
        score += 0.2;
        matches++;
      }
    }
    
    // Check for absolute statements
    if (/\b(all|every|no one|everyone)\b/i.test(content)) {
      score += 0.3;
    }
    
    return Math.min(score, 1.0);
  }
  
  checkMedicalClaims(content) {
    const lowerContent = content.toLowerCase();
    const claims = [];
    
    for (const claim of this.medicalClaims) {
      if (lowerContent.includes(claim)) {
        claims.push(claim);
      }
    }
    
    return {
      hasUnverifiedClaims: claims.length > 0,
      type: 'medical_claims',
      claims: claims,
      issue: claims.length > 0 ? 'Medical claims require evidence' : null
    };
  }
}
```

## STEP 7: Create src/platform-optimizer.js - Platform Adaptation
```javascript
export class PlatformOptimizer {
  constructor() {
    this.platforms = {
      linkedin: {
        maxLength: 3000,
        idealLength: { min: 150, max: 200 },
        hashtagLimit: 5,
        style: 'professional',
        optimalTimes: ['7am', '12pm', '5pm']
      },
      threads: {
        maxLength: 500,
        idealLength: { min: 50, max: 75 },
        hashtagLimit: 3,
        style: 'conversational',
        optimalTimes: ['8am', '1pm', '8pm']
      },
      instagram: {
        maxLength: 2200,
        idealLength: { min: 125, max: 150 },
        hashtagLimit: 30,
        style: 'visual',
        optimalTimes: ['11am', '2pm', '5pm']
      },
      facebook: {
        maxLength: 63206,
        idealLength: { min: 100, max: 150 },
        hashtagLimit: 3,
        style: 'personal',
        optimalTimes: ['9am', '3pm', '7pm']
      },
      twitter: {
        maxLength: 280,
        idealLength: { min: 70, max: 100 },
        hashtagLimit: 2,
        style: 'concise',
        optimalTimes: ['9am', '12pm', '6pm']
      }
    };
  }
  
  optimize(content, platform) {
    const rules = this.platforms[platform] || this.platforms.linkedin;
    let optimized = content;
    
    // Adjust length
    if (content.length > rules.maxLength) {
      optimized = this.truncate(content, rules.maxLength);
    }
    
    // Add platform-specific formatting
    optimized = this.formatForPlatform(optimized, platform);
    
    // Add hashtags
    optimized = this.addHashtags(optimized, platform);
    
    return optimized;
  }
  
  truncate(content, maxLength) {
    if (content.length <= maxLength) return content;
    
    // Find last complete sentence before limit
    const truncated = content.substring(0, maxLength - 3);
    const lastPeriod = truncated.lastIndexOf('.');
    
    if (lastPeriod > maxLength * 0.7) {
      return truncated.substring(0, lastPeriod + 1);
    }
    
    return truncated + '...';
  }
  
  formatForPlatform(content, platform) {
    switch(platform) {
      case 'linkedin':
        // Add line breaks for readability
        return content.replace(/\. /g, '.\n\n');
        
      case 'threads':
        // Keep it punchy
        return content.replace(/\. /g, '.\n');
        
      case 'instagram':
        // Add emoji and line breaks
        return '🏥 ' + content.replace(/\. /g, '.\n.\n');
        
      default:
        return content;
    }
  }
  
  addHashtags(content, platform) {
    const rules = this.platforms[platform];
    const hashtags = this.generateHashtags(content, rules.hashtagLimit);
    
    if (platform === 'linkedin') {
      return content + '\n\n' + hashtags.join(' ');
    } else if (platform === 'instagram') {
      return content + '\n.\n.\n' + hashtags.join(' ');
    } else {
      return content + '\n\n' + hashtags.join(' ');
    }
  }
  
  generateHashtags(content, limit) {
    // Core hashtags for the user
    const coreHashtags = [
      '#HealthTech',
      '#HealthcareAI',
      '#PhysicianLeadership',
      '#DigitalHealth',
      '#MedTech'
    ];
    
    // Topic-specific hashtags based on content
    const topicHashtags = [];
    
    if (content.toLowerCase().includes('ai')) {
      topicHashtags.push('#AIinHealthcare', '#ArtificialIntelligence');
    }
    if (content.toLowerCase().includes('data')) {
      topicHashtags.push('#HealthData', '#DataDriven');
    }
    if (content.toLowerCase().includes('burnout')) {
      topicHashtags.push('#PhysicianBurnout', '#ClinicalWellbeing');
    }
    if (content.toLowerCase().includes('business')) {
      topicHashtags.push('#HealthcareBusiness', '#ValueBasedCare');
    }
    
    // Combine and limit
    const allHashtags = [...coreHashtags, ...topicHashtags];
    return allHashtags.slice(0, limit);
  }
  
  getOptimalTime(platform) {
    const times = this.platforms[platform]?.optimalTimes || ['9am', '12pm', '5pm'];
    const timezone = 'America/New_York';
    const today = new Date();
    const dayOfWeek = today.getDay();
    
    // Best times by day
    if (dayOfWeek === 0 || dayOfWeek === 6) {
      // Weekend
      return { time: '11am', timezone, note: 'Weekend optimal' };
    } else if (dayOfWeek === 2 || dayOfWeek === 4) {
      // Tuesday/Thursday - best engagement
      return { time: times[1], timezone, note: 'Peak engagement day' };
    } else {
      // Regular weekday
      return { time: times[0], timezone, note: 'Standard optimal' };
    }
  }
}
```

## STEP 8: Update docker-compose.yml
Add this service to the existing docker-compose.yml:

```yaml
  hermes-social:
    container_name: demestihas-hermes-social
    build:
      context: ./agents/hermes-social
      dockerfile: Dockerfile
    ports:
      - "8005:8005"
    environment:
      - NODE_ENV=production
      - PORT=8005
    networks:
      - demestihas-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 3s
      retries: 3
```

## STEP 9: Build and Run

```bash
# Navigate to project root
cd /Users/menedemestihas/Projects/demestihas-ai

# Build and start the container
docker-compose up -d --build hermes-social

# Check if it's running
docker ps | grep hermes-social

# Check logs
docker logs demestihas-hermes-social --tail 50

# Test health endpoint
curl http://localhost:8005/health
```

## STEP 10: Test the Implementation

```bash
# Test 1: Generate LinkedIn post
curl -X POST http://localhost:8005/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI scribes in healthcare",
    "platforms": ["linkedin"],
    "variations": 3
  }'

# Test 2: Check HIPAA compliance
curl -X POST http://localhost:8005/analyze-risk \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Patient John Smith, MRN #12345, diagnosed with diabetes"
  }'

# Test 3: Generate multi-platform
curl -X POST http://localhost:8005/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "healthcare technology innovation",
    "platforms": ["linkedin", "threads", "instagram"]
  }'

# Test 4: Generate without controversy check
curl -X POST http://localhost:8005/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "digital transformation in medicine",
    "platforms": ["linkedin"],
    "check_controversy": false
  }'
```

## Expected Output Examples

### LinkedIn Post:
```
Spicy take: The real value of AI scribes in healthcare isn't what everyone thinks.

Most people see AI scribes in healthcare as a technology problem. They're missing the bigger picture.

Two things became clear at the recent summit: First, AI scribes in healthcare has negative margins. Second, the real asset is the DATA.

The key is understanding the bridge between clinical and business.

Smart leaders are using AI scribes in healthcare to bridge the gap between care quality and business metrics.

Shoot me a DM if you want to chat more about this.

#HealthTech #HealthcareAI #PhysicianLeadership #DigitalHealth #AIinHealthcare
```

### Risk Analysis Response:
```json
{
  "safe": false,
  "risks": [{
    "violation": true,
    "type": "HIPAA",
    "issue": "Potential PHI disclosure detected",
    "pattern": "/patient\\s+name/i"
  }],
  "suggestions": ["Remove patient identifying information"]
}
```

## Success Criteria
✅ Container running on port 8005
✅ Health check passing
✅ Posts match user's voice patterns
✅ HIPAA violations detected
✅ Platform-specific formatting working
✅ Hashtags generated appropriately
✅ Multiple variations generated

## Troubleshooting
- If port 8005 is in use: `lsof -i :8005` and kill the process
- If container won't start: Check `docker logs demestihas-hermes-social`
- If health check fails: Verify curl is installed in container
- If voice doesn't match: Review voice-engine.js patterns

Build this step by step, testing after each major component. The voice matching is critical - the posts MUST sound like the user's examples with "Spicy take:" openers and clinical-business bridge building.
