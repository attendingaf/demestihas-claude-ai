# HERMES_SOCIAL_PRD.md
## Social Media Orchestration Agent - Product Requirements Document
*Ready for Claude Code Implementation*

### Executive Summary
Hermes-Social: AI-powered social media agent that captures your CMO physician executive voice, generates platform-optimized content, and manages cross-platform thought leadership campaigns with medical accuracy and compliance checking.

### User Story
AS a CMO-level physician executive with limited time  
I WANT an AI agent that writes in my voice and manages my social presence  
SO THAT I can maintain thought leadership while focusing on strategic work  

### Your Writing DNA (Captured from Analysis)
- **Hook Pattern**: "Spicy take:" + contrarian insight
- **Bridge Builder**: Connect clinical ↔ business perspectives  
- **Evidence-Based**: Conference insights, data points, real examples
- **Direct CTAs**: "Shoot me a DM" / "Let's talk"
- **Strategic Tagging**: Mention specific leaders when relevant
- **Value Prop**: "The gap I fill" - clear positioning
- **Narrative Arc**: Problem → Insight → Solution → Action

### Platform Priority & Strategy
1. **LinkedIn** (Primary) - Long-form thought leadership, 2-3x/week
2. **Instagram** - Visual stories from conferences, 1-2x/week  
3. **Facebook** - Repurposed LinkedIn with personal touch, 1x/week
4. **Threads** - Quick healthcare tech takes, 3-4x/week
5. **Twitter/X** - Conference live-tweets, industry commentary
6. **TikTok** - Educational content if time permits

### Core Capabilities

#### 1. Voice Cloning Engine
```javascript
class VoiceEngine {
  constructor() {
    this.patterns = {
      hooks: [
        "Spicy take:",
        "Health tech companies rarely expect...",
        "For years, I thought..."
      ],
      bridges: [
        "clinical and business",
        "medicine and metrics",
        "patient care and profitability"
      ],
      closers: [
        "Shoot me a DM",
        "Let's talk about",
        "That's the gap I fill"
      ]
    };
  }
  
  async analyzeEmailStyle() {
    // Pull from Gmail via Pluma integration
    const emails = await this.gmail.getRecentSent(50);
    return this.extractStylePatterns(emails);
  }
  
  async learnFromPosts() {
    // Scrape your existing LinkedIn posts
    const posts = await this.scraper.getMyPosts('linkedin', 100);
    return this.updateVoiceModel(posts);
  }
}
```

#### 2. Content Generation Pipeline
```javascript
class ContentGenerator {
  async generatePost(topic, platform) {
    const post = {
      hook: await this.viralHookGenerator(topic),
      body: await this.expandIdea(topic, platform),
      cta: await this.selectCTA(topic),
      hashtags: await this.researchHashtags(topic, platform)
    };
    
    // Platform optimization
    return this.optimizeForPlatform(post, platform);
  }
  
  async viralHookGenerator(topic) {
    // Analyze trending hooks in healthcare/tech
    const trends = await this.analyzeTrends();
    
    // Generate 3 hook variations
    return [
      `Spicy take: ${this.contrarian(topic)}`,
      `${this.question(topic)} Here's what I learned:`,
      `Everyone thinks ${this.common}. They're wrong.`
    ];
  }
}
```

#### 3. Counter-Narrative Detector
```javascript
class RiskAnalyzer {
  async checkControversy(content) {
    const risks = {
      medical: await this.medicalAccuracyCheck(content),
      compliance: await this.hipaaComplianceCheck(content),
      interpretation: await this.controversyScore(content),
      family: await this.privacyCheck(content)
    };
    
    if (risks.interpretation > 0.7) {
      return {
        warning: "High controversy potential",
        issues: this.explainRisks(risks),
        alternatives: this.suggestSaferAngles(content)
      };
    }
    
    return { safe: true, risks };
  }
}
```

#### 4. A/B Test Variation Generator
```javascript
class VariationEngine {
  generateVariations(post, count = 3) {
    return {
      original: post,
      variations: [
        this.varyHook(post),      // Different opening
        this.varyTone(post),      // Formal vs casual
        this.varyLength(post),    // Short vs detailed
        this.varyCTA(post)        // Different call-to-action
      ].slice(0, count)
    };
  }
}
```

#### 5. Cross-Platform Campaign Manager  
```javascript
class CampaignOrchestrator {
  async planCampaign(theme, duration = '1 week') {
    const calendar = await this.huata.getEvents(duration);
    const campaign = {
      theme,
      platforms: this.platformSchedule(theme),
      calendar_hooks: this.extractEventHooks(calendar),
      content_calendar: this.generateSchedule(theme, calendar)
    };
    
    return {
      linkedin: campaign.content_calendar.filter(p => p.platform === 'linkedin'),
      instagram: this.visualBriefs(campaign),
      threads: this.quickTakes(campaign),
      coordinated: true
    };
  }
}
```

### Technical Architecture

#### Container Setup
```dockerfile
FROM node:20-alpine
WORKDIR /app

