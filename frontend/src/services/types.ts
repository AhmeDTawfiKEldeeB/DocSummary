export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export type PipelineType = 'SMALL_DOC' | 'LARGE_DOC';

export type ProcessingStage =
  | 'IDLE'
  | 'UPLOADING'
  | 'PARSING'
  | 'SELECTING_PIPELINE'
  | 'SUMMARIZING'
  | 'COMPLETED'
  | 'FAILED';

export interface JobCreateResult {
  jobId: string;
  status: JobStatus;
  pipeline: PipelineType;
  totalPages: number;
  filename: string;
}

export type SummaryEvent =
  | {
      type: 'stage';
      stage: ProcessingStage;
      progress: number;
      message: string;
      pipeline?: PipelineType;
      totalPages?: number;
    }
  | {
      type: 'token';
      token: string;
    }
  | {
      type: 'done';
      status: 'COMPLETED';
      summary: string;
      totalTokens?: number;
      elapsedMs?: number;
    }
  | {
      type: 'error';
      error: string;
      stage?: ProcessingStage;
    };

export interface ServiceOptions {
  signal?: AbortSignal;
  simulateError?: boolean;
}

export interface ISummaryService {
  readonly modeName: 'mock' | 'api';
  uploadDocument(file: File, options?: ServiceOptions): Promise<JobCreateResult>;
  streamSummary(
    jobId: string,
    onEvent: (event: SummaryEvent) => void,
    options?: ServiceOptions
  ): Promise<void>;
  cancel?(jobId: string): Promise<void>;
}

export interface TOCItem {
  id: string;
  title: string;
  level: number; // 1, 2, or 3
}
