import express from 'express';
import cors from 'cors';

const app = express();
app.use(cors());
app.use(express.json());

const IRIS_PERSONALITY = {
  name: "IRIS",
  role: "Clinical & Business Bridge",
  voicePatterns: [
    "from both clinical and business perspectives",
    "bridging clinical excellence with business acumen",
    "integrating patient care with operational efficiency",
    "Shoot me a DM to discuss further"
  ],
  expertise: [
    "Healthcare transformation",
    "Clinical operations",
    "Business strategy",
    "Digital health innovation"
  ]
};

const HIPAA_PATTERNS = [
  /\b\d{3}-\d{2}-\d{4}\b/,  // SSN
  /\b[A-Z][a-z]+\s+[A-Z][a-z]+\b.*diagnosed/i,  // Patient names with diagnosis
  /patient\s+[A-Z][a-z]+\s+[A-Z][a-z]+/i,  // Direct patient references
  /MRN\s*:?\s*\d+/i,  // Medical record numbers
  /DOB\s*:?\s*\d{1,2}\/\d{1,2}\/\d{4}/i  // Dates of birth
];

function checkHIPAACompliance(text) {
  const violations = [];
  for (const pattern of HIPAA_PATTERNS) {
    if (pattern.test(text)) {
      violations.push(`Potential HIPAA violation detected: ${pattern}`);
    }
  }
  return {
    compliant: violations.length === 0,
    violations
  };
}

function generateLinkedInPost(topic) {
  const posts = {
    transformation: `Healthcare transformation requires a dual lens approach - from both clinical and business perspectives. When we integrate operational excellence with patient-centered care, we create sustainable systems that benefit all stakeholders. The key is understanding that clinical quality and business efficiency aren't competing priorities; they're complementary forces that drive meaningful change. In today's evolving healthcare landscape, organizations that bridge this divide will lead the way forward. Shoot me a DM to discuss how we can transform your healthcare delivery model.`,

    innovation: `Digital health innovation must balance clinical rigor with business viability. From both clinical and business perspectives, successful implementations require deep understanding of workflow impacts and ROI metrics. We're not just implementing technology; we're reimagining care delivery models that enhance patient outcomes while optimizing operational efficiency. The organizations winning in this space understand that innovation isn't about the latest tech - it's about meaningful integration that serves both patients and providers. Shoot me a DM to explore strategic innovation opportunities.`,

    leadership: `Healthcare leadership demands fluency in both clinical excellence and business acumen. Bridging clinical and business perspectives allows us to make decisions that honor our mission while ensuring sustainability. Today's healthcare leaders must navigate complex regulatory environments, drive quality improvements, and maintain financial health - all while keeping patient care at the center. This integrated approach isn't just beneficial; it's essential for thriving in modern healthcare. Shoot me a DM to discuss leadership strategies that work.`
  };

  return posts[topic] || posts.transformation;
}

function generateInstagramPost(topic) {
  const posts = {
    transformation: {
      caption: `🏥 Healthcare transformation through dual perspectives\n\n✨ Clinical excellence meets business strategy\n📊 Data-driven decisions with patient focus\n🚀 Innovation that scales sustainably\n💡 Solutions that work for all stakeholders\n\nBridging clinical and business worlds to create better healthcare outcomes.\n\n#HealthcareInnovation #ClinicalExcellence #HealthTech #DigitalHealth #HealthcareLeadership #BusinessStrategy`,
      cta: "Shoot me a DM to transform your healthcare delivery! 💬"
    },

    innovation: {
      caption: `💡 Innovation in healthcare requires balance\n\n🩺 Clinical rigor + 📈 Business viability\n🔬 Evidence-based + 💰 ROI-focused\n👥 Patient-centered + 🏢 Operationally efficient\n\nFrom both clinical and business perspectives, true innovation serves everyone.\n\n#HealthInnovation #DigitalHealth #HealthcareTransformation #MedTech #ClinicalInnovation`,
      cta: "Shoot me a DM to explore innovation opportunities! 🚀"
    },

    leadership: {
      caption: `🌟 Modern healthcare leadership essentials:\n\n✅ Clinical expertise\n✅ Business acumen\n✅ Strategic vision\n✅ Operational excellence\n\nBridging clinical and business perspectives for sustainable success.\n\n#HealthcareLeadership #ClinicalLeadership #HealthcareManagement #Leadership #HealthcareBusiness`,
      cta: "Shoot me a DM to discuss leadership strategies! 💪"
    }
  };

  return posts[topic] || posts.transformation;
}

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    agent: 'IRIS',
    role: 'Clinical & Business Bridge',
    timestamp: new Date().toISOString()
  });
});

app.post('/generate', (req, res) => {
  const { platform, topic, customContent } = req.body;

  if (!platform || !['linkedin', 'instagram'].includes(platform)) {
    return res.status(400).json({ error: 'Platform must be "linkedin" or "instagram"' });
  }

  let content;

  if (customContent) {
    const hipaaCheck = checkHIPAACompliance(customContent);
    if (!hipaaCheck.compliant) {
      return res.status(400).json({
        error: 'HIPAA compliance check failed',
        violations: hipaaCheck.violations
      });
    }
    content = customContent;
  } else {
    if (platform === 'linkedin') {
      content = generateLinkedInPost(topic || 'transformation');
    } else {
      content = generateInstagramPost(topic || 'transformation');
    }
  }

  const wordCount = typeof content === 'string'
    ? content.split(/\s+/).length
    : content.caption.split(/\s+/).length;

  res.json({
    agent: 'IRIS',
    platform,
    topic: topic || 'transformation',
    content,
    wordCount,
    hipaaCompliant: true,
    personality: IRIS_PERSONALITY,
    timestamp: new Date().toISOString()
  });
});

app.post('/check-compliance', (req, res) => {
  const { text } = req.body;

  if (!text) {
    return res.status(400).json({ error: 'Text is required for compliance check' });
  }

  const result = checkHIPAACompliance(text);

  res.json({
    text,
    ...result,
    checkedAt: new Date().toISOString()
  });
});

app.get('/personality', (req, res) => {
  res.json(IRIS_PERSONALITY);
});

const PORT = 8005;
app.listen(PORT, () => {
  console.log(`IRIS Agent running on port ${PORT}`);
  console.log('Role: Bridging clinical and business perspectives');
  console.log('Endpoints:');
  console.log('  GET  /health - Health check');
  console.log('  POST /generate - Generate social media content');
  console.log('  POST /check-compliance - Check HIPAA compliance');
  console.log('  GET  /personality - Get IRIS personality profile');
});
