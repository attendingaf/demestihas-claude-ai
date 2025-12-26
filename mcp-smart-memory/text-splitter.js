import natural from 'natural';

class SmartTextSplitter {
  constructor(options = {}) {
    this.maxChunkSize = options.maxChunkSize || 1000;
    this.minChunkSize = options.minChunkSize || 200;
    this.overlap = options.overlap || 200;
    this.sentenceTokenizer = new natural.SentenceTokenizer();
  }

  // Split by headers (for markdown documents)
  splitByHeaders(text) {
    const chunks = [];
    const sections = text.split(/^#{1,3}\s+/m);

    for (const section of sections) {
      if (section.trim().length > this.maxChunkSize) {
        // Further split large sections
        chunks.push(...this.splitBySentences(section));
      } else if (section.trim().length > this.minChunkSize) {
        chunks.push(section.trim());
      }
    }

    return chunks;
  }

  // Split by sentences with smart boundaries
  splitBySentences(text) {
    const chunks = [];
    const sentences = this.sentenceTokenizer.tokenize(text);

    let currentChunk = '';

    for (const sentence of sentences) {
      if (currentChunk.length + sentence.length > this.maxChunkSize) {
        if (currentChunk) chunks.push(currentChunk.trim());
        currentChunk = sentence;
      } else {
        currentChunk += ' ' + sentence;
      }
    }

    if (currentChunk) chunks.push(currentChunk.trim());
    return chunks;
  }

  // Main splitting method
  split(text, documentType = 'auto') {
    // Detect document type if auto
    if (documentType === 'auto') {
      if (text.includes('# ') || text.includes('## ')) {
        documentType = 'markdown';
      } else if (text.includes('\n\n\n')) {
        documentType = 'structured';
      } else {
        documentType = 'plain';
      }
    }

    let chunks = [];

    switch (documentType) {
      case 'markdown':
        chunks = this.splitByHeaders(text);
        break;
      case 'structured':
        chunks = this.splitByParagraphs(text);
        break;
      default:
        chunks = this.splitBySentences(text);
    }

    // Add overlap between chunks
    return this.addOverlap(chunks);
  }

  splitByParagraphs(text) {
    const paragraphs = text.split(/\n\n+/);
    const chunks = [];

    let currentChunk = '';

    for (const para of paragraphs) {
      if (currentChunk.length + para.length > this.maxChunkSize) {
        if (currentChunk) chunks.push(currentChunk.trim());
        currentChunk = para;
      } else {
        currentChunk += '\n\n' + para;
      }
    }

    if (currentChunk) chunks.push(currentChunk.trim());
    return chunks;
  }

  addOverlap(chunks) {
    const overlapped = [];

    for (let i = 0; i < chunks.length; i++) {
      let chunk = chunks[i];

      // Add overlap from previous chunk
      if (i > 0 && this.overlap > 0) {
        const prevWords = chunks[i-1].split(' ');
        const overlapWords = prevWords.slice(-Math.floor(this.overlap/10));
        chunk = overlapWords.join(' ') + ' ... ' + chunk;
      }

      // Add preview of next chunk
      if (i < chunks.length - 1 && this.overlap > 0) {
        const nextWords = chunks[i+1].split(' ');
        const previewWords = nextWords.slice(0, Math.floor(this.overlap/10));
        chunk = chunk + ' ... ' + previewWords.join(' ');
      }

      overlapped.push(chunk);
    }

    return overlapped;
  }
}

export default SmartTextSplitter;
