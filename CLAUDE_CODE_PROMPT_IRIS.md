# Build IRIS Social Media Agent

Create a containerized social media agent named IRIS that generates posts in my specific CMO physician executive voice.

## My Writing Voice (MUST REPLICATE)
- Opens with "Spicy take:" or contrarian insights  
- Bridges clinical and business perspectives
- Uses conference evidence and data
- Closes with "Shoot me a DM" or "That's the gap I fill"

## Step 1: Create Directory Structure
```bash
cd /Users/menedemestihas/Projects/demestihas-ai
mkdir -p agents/iris/src agents/iris/data
cd agents/iris
```

## Step 2: Create package.json
```json
{
  "name": "iris-agent",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node src/index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5"
  }
}
```

## Step 3: Create Dockerfile
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE 8005
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8005/health || exit 1
CMD ["node", "src/index.js"]
```

## Step 4: Create src/index.js - Main Server
```javascript
import express from 'express';
import cors from 'cors';

const app = express();
app.use(express.json());
app.use(cors());

// My specific voice patterns - IRIS bridges realms
const VOICE_PATTERNS = {
  hooks: [
    "Spicy take:",
    "Health tech companies rarely expect",
    "For years, I thought",
    "Everyone thinks",
    "Here's what stuck out from"
  ],
  bridges: [
    "clinical and business",
    "medicine and metrics", 
    "patient care and profitability",
    "physicians and health tech"
  ],
  evidence: [
    "from the conference",
    "during the panel",
    "the data shows",
    "leaders like"
  ],
  closers: [
    "Shoot me a DM if you want to chat more",
    "Let's talk about",
    "That's the gap I fill",
    "DM me to discuss"
  ]
};

// HIPAA compliance patterns
const HIPAA_VIOLATIONS = [
  /patient\s+name/i,
  /\d{3}-\d{2}-\d{4}/, // SSN
  /medical\s+record/i,
  /\bMRN\b/,
  /specific\s+diagnosis/i
];

