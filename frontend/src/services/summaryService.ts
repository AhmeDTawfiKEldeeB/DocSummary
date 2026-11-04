import type {
  ISummaryService,
  JobCreateResult,
  PipelineType,
  ServiceOptions,
  SummaryEvent,
} from './types';

export class BackendSummaryService implements ISummaryService {
  readonly modeName = 'api' as const;
  private apiBaseUrl: string;

  constructor(apiBaseUrl?: string) {
    this.apiBaseUrl =
      apiBaseUrl ||
      (import.meta.env.VITE_API_BASE_URL as string) ||
      'http://localhost:8000/api/v1';
  }

  async uploadDocument(file: File, options?: ServiceOptions): Promise<JobCreateResult> {
    const formData = new FormData();
    formData.append('file', file);

    const uploadUrl = `${this.apiBaseUrl}/summarize`;
    const response = await fetch(uploadUrl, {
      method: 'POST',
      body: formData,
      signal: options?.signal,
    });

    if (!response.ok) {
      let errorDetail = `Upload failed with HTTP ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fallback
      }
      throw new Error(errorDetail);
    }

    const data = await response.json();
    return {
      jobId: data.job_id,
      status: data.status,
      pipeline: data.pipeline as PipelineType,
      totalPages: data.total_pages,
      filename: file.name,
    };
  }

  async streamSummary(
    jobId: string,
    onEvent: (event: SummaryEvent) => void,
    options?: ServiceOptions
  ): Promise<void> {
    const streamUrl = `${this.apiBaseUrl}/jobs/${jobId}/stream`;
    const statusUrl = `${this.apiBaseUrl}/jobs/${jobId}`;
    const signal = options?.signal;

    return new Promise<void>((resolve, reject) => {
      let isDone = false;
      const eventSource = new EventSource(streamUrl);

      const cleanup = () => {
        isDone = true;
        eventSource.close();
      };

      if (signal) {
        signal.addEventListener(
          'abort',
          () => {
            cleanup();
            resolve();
          },
          { once: true }
        );
      }

      eventSource.addEventListener('status', (e: MessageEvent) => {
        try {
          const payload = JSON.parse(e.data);
          const stage =
            payload.status === 'PROCESSING'
              ? 'SUMMARIZING'
              : payload.status === 'PENDING'
              ? 'PARSING'
              : 'IDLE';

          onEvent({
            type: 'stage',
            stage,
            progress: payload.status === 'PROCESSING' ? 70 : 40,
            message: `Document status: ${payload.status} (${payload.pipeline || 'Pipeline'}, ${payload.total_pages || '?'} pages)`,
            pipeline: payload.pipeline,
            totalPages: payload.total_pages,
          });
        } catch {
          // ignore
        }
      });

      eventSource.addEventListener('token', (e: MessageEvent) => {
        try {
          const payload = JSON.parse(e.data);
          if (payload.token) {
            onEvent({
              type: 'token',
              token: payload.token,
            });
          }
        } catch {
          // ignore
        }
      });

      eventSource.addEventListener('done', (e: MessageEvent) => {
        try {
          const payload = JSON.parse(e.data);
          onEvent({
            type: 'done',
            status: 'COMPLETED',
            summary: payload.summary || '',
          });
        } catch {
          onEvent({
            type: 'done',
            status: 'COMPLETED',
            summary: '',
          });
        }
        cleanup();
        resolve();
      });

      eventSource.addEventListener('error', async () => {
        if (isDone) return;
        cleanup();

        // Fallback poll verification: check if job succeeded or failed in DB
        try {
          const resp = await fetch(statusUrl);
          if (resp.ok) {
            const data = await resp.json();
            if (data.status === 'COMPLETED' && data.summary) {
              onEvent({
                type: 'done',
                status: 'COMPLETED',
                summary: data.summary,
              });
              return resolve();
            } else if (data.status === 'FAILED') {
              const errMsg = data.error || 'Document processing failed on cluster.';
              onEvent({ type: 'error', error: errMsg });
              return reject(new Error(errMsg));
            }
          }
        } catch {
          // fallback failed
        }

        const fallbackMsg = 'Disconnected from backend summary stream.';
        onEvent({ type: 'error', error: fallbackMsg });
        reject(new Error(fallbackMsg));
      });
    });
  }
}

export const backendSummaryService = new BackendSummaryService();
