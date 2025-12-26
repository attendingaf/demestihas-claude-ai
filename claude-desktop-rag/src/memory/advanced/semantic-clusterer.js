import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';
import { config } from '../../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class SemanticClusterer {
  constructor() {
    this.clusters = new Map();
    this.memories = new Map();
    this.topics = new Map();
    this.bridges = new Map();
    this.minClusterSize = 3;
    this.maxClusterSize = 50;
    this.similarityThreshold = 0.75;
    this.mergeThreshold = 0.85;
  }

  async initialize() {
    logger.info('Initializing semantic clusterer...');
    this.loadExistingClusters();
    logger.info('Semantic clusterer initialized');
  }

  async addMemory(memory) {
    const memoryId = memory.id || uuidv4();
    
    const enrichedMemory = {
      ...memory,
      id: memoryId,
      clusterId: null,
      addedAt: Date.now()
    };
    
    this.memories.set(memoryId, enrichedMemory);
    
    // Find best cluster
    const bestCluster = await this.findBestCluster(memory.embedding);
    
    if (bestCluster) {
      await this.addToCluster(memoryId, bestCluster.id);
    } else {
      // Consider creating new cluster if enough orphan memories
      await this.considerNewCluster();
    }
    
    return memoryId;
  }

  async performClustering() {
    logger.info('Performing clustering...');
    
    const unclustered = Array.from(this.memories.values())
      .filter(m => !m.clusterId);
    
    if (unclustered.length < this.minClusterSize) {
      logger.debug('Not enough unclustered memories for clustering');
      return Array.from(this.clusters.values());
    }
    
    // Perform HDBSCAN-inspired clustering
    const clusters = await this.hdbscanClustering(unclustered);
    
    // Merge similar clusters
    await this.mergeSimilarClusters();
    
    // Identify bridges between clusters
    await this.identifyBridges();
    
    // Extract topics for each cluster
    await this.extractTopicsForClusters();
    
    logger.info(`Clustering complete: ${this.clusters.size} clusters formed`);
    
    return Array.from(this.clusters.values());
  }

  async hdbscanClustering(memories) {
    const newClusters = [];
    const visited = new Set();
    
    for (const memory of memories) {
      if (visited.has(memory.id)) continue;
      
      // Find neighbors
      const neighbors = await this.findNeighbors(memory, memories, this.similarityThreshold);
      
      if (neighbors.length >= this.minClusterSize - 1) {
        // Form new cluster
        const cluster = await this.formCluster(memory, neighbors, visited);
        newClusters.push(cluster);
      }
    }
    
    return newClusters;
  }

  async formCluster(seed, neighbors, visited) {
    const clusterId = uuidv4();
    const members = [seed.id];
    visited.add(seed.id);
    
    // Expand cluster
    const toProcess = [...neighbors];
    
    while (toProcess.length > 0 && members.length < this.maxClusterSize) {
      const current = toProcess.shift();
      
      if (visited.has(current.id)) continue;
      
      visited.add(current.id);
      members.push(current.id);
      
      // Find more neighbors
      const moreNeighbors = await this.findNeighbors(
        current,
        Array.from(this.memories.values()),
        this.similarityThreshold * 0.9 // Slightly lower threshold for expansion
      );
      
      toProcess.push(...moreNeighbors.filter(n => !visited.has(n.id)));
    }
    
    // Create cluster
    const cluster = {
      id: clusterId,
      members,
      centroid: await this.calculateCentroid(members),
      created: Date.now(),
      lastUpdated: Date.now(),
      topic: null,
      stability: 1.0
    };
    
    this.clusters.set(clusterId, cluster);
    
    // Update memory cluster assignments
    members.forEach(memId => {
      const memory = this.memories.get(memId);
      if (memory) {
        memory.clusterId = clusterId;
      }
    });
    
    return cluster;
  }

  async findNeighbors(memory, candidates, threshold) {
    const neighbors = [];
    
    for (const candidate of candidates) {
      if (candidate.id === memory.id) continue;
      
      const similarity = this.calculateSimilarity(memory.embedding, candidate.embedding);
      
      if (similarity >= threshold) {
        neighbors.push(candidate);
      }
    }
    
    return neighbors;
  }

  calculateSimilarity(embedding1, embedding2) {
    if (!embedding1 || !embedding2) return 0;
    
    // Cosine similarity
    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;
    
    for (let i = 0; i < embedding1.length; i++) {
      dotProduct += embedding1[i] * embedding2[i];
      norm1 += embedding1[i] * embedding1[i];
      norm2 += embedding2[i] * embedding2[i];
    }
    
    norm1 = Math.sqrt(norm1);
    norm2 = Math.sqrt(norm2);
    
    if (norm1 === 0 || norm2 === 0) return 0;
    
    return dotProduct / (norm1 * norm2);
  }

  async calculateCentroid(memberIds) {
    const embeddings = memberIds
      .map(id => this.memories.get(id))
      .filter(m => m && m.embedding)
      .map(m => m.embedding);
    
    if (embeddings.length === 0) return null;
    
    const dimensions = embeddings[0].length;
    const centroid = new Array(dimensions).fill(0);
    
    // Calculate mean
    for (const embedding of embeddings) {
      for (let i = 0; i < dimensions; i++) {
        centroid[i] += embedding[i];
      }
    }
    
    for (let i = 0; i < dimensions; i++) {
      centroid[i] /= embeddings.length;
    }
    
    return centroid;
  }

  async findBestCluster(embedding) {
    let bestCluster = null;
    let bestSimilarity = 0;
    
    for (const cluster of this.clusters.values()) {
      if (!cluster.centroid) continue;
      
      const similarity = this.calculateSimilarity(embedding, cluster.centroid);
      
      if (similarity > this.similarityThreshold && similarity > bestSimilarity) {
        bestSimilarity = similarity;
        bestCluster = cluster;
      }
    }
    
    return bestCluster;
  }

  async addToCluster(memoryId, clusterId) {
    const cluster = this.clusters.get(clusterId);
    const memory = this.memories.get(memoryId);
    
    if (!cluster || !memory) return;
    
    cluster.members.push(memoryId);
    memory.clusterId = clusterId;
    cluster.lastUpdated = Date.now();
    
    // Recalculate centroid
    cluster.centroid = await this.calculateCentroid(cluster.members);
    
    // Check if cluster needs splitting
    if (cluster.members.length > this.maxClusterSize) {
      await this.splitCluster(clusterId);
    }
  }

  async splitCluster(clusterId) {
    const cluster = this.clusters.get(clusterId);
    if (!cluster) return;
    
    const members = cluster.members.map(id => this.memories.get(id)).filter(Boolean);
    
    // Use k-means with k=2 to split
    const { cluster1, cluster2 } = await this.kMeansSplit(members);
    
    // Update original cluster
    cluster.members = cluster1.map(m => m.id);
    cluster.centroid = await this.calculateCentroid(cluster.members);
    
    // Create new cluster
    const newClusterId = uuidv4();
    const newCluster = {
      id: newClusterId,
      members: cluster2.map(m => m.id),
      centroid: await this.calculateCentroid(cluster2.map(m => m.id)),
      created: Date.now(),
      lastUpdated: Date.now(),
      topic: null,
      stability: 0.8
    };
    
    this.clusters.set(newClusterId, newCluster);
    
    // Update memory assignments
    cluster2.forEach(memory => {
      memory.clusterId = newClusterId;
    });
    
    logger.debug(`Split cluster ${clusterId} into two clusters`);
  }

  async kMeansSplit(memories) {
    // Simple k-means with k=2
    const center1 = memories[0].embedding;
    const center2 = memories[Math.floor(memories.length / 2)].embedding;
    
    let cluster1 = [];
    let cluster2 = [];
    
    // Assign to nearest center
    for (const memory of memories) {
      const dist1 = this.calculateSimilarity(memory.embedding, center1);
      const dist2 = this.calculateSimilarity(memory.embedding, center2);
      
      if (dist1 > dist2) {
        cluster1.push(memory);
      } else {
        cluster2.push(memory);
      }
    }
    
    return { cluster1, cluster2 };
  }

  async mergeSimilarClusters() {
    const clusterList = Array.from(this.clusters.values());
    const toMerge = [];
    
    for (let i = 0; i < clusterList.length; i++) {
      for (let j = i + 1; j < clusterList.length; j++) {
        const similarity = this.calculateSimilarity(
          clusterList[i].centroid,
          clusterList[j].centroid
        );
        
        if (similarity > this.mergeThreshold) {
          toMerge.push([clusterList[i].id, clusterList[j].id]);
        }
      }
    }
    
    // Merge clusters
    for (const [id1, id2] of toMerge) {
      await this.mergeClusters(id1, id2);
    }
  }

  async mergeClusters(clusterId1, clusterId2) {
    const cluster1 = this.clusters.get(clusterId1);
    const cluster2 = this.clusters.get(clusterId2);
    
    if (!cluster1 || !cluster2) return;
    
    // Merge into cluster1
    cluster1.members.push(...cluster2.members);
    cluster1.centroid = await this.calculateCentroid(cluster1.members);
    cluster1.lastUpdated = Date.now();
    cluster1.stability = (cluster1.stability + cluster2.stability) / 2;
    
    // Update memory assignments
    cluster2.members.forEach(memId => {
      const memory = this.memories.get(memId);
      if (memory) {
        memory.clusterId = clusterId1;
      }
    });
    
    // Remove cluster2
    this.clusters.delete(clusterId2);
    
    logger.debug(`Merged cluster ${clusterId2} into ${clusterId1}`);
  }

  async identifyBridges() {
    this.bridges.clear();
    
    for (const memory of this.memories.values()) {
      if (!memory.clusterId) continue;
      
      // Check similarity to other clusters
      const similarities = [];
      
      for (const cluster of this.clusters.values()) {
        if (cluster.id === memory.clusterId) continue;
        
        const similarity = this.calculateSimilarity(memory.embedding, cluster.centroid);
        
        if (similarity > this.similarityThreshold * 0.8) {
          similarities.push({ clusterId: cluster.id, similarity });
        }
      }
      
      if (similarities.length > 0) {
        this.bridges.set(memory.id, {
          memoryId: memory.id,
          primaryCluster: memory.clusterId,
          connections: similarities
        });
      }
    }
    
    logger.debug(`Identified ${this.bridges.size} bridge memories`);
  }

  async extractTopics() {
    const topics = [];
    
    for (const cluster of this.clusters.values()) {
      const topic = await this.extractClusterTopic(cluster);
      if (topic) {
        topics.push(topic);
        cluster.topic = topic.id;
      }
    }
    
    return topics;
  }

  async extractTopicsForClusters() {
    for (const cluster of this.clusters.values()) {
      const topic = await this.extractClusterTopic(cluster);
      if (topic) {
        this.topics.set(topic.id, topic);
        cluster.topic = topic.id;
      }
    }
  }

  async extractClusterTopic(cluster) {
    const memories = cluster.members
      .map(id => this.memories.get(id))
      .filter(Boolean);
    
    if (memories.length === 0) return null;
    
    // Extract common themes
    const contents = memories.map(m => m.content || '').filter(c => c);
    const metadata = memories.map(m => m.metadata || {});
    
    // Simple keyword extraction (in production, use NLP)
    const keywords = this.extractKeywords(contents);
    const types = this.extractCommonTypes(metadata);
    
    const topic = {
      id: uuidv4(),
      clusterId: cluster.id,
      label: keywords.slice(0, 3).join('-') || 'cluster-' + cluster.id.slice(0, 8),
      keywords,
      types,
      memberCount: cluster.members.length,
      stability: cluster.stability
    };
    
    return topic;
  }

  extractKeywords(contents) {
    const wordFreq = new Map();
    
    for (const content of contents) {
      const words = content.toLowerCase().split(/\s+/);
      
      for (const word of words) {
        if (word.length > 3) {
          wordFreq.set(word, (wordFreq.get(word) || 0) + 1);
        }
      }
    }
    
    // Sort by frequency
    const sorted = Array.from(wordFreq.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([word]) => word);
    
    return sorted.slice(0, 10);
  }

  extractCommonTypes(metadata) {
    const typeFreq = new Map();
    
    for (const meta of metadata) {
      if (meta.type) {
        typeFreq.set(meta.type, (typeFreq.get(meta.type) || 0) + 1);
      }
    }
    
    return Array.from(typeFreq.keys());
  }

  async findSimilarInCluster(embedding, threshold = 0.7) {
    const similar = [];
    
    for (const memory of this.memories.values()) {
      const similarity = this.calculateSimilarity(embedding, memory.embedding);
      
      if (similarity >= threshold) {
        similar.push({
          ...memory,
          similarity
        });
      }
    }
    
    similar.sort((a, b) => b.similarity - a.similarity);
    
    return similar;
  }

  async considerNewCluster() {
    const unclustered = Array.from(this.memories.values())
      .filter(m => !m.clusterId);
    
    if (unclustered.length >= this.minClusterSize) {
      await this.performClustering();
    }
  }

  loadExistingClusters() {
    // In production, load from persistent storage
    logger.debug('Loading existing clusters from storage');
  }

  async getMetrics() {
    const clusterSizes = Array.from(this.clusters.values()).map(c => c.members.length);
    
    return {
      totalMemories: this.memories.size,
      totalClusters: this.clusters.size,
      avgClusterSize: clusterSizes.length > 0
        ? clusterSizes.reduce((a, b) => a + b, 0) / clusterSizes.length
        : 0,
      largestCluster: Math.max(...clusterSizes, 0),
      smallestCluster: Math.min(...clusterSizes, 0),
      bridges: this.bridges.size,
      topics: this.topics.size,
      clusteringQuality: this.calculateClusteringQuality()
    };
  }

  calculateClusteringQuality() {
    // Silhouette coefficient approximation
    let totalScore = 0;
    let count = 0;
    
    for (const memory of this.memories.values()) {
      if (!memory.clusterId || !memory.embedding) continue;
      
      const cluster = this.clusters.get(memory.clusterId);
      if (!cluster || !cluster.centroid) continue;
      
      // Intra-cluster distance
      const intraDistance = 1 - this.calculateSimilarity(memory.embedding, cluster.centroid);
      
      // Inter-cluster distance (to nearest cluster)
      let minInterDistance = 1;
      for (const otherCluster of this.clusters.values()) {
        if (otherCluster.id === cluster.id || !otherCluster.centroid) continue;
        
        const distance = 1 - this.calculateSimilarity(memory.embedding, otherCluster.centroid);
        minInterDistance = Math.min(minInterDistance, distance);
      }
      
      // Silhouette score
      const score = (minInterDistance - intraDistance) / Math.max(intraDistance, minInterDistance);
      totalScore += score;
      count++;
    }
    
    return count > 0 ? totalScore / count : 0;
  }
}

export default new SemanticClusterer();