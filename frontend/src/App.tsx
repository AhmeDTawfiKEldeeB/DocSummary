import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { LandingHero } from './components/LandingHero';
import { FileUpload } from './components/FileUpload';
import { BlueHandLoader } from './components/BlueHandLoader';
import { SummaryWorkspace } from './components/SummaryWorkspace';
import { ToastContainer } from './components/Toast';
import type { ToastMessage } from './components/Toast';
import { useSummaryStreaming } from './hooks/useSummaryStreaming';
import type { SamplePaper } from './utils/samplePapers';
import { AlertCircle, RotateCcw } from 'lucide-react';

export const App: React.FC = () => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const {
    file,
    setFile,
    stage,
    jobInfo,
    summaryText,
    isStreaming,
    isCompleted,
    error,
    tableOfContents,
    tokenCount,
    elapsedSeconds,
    startSummarization,
    cancelSummarization,
    reset,
  } = useSummaryStreaming();

  const addToast = (type: 'success' | 'error' | 'info', title: string, description?: string) => {
    const id = Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
    setToasts((prev) => [...prev, { id, type, title, description }]);
    setTimeout(() => {
      dismissToast(id);
    }, 4500);
  };

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleSelectSample = (paper: SamplePaper) => {
    const simulatedFile = new File(['%PDF-1.4 simulated data'], paper.filename, {
      type: 'application/pdf',
    });
    setFile(simulatedFile);
    addToast(
      'info',
      'Document Selected',
      `Selected "${paper.title}". Uploading to backend...`
    );
    startSummarization(simulatedFile);
  };

  const handleStartAnalysis = () => {
    if (!file) {
      addToast('error', 'No Document', 'Please upload or select a PDF document first.');
      return;
    }
    startSummarization(file);
  };

  // The summary workspace is shown ONLY once the first token has arrived
  const inSummaryWorkspace = summaryText.length > 0;

  // The blue hand animation stays active continuously from upload until the first token arrives
  const isWorking = !inSummaryWorkspace && stage !== 'IDLE' && stage !== 'FAILED';

  return (
    <div className="min-h-screen bg-white text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Top Navigation */}
      <Navbar onReset={reset} canReset={stage !== 'IDLE'} />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col justify-center bg-white">
        {/* State 1: IDLE - Landing Hero & File Upload */}
        {stage === 'IDLE' && (
          <div className="py-6 sm:py-10 space-y-8 animate-fadeIn bg-white">
            <LandingHero onSelectSample={handleSelectSample} />
            <FileUpload
              selectedFile={file}
              onSelectFile={setFile}
              onAnalyze={handleStartAnalysis}
              isLoading={false}
              onError={(msg) => addToast('error', 'Validation Error', msg)}
            />
          </div>
        )}

        {/* State 2: Document Processing - Blue Hand Animation (Active until first token) */}
        {isWorking && (
          <div className="py-16 px-4 animate-fadeIn bg-white">
            <BlueHandLoader onCancel={cancelSummarization} />
          </div>
        )}

        {/* State 3: Summary Workspace (Live token streaming & TOC) */}
        {inSummaryWorkspace && (
          <div className="animate-fadeIn bg-white">
            <SummaryWorkspace
              filename={file?.name || jobInfo?.filename || 'Document'}
              pipeline={jobInfo?.pipeline || 'LARGE_DOC'}
              totalPages={jobInfo?.totalPages || 32}
              summaryText={summaryText}
              isStreaming={isStreaming}
              isCompleted={isCompleted}
              tableOfContents={tableOfContents}
              tokenCount={tokenCount}
              elapsedSeconds={elapsedSeconds}
              onReset={reset}
              onToast={addToast}
            />
          </div>
        )}

        {/* State 4: Error State */}
        {stage === 'FAILED' && (
          <div className="max-w-lg mx-auto p-8 rounded-2xl bg-white border border-rose-200 shadow-sm my-12 text-center animate-fadeIn">
            <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto mb-4 border border-rose-100">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900">
              Summarization Failed
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
              {error || 'An unexpected error occurred during document processing.'}
            </p>
            <div className="mt-6 flex items-center justify-center space-x-3">
              <button
                onClick={() => startSummarization(file || undefined)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-colors flex items-center space-x-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Retry Analysis</span>
              </button>
              <button
                onClick={reset}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 transition-colors"
              >
                Choose Another Document
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto py-6 border-t border-slate-100 text-center text-xs text-slate-400 bg-white">
        <p>DocSummary • Autonomous Multi-Pipeline Research Paper & Document Summarizer</p>
        <p className="mt-1 text-[11px] text-slate-400">
          Powered by FastAPI + Celery + PostgreSQL
        </p>
      </footer>

      {/* Floating Toast Notification Container */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
};

export default App;
