import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import type {
  JobCreateResult,
  ProcessingStage,
  SummaryEvent,
  TOCItem,
} from '../services';
import { backendSummaryService } from '../services/summaryService';
import { extractTOC } from '../utils/markdownParser';

export function useSummaryStreaming() {
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<ProcessingStage>('IDLE');
  const [jobInfo, setJobInfo] = useState<JobCreateResult | null>(null);
  const [summaryText, setSummaryText] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  const abortControllerRef = useRef<AbortController | null>(null);
  const timerIntervalRef = useRef<number | null>(null);

  // Dynamic Table of Contents extracted whenever summaryText updates
  const tableOfContents = useMemo<TOCItem[]>(() => {
    return extractTOC(summaryText);
  }, [summaryText]);

  // Rough token estimation: words * 1.3
  const tokenCount = useMemo(() => {
    if (!summaryText) return 0;
    const words = summaryText.trim().split(/\s+/).filter(Boolean);
    return Math.round(words.length * 1.33);
  }, [summaryText]);

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    setFile(null);
    setStage('IDLE');
    setJobInfo(null);
    setSummaryText('');
    setIsStreaming(false);
    setIsCompleted(false);
    setError(null);
    setProgress(0);
    setStatusMessage('');
    setElapsedSeconds(0);
  }, []);

  const cancelSummarization = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    setIsStreaming(false);
    setStatusMessage('Operation canceled.');
    setStage('IDLE');
  }, []);

  const startSummarization = useCallback(
    async (fileToProcess?: File) => {
      const activeFile = fileToProcess || file;
      if (!activeFile) {
        setError('No document selected. Please provide a PDF document.');
        return;
      }

      setError(null);
      setSummaryText('');
      setIsStreaming(false);
      setIsCompleted(false);
      setProgress(5);
      setElapsedSeconds(0);
      setStage('UPLOADING');
      setStatusMessage(`Uploading ${activeFile.name}...`);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const startTime = Date.now();
      timerIntervalRef.current = window.setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);

      const service = backendSummaryService;

      try {
        // Step 1: Upload document to backend
        const createdJob = await service.uploadDocument(activeFile, {
          signal: controller.signal,
        });

        setJobInfo(createdJob);
        setProgress(25);
        setStage('PARSING');
        setStatusMessage('Document uploaded. Parsing structure & extracting pages...');

        // Step 2: Stream summary from backend SSE endpoint
        await service.streamSummary(
          createdJob.jobId,
          (event: SummaryEvent) => {
            if (controller.signal.aborted) return;

            if (event.type === 'stage') {
              setStage(event.stage);
              setProgress(event.progress);
              setStatusMessage(event.message);
              if (event.pipeline && createdJob) {
                setJobInfo((prev) =>
                  prev
                    ? {
                        ...prev,
                        pipeline: event.pipeline!,
                        totalPages: event.totalPages || prev.totalPages,
                      }
                    : prev
                );
              }
            } else if (event.type === 'token') {
              setIsStreaming(true);
              setStage('SUMMARIZING');
              setSummaryText((prev) => prev + event.token);
              setProgress(85);
            } else if (event.type === 'done') {
              setIsStreaming(false);
              setIsCompleted(true);
              setStage('COMPLETED');
              setProgress(100);
              setStatusMessage('Summary generation complete.');
              if (event.summary) {
                setSummaryText(event.summary);
              }
              if (timerIntervalRef.current) {
                clearInterval(timerIntervalRef.current);
                timerIntervalRef.current = null;
              }
            } else if (event.type === 'error') {
              setIsStreaming(false);
              setStage('FAILED');
              setError(event.error);
              setStatusMessage(`Error: ${event.error}`);
              if (timerIntervalRef.current) {
                clearInterval(timerIntervalRef.current);
                timerIntervalRef.current = null;
              }
            }
          },
          {
            signal: controller.signal,
          }
        );
      } catch (err: unknown) {
        if (controller.signal.aborted) return;
        const msg = err instanceof Error ? err.message : 'Failed to process document';
        setError(msg);
        setStage('FAILED');
        setIsStreaming(false);
        setStatusMessage(`Error: ${msg}`);
        if (timerIntervalRef.current) {
          clearInterval(timerIntervalRef.current);
          timerIntervalRef.current = null;
        }
      }
    },
    [file]
  );

  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    file,
    setFile,
    stage,
    jobInfo,
    summaryText,
    isStreaming,
    isCompleted,
    error,
    progress,
    statusMessage,
    tableOfContents,
    tokenCount,
    elapsedSeconds,
    startSummarization,
    cancelSummarization,
    reset,
  };
}