// Generate post in my voice
app.post('/generate', async (req, res) => {
  try {
    const { topic, platforms = ['linkedin'], variations = 1 } = req.body;
    console.log(`IRIS generating post about: ${topic}`);
    
    const results = [];
    
    for (const platform of platforms) {
      const posts = [];
      
      for (let i = 0; i < variations; i++) {
        // Build post structure
        const hook = VOICE_PATTERNS.hooks[Math.floor(Math.random() * VOICE_PATTERNS.hooks.length)];
        const bridge = VOICE_PATTERNS.bridges[Math.floor(Math.random() * VOICE_PATTERNS.bridges.length)];
        const evidence = VOICE_PATTERNS.evidence[Math.floor(Math.random() * VOICE_PATTERNS.evidence.length)];
        const closer = VOICE_PATTERNS.closers[Math.floor(Math.random() * VOICE_PATTERNS.closers.length)];
        
        let post;
        
        if (platform === 'linkedin') {
          // LinkedIn: 150-200 words, professional
          post = `${hook} The real value of ${topic} isn't just efficiency. It's transformation.

The disconnect between ${bridge} in ${topic} creates unnecessary friction. We're optimizing metrics without considering the human element.

What I've learned ${evidence}: When we align ${topic} with both clinical excellence AND business sustainability, that's when real change happens. It's not about choosing sides - it's about building bridges.

${topic} works when physicians feel heard and businesses see results. That partnership mindset changes everything.

${closer} about ${topic}.

#HealthcareInnovation #DigitalHealth #PhysicianLeadership #HealthTech #AIinHealthcare`;
        
        } else if (platform === 'threads') {
          // Threads: 50-75 words, punchy
          post = `${hook} ${topic} isn't about the tech.

The real game-changer? Bridging ${bridge}.

${closer}`;
        
        } else if (platform === 'instagram') {
          // Instagram: Visual-first with caption
          post = `${hook}

${topic} transforms healthcare when we stop treating ${bridge} as separate worlds.

The magic happens at the intersection. 🌈

${closer}

#HealthTech #Innovation #PhysicianLeader #DigitalHealth #Healthcare`;
        }
        
        // Check HIPAA compliance
        let safe = true;
        for (const pattern of HIPAA_VIOLATIONS) {
          if (pattern.test(post)) {
            safe = false;
            break;
          }
        }
        
        if (safe) {
          posts.push(post);
        }
      }
      
      results.push({
        platform,
        posts,
        optimal_time: getOptimalTime(platform)
      });
    }
    
    res.json({
      success: true,
      agent: 'iris',
      results
    });
    
  } catch (error) {
    console.error('IRIS generation error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Risk analysis endpoint
app.post('/analyze-risk', async (req, res) => {
  const { content } = req.body;
  const risks = [];
  let safe = true;
  
  // Check HIPAA
  for (const pattern of HIPAA_VIOLATIONS) {
    if (pattern.test(content)) {
      safe = false;
      risks.push({
        type: 'HIPAA',
        risk: 1.0,
        issue: 'Contains protected health information',
        match: content.match(pattern)[0]
      });
    }
  }
  
  // Check for family privacy
  const familyTerms = ['my kids', 'my wife', 'Cindy', 'Elena', 'Aris', 'Eleni'];
  for (const term of familyTerms) {
    if (content.toLowerCase().includes(term.toLowerCase())) {
      safe = false;
      risks.push({
        type: 'Family Privacy',
        risk: 0.8,
        issue: 'Contains family information'
      });
    }
  }
  
  // Check for absolute claims
  const controversial = ['guaranteed', 'cure', 'never', 'always'];
  for (const term of controversial) {
    if (content.toLowerCase().includes(term)) {
      risks.push({
        type: 'Controversy',
        risk: 0.5,
        issue: 'Contains absolute claims'
      });
    }
  }
  
  res.json({
    safe,
    risks,
    suggestions: safe ? [] : [
      'Remove any patient-specific information',
      'Use hypothetical examples instead',
      'Soften absolute claims with "often" or "typically"'
    ]
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    agent: 'iris',
    version: '1.0.0',
    description: 'Social media orchestration - bridging clinical and business',
    timestamp: new Date().toISOString()
  });
});

// Helper function for optimal posting times
function getOptimalTime(platform) {
  const times = {
    linkedin: ['7:30 AM ET', '12:00 PM ET', '5:30 PM ET'],
    threads: ['8:00 AM ET', '1:00 PM ET', '7:00 PM ET'],
    instagram: ['6:00 AM ET', '12:00 PM ET', '6:00 PM ET'],
    facebook: ['9:00 AM ET', '3:00 PM ET', '8:00 PM ET'],
    twitter: ['9:00 AM ET', '12:00 PM ET', '5:00 PM ET']
  };
  
  const platformTimes = times[platform] || times.linkedin;
  const now = new Date();
  const currentHour = now.getHours();
  
  for (const time of platformTimes) {
    const hour = parseInt(time.split(':')[0]);
    if (hour > currentHour) {
      return `Today at ${time}`;
    }
  }
  
  return `Tomorrow at ${platformTimes[0]}`;
}

const PORT = 8005;
app.listen(PORT, () => {
  console.log(`IRIS (Social Media Agent) running on port ${PORT}`);
  console.log('Bridging clinical and business perspectives across platforms');
});
```

## Step 5: Update docker-compose.yml
Add this service to `/Users/menedemestihas/Projects/demestihas-ai/docker-compose.yml`:

```yaml
  iris:
    container_name: demestihas-iris
    build:
      context: ./agents/iris
      dockerfile: Dockerfile
    ports:
      - "8005:8005"
    networks:
      - demestihas-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

## Step 6: Build and Run
```bash
# Navigate to main directory
cd /Users/menedemestihas/Projects/demestihas-ai

# Build the container
docker-compose build iris

# Start IRIS
docker-compose up -d iris

# Check it's running
docker ps | grep iris

# View logs
docker logs demestihas-iris

# Test health endpoint
curl http://localhost:8005/health
```

## Step 7: Test IRIS

### Test 1: Generate LinkedIn Post
```bash
curl -X POST http://localhost:8005/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI scribes in healthcare",
    "platforms": ["linkedin"],
    "variations": 3
  }'
```

### Test 2: Check HIPAA Compliance
```bash
curl -X POST http://localhost:8005/analyze-risk \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Patient John Smith with MRN 12345 diagnosed with diabetes"
  }'
```

### Test 3: Multi-Platform Generation
```bash
curl -X POST http://localhost:8005/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "digital transformation in healthcare",
    "platforms": ["linkedin", "threads", "instagram"]
  }'
```

## Expected Results
- Container named `demestihas-iris` running on port 8005
- Health endpoint returns JSON with agent name "iris"
- Generate endpoint creates posts that sound like my examples
- Risk analyzer blocks HIPAA violations and family information
- Each platform has optimized content length and format

## Debugging
```bash
# If container fails
docker logs demestihas-iris --tail 50

# Restart if needed
docker-compose restart iris

# Check health
docker inspect demestihas-iris --format='{{.State.Health.Status}}'
```

Build this step by step. IRIS should bridge the clinical-business divide in every post, using my specific voice patterns.
