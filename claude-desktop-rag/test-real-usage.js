import { MemoryStore } from './src/memory/memory-store.js';
import { ContextRetriever } from './src/memory/context-retriever.js';

const memory = new MemoryStore();
const retriever = new ContextRetriever();

async function test() {
  // Store some memories
  await memory.store({
    content: "The Demestihas family uses a multi-agent AI system",
    metadata: { project: "demestihas-mas", type: "fact" }
  });
  
  await memory.store({
    content: "Yanay.ai is the orchestration layer",
    metadata: { project: "demestihas-mas", type: "architecture" }
  });
  
  // Retrieve relevant context
  const context = await retriever.retrieve("Tell me about the family AI system");
  console.log("Retrieved context:", context);
}

test();