# Install Playwright for scraping
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

COPY package*.json ./
RUN npm install
COPY . .

EXPOSE 8005
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8005/health || exit 1
CMD ["node", "src/index.js"]
```

#### API Endpoints
```javascript
// POST /generate - Generate content
{
  topic: "AI scribes and data value",
  platforms: ["linkedin", "threads"],
  variations: 3,
  check_controversy: true
}

// POST /campaign - Plan multi-platform campaign
{
  theme: "Healthcare AI Summit insights",
  duration: "1 week",
  include_events: true
}

// POST /analyze - Analyze post performance
{
  post_url: "https://linkedin.com/posts/...",
  metrics: ["engagement", "reach", "leads"]
}

// GET /schedule - Get optimal posting times
{
  platform: "linkedin",
  timezone: "America/New_York"
}

// POST /learn - Update voice model
{
  source: "gmail",  // or "linkedin", "drive"
  count: 50
}
```

### Integration Points

#### 1. With Existing Agents
- **Huata**: Pull calendar events for content hooks
- **Pluma**: Analyze email style and tone
- **Mnemo**: Store successful post patterns
- **Lyco**: Schedule content creation during high-energy windows

#### 2. Platform APIs & Scraping
```javascript
class PlatformConnector {
  constructor() {
    this.apis = {
      linkedin: new LinkedInAPI(process.env.LINKEDIN_TOKEN),
      instagram: new InstagramBasicAPI(process.env.IG_TOKEN),
      twitter: new TwitterAPI(process.env.TWITTER_BEARER)
    };
    
    this.scrapers = {
      linkedin: new LinkedInScraper(), // Playwright-based
      instagram: new InstagramScraper()
    };
  }
  
  async hybridFetch(platform, action, params) {
    // Try API first
    try {
      return await this.apis[platform][action](params);
    } catch (error) {
      if (error.code === 'RATE_LIMIT') {
        // Fall back to scraping
        return await this.scrapers[platform][action](params);
      }
      throw error;
    }
  }
}
```

### Docker Compose Addition
```yaml
hermes-social:
  container_name: demestihas-hermes-social
  build:
    context: ./agents/hermes-social
    dockerfile: Dockerfile
  ports:
    - "8005:8005"
  volumes:
    - ./agents/hermes-social/data:/data
    - ./agents/hermes-social/config:/config
  environment:
    - NODE_ENV=production
    - REDIS_HOST=demestihas-redis
    - HUATA_URL=http://demestihas-huata:8003
    - PLUMA_URL=http://demestihas-pluma:8002
    - MNEMO_URL=http://demestihas-mnemo:8004
    - LINKEDIN_TOKEN=${LINKEDIN_TOKEN}
    - TWITTER_BEARER=${TWITTER_BEARER}
    - IG_TOKEN=${IG_TOKEN}
  networks:
    - demestihas-network
  restart: unless-stopped
  depends_on:
    - redis
    - huata
    - mnemo
