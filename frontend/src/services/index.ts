import type { ISummaryService } from './types';
import { mockSummaryService } from './mockSummaryService';
import { backendSummaryService } from './summaryService';

export * from './types';
export * from './mockSummaryService';
export * from './summaryService';

const envMode = (import.meta.env.VITE_SUMMARY_MODE as string)?.toLowerCase();
let currentMode: 'mock' | 'api' =
  (sessionStorage.getItem('DOCSUMMARY_MODE') as 'mock' | 'api') ||
  (envMode === 'mock' ? 'mock' : 'api');

export function getServiceMode(): 'mock' | 'api' {
  return currentMode;
}

export function setServiceMode(mode: 'mock' | 'api') {
  currentMode = mode;
  sessionStorage.setItem('DOCSUMMARY_MODE', mode);
}

export function getSummaryService(): ISummaryService {
  return currentMode === 'api' ? backendSummaryService : mockSummaryService;
}
