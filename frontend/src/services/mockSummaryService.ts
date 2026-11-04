import type {
  ISummaryService,
  JobCreateResult,
  PipelineType,
  ServiceOptions,
  SummaryEvent,
} from './types';
import { SAMPLE_RESEARCH_PAPERS } from '../utils/samplePapers';

export class MockSummaryService implements ISummaryService {
  readonly modeName = 'mock' as const;

  // Cache job metadata so streamSummary can lookup the document
  private jobCache = new Map<
    string,
    {
      filename: string;
      pipeline: PipelineType;
      totalPages: number;
      sampleText: string;
    }
  >();

  private delay(ms: number, signal?: AbortSignal): Promise<void> {
    return new Promise((resolve, reject) => {
      if (signal?.aborted) {
        return reject(new DOMException('Operation aborted by user', 'AbortError'));
      }
      const timer = setTimeout(() => resolve(), ms);
      signal?.addEventListener(
        'abort',
        () => {
          clearTimeout(timer);
          reject(new DOMException('Operation aborted by user', 'AbortError'));
        },
        { once: true }
      );
    });
  }

  async uploadDocument(file: File, options?: ServiceOptions): Promise<JobCreateResult> {
    const signal = options?.signal;
    if (signal?.aborted) {
      throw new DOMException('Upload aborted', 'AbortError');
    }

    // Check error simulation flag
    if (options?.simulateError) {
      await this.delay(600, signal);
      throw new Error('Simulated Upload Error: Failed to upload document to cluster storage.');
    }

    // Simulate network upload latency (500ms)
    await this.delay(500, signal);

    // Pick matching sample text or default to DeepSeek-R1
    const matchingSample =
      SAMPLE_RESEARCH_PAPERS.find(
        (s) =>
          file.name.toLowerCase().includes(s.id) ||
          file.name.toLowerCase().includes(s.filename.toLowerCase())
      ) ||
      (file.size < 2_500_000
        ? SAMPLE_RESEARCH_PAPERS[1]
        : SAMPLE_RESEARCH_PAPERS[0]);

    const jobId = `mock-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 7)}`;
    const totalPages = matchingSample.pageCount;
    const pipeline: PipelineType = totalPages <= 15 ? 'SMALL_DOC' : 'LARGE_DOC';

    this.jobCache.set(jobId, {
      filename: file.name,
      pipeline,
      totalPages,
      sampleText: matchingSample.summaryMarkdown,
    });

    return {
      jobId,
      status: 'PENDING',
      pipeline,
      totalPages,
      filename: file.name,
    };
  }

  async streamSummary(
    jobId: string,
    onEvent: (event: SummaryEvent) => void,
    options?: ServiceOptions
  ): Promise<void> {
    const signal = options?.signal;
    const cached = this.jobCache.get(jobId);

    const filename = cached?.filename || 'research_document.pdf';
    const pipeline: PipelineType = cached?.pipeline || 'LARGE_DOC';
    const totalPages = cached?.totalPages || 32;
    const fullSummaryText = cached?.sampleText || SAMPLE_RESEARCH_PAPERS[0].summaryMarkdown;

    const startTime = Date.now();

    try {
      // Stage 1: Document Ingestion & Parsing
      onEvent({
        type: 'stage',
        stage: 'PARSING',
        progress: 25,
        message: `Extracting text layers, typography, and structural metadata from ${filename}...`,
        pipeline,
        totalPages,
      });
      await this.delay(700, signal);

      if (options?.simulateError) {
        throw new Error('Simulated Parsing Error: Document PDF stream is corrupted or unreadable.');
      }

      // Stage 2: Pipeline Selection & Planning
      onEvent({
        type: 'stage',
        stage: 'SELECTING_PIPELINE',
        progress: 55,
        message:
          pipeline === 'LARGE_DOC'
            ? `Detected ${totalPages} pages. Assigned Hierarchical Map-Reduce Pipeline for long-form synthesis.`
            : `Detected ${totalPages} pages. Assigned Single-Pass High-Throughput Pipeline.`,
        pipeline,
        totalPages,
      });
      await this.delay(750, signal);

      // Stage 3: LLM Context Assembly & First-token trigger
      onEvent({
        type: 'stage',
        stage: 'SUMMARIZING',
        progress: 80,
        message: 'Connecting to inference cluster and generating structured synthesis...',
        pipeline,
        totalPages,
      });
      await this.delay(600, signal);

      // Progressive Token-by-Token Streaming
      const words = fullSummaryText.split(' ');
      let currentIdx = 0;
      let totalTokens = 0;

      while (currentIdx < words.length) {
        if (signal?.aborted) {
          throw new DOMException('Streaming canceled by user', 'AbortError');
        }

        const chunkSize = Math.floor(Math.random() * 3) + 2;
        const nextSlice = words.slice(currentIdx, currentIdx + chunkSize);
        currentIdx += chunkSize;

        let chunkText = nextSlice.join(' ');
        if (currentIdx < words.length) {
          chunkText += ' ';
        }

        totalTokens += nextSlice.length;

        onEvent({
          type: 'token',
          token: chunkText,
        });

        let pauseMs = 18 + Math.floor(Math.random() * 15);
        if (chunkText.includes('\n\n') || chunkText.includes('---')) {
          pauseMs = 45;
        } else if (chunkText.includes('.') || chunkText.includes(':')) {
          pauseMs = 28;
        }

        await this.delay(pauseMs, signal);
      }

      // Generation Completed!
      const elapsedMs = Date.now() - startTime;
      onEvent({
        type: 'done',
        status: 'COMPLETED',
        summary: fullSummaryText,
        totalTokens: Math.round(totalTokens * 1.3),
        elapsedMs,
      });
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      const message = err instanceof Error ? err.message : 'Unknown generation failure';
      onEvent({
        type: 'error',
        error: message,
        stage: 'FAILED',
      });
      throw err;
    }
  }

  async cancel(): Promise<void> {
    // Coordinated via AbortSignal
  }
}

export const mockSummaryService = new MockSummaryService();