```

### File Structure
```
/agents/hermes-social/
├── src/
│   ├── index.js              # Express server
│   ├── voice-engine.js       # Style learning
│   ├── content-generator.js  # Post creation
│   ├── risk-analyzer.js      # Controversy detection
│   ├── variation-engine.js   # A/B testing
│   └── campaign-manager.js   # Multi-platform coordination
├── scrapers/
│   ├── linkedin-scraper.js   # Playwright-based
│   ├── instagram-scraper.js  
│   └── twitter-scraper.js
├── apis/
│   ├── linkedin-api.js       # Official API
│   ├── instagram-api.js
│   └── twitter-api.js
├── templates/
│   ├── hooks.json            # Your hook patterns
│   ├── ctas.json             # Call-to-action templates
│   └── voice-model.json      # Your writing DNA
├── data/
│   ├── posts.db              # Historical posts
│   ├── performance.db        # Metrics tracking
│   └── campaigns.db          # Campaign history
├── config/
│   └── platforms.json        # Platform-specific rules
├── package.json
├── Dockerfile
└── .env.example
```

### Dependencies
```json
{
  "name": "hermes-social-agent",
  "version": "1.0.0",
  "type": "module",
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "axios": "^1.4.0",
    "playwright": "^1.40.0",
    "cheerio": "^1.0.0-rc.12",
    "natural": "^6.10.0",
    "compromise": "^14.10.0",
    "linkedin-api": "^2.0.0",
    "twitter-api-v2": "^1.15.0",
    "openai": "^4.20.0",
    "sqlite3": "^5.1.6",
    "node-schedule": "^2.1.1",
    "redis": "^4.6.5"
  }
}
```

### Test Commands
```bash
# 1. Generate a LinkedIn post
curl -X POST http://localhost:8005/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI scribes real value is data",
    "platforms": ["linkedin"],
    "check_controversy": true
  }'

# 2. Plan weekly campaign
curl -X POST http://localhost:8005/campaign \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Healthcare AI insights",
    "duration": "1 week"
  }'

# 3. Learn from emails
curl -X POST http://localhost:8005/learn \
  -H "Content-Type: application/json" \
  -d '{
    "source": "gmail",
    "count": 50
  }'

# 4. Get optimal posting time
curl "http://localhost:8005/schedule?platform=linkedin"

# 5. Check health
curl http://localhost:8005/health
```

### Success Metrics & Validation
1. **Voice Match Score**: >85% similarity to your writing style
2. **Engagement Prediction**: ±20% accuracy on likes/comments
3. **Controversy Detection**: 0 compliance violations
4. **Generation Speed**: <3 seconds per post
5. **Campaign Coherence**: Cross-platform message alignment

### Implementation Phases

#### Phase 1: Core Voice Engine (Day 1)
- Extract patterns from provided examples
- Basic LinkedIn post generation
- Health endpoint

#### Phase 2: Platform Integration (Day 2)
- LinkedIn API + scraping hybrid
- Instagram/Threads adapters
- Optimal timing calculator

#### Phase 3: Risk Management (Day 3)
- Medical accuracy checker
- HIPAA compliance scanner
- Controversy detector

#### Phase 4: Advanced Features (Day 4)
- A/B variation generator
- Campaign orchestrator
- Performance tracking

#### Phase 5: Agent Integration (Day 5)
- Connect to Huata for calendar
- Connect to Mnemo for patterns
- Connect to Pluma for email style

### Medical & Compliance Rules
```javascript
const COMPLIANCE_RULES = {
  hipaa: {
    forbidden: ['patient name', 'MRN', 'specific dates', 'photos'],
    check: content => !HIPAA_PATTERNS.test(content)
  },
  medical_claims: {
    require_evidence: ['cure', 'treatment', 'diagnosis'],
    require_disclaimer: ['medical advice', 'recommendation']
  },
  corporate: {
    avoid: ['insider information', 'earnings', 'unannounced']
  }
};
```

### Your Unique Voice Patterns
Based on analysis:
- **Opening**: 60% start with provocative statement
- **Structure**: Problem (30%) → Insight (40%) → Solution (20%) → CTA (10%)
- **Evidence**: Always includes conference, data, or peer reference
- **Perspective**: Bridges clinical-business divide in 80% of posts
- **Engagement**: Direct DM requests outperform generic CTAs 3:1
- **Length**: LinkedIn optimal 150-200 words, Threads 50-75 words

---

*Ready for Claude Code implementation. Containerized for immediate integration with existing Demestihas AI system.*
