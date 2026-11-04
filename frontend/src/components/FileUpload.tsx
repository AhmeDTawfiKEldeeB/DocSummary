import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileCheck,
  X,
  Sparkles,
  Layers,
  Zap,
} from 'lucide-react';

interface FileUploadProps {
  selectedFile: File | null;
  onSelectFile: (file: File | null) => void;
  onAnalyze: () => void;
  isLoading: boolean;
  onError: (msg: string) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  selectedFile,
  onSelectFile,
  onAnalyze,
  isLoading,
  onError,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [summaryFocus, setSummaryFocus] = useState<'comprehensive' | 'executive' | 'technical'>('comprehensive');
  const inputRef = useRef<HTMLInputElement | null>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const validateAndSetFile = (file: File) => {
    const isPdf =
      file.name.toLowerCase().endsWith('.pdf') ||
      file.type === 'application/pdf';

    if (!isPdf) {
      onError('Invalid file format. DocSummary requires a readable PDF document (.pdf).');
      return;
    }

    const MAX_SIZE = 50 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      onError('File exceeds maximum limit of 50MB. Please choose a smaller document.');
      return;
    }

    if (file.size === 0) {
      onError('Uploaded file is empty. Please select a valid document.');
      return;
    }

    onSelectFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      validateAndSetFile(droppedFile);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const estimatedPages = selectedFile
    ? Math.max(1, Math.round(selectedFile.size / (110 * 1024)))
    : 0;

  const predictedPipeline = estimatedPages > 15 ? 'LARGE_DOC' : 'SMALL_DOC';

  return (
    <div className="w-full max-w-2xl mx-auto px-4 bg-white">
      {!selectedFile ? (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => inputRef.current?.click()}
          className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-10 sm:p-14 text-center transition-all duration-150 bg-white group ${
            isDragOver
              ? 'border-blue-600 bg-blue-50/20'
              : 'border-slate-300 hover:border-blue-500 hover:bg-slate-50/50'
          }`}
        >
          <input
            type="file"
            ref={inputRef}
            onChange={handleFileChange}
            accept=".pdf,application/pdf"
            className="hidden"
          />

          <div className="w-14 h-14 mx-auto mb-4 rounded-xl bg-slate-100 text-blue-600 flex items-center justify-center group-hover:scale-105 transition-all">
            <UploadCloud className="w-7 h-7" />
          </div>

          <h3 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
            Drop your PDF here, or <span className="text-blue-600 underline">browse files</span>
          </h3>

          <p className="mt-2 text-xs sm:text-sm text-slate-500 max-w-md mx-auto">
            Supports technical papers, research articles, whitepapers, and reports (up to 50MB).
          </p>

          <div className="mt-6 flex items-center justify-center space-x-3 text-xs text-slate-400">
            <span>• PDF Document</span>
            <span>• Direct API Ingestion</span>
            <span>• Max 50MB</span>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-sm">
          <div className="flex items-start justify-between pb-6 border-b border-slate-100">
            <div className="flex items-start space-x-4 min-w-0">
              <div className="w-12 h-12 rounded-xl bg-slate-100 text-blue-600 flex items-center justify-center flex-shrink-0 border border-slate-200">
                <FileCheck className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center space-x-2">
                  <h3 className="text-base font-bold text-slate-900 truncate max-w-md">
                    {selectedFile.name}
                  </h3>
                  <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-slate-100 text-slate-700 rounded border border-slate-200">
                    PDF
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-slate-500">
                  <span>Size: {formatFileSize(selectedFile.size)}</span>
                  <span>•</span>
                  <span>Est. {estimatedPages} pages</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => onSelectFile(null)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              title="Remove file"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="my-5 p-4 rounded-xl bg-slate-50 border border-slate-200">
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-800 mb-1">
              {predictedPipeline === 'LARGE_DOC' ? (
                <>
                  <Layers className="w-4 h-4 text-blue-600" />
                  <span>Pipeline Strategy: Hierarchical Map-Reduce (Large Document)</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-blue-600" />
                  <span>Pipeline Strategy: Single-Pass Synthesis (Small Document)</span>
                </>
              )}
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {predictedPipeline === 'LARGE_DOC'
                ? 'Document exceeds 15 pages. The backend will partition text into semantic chunks and generate hierarchical section summaries.'
                : 'Document is within 15 pages. The backend will process the text within a single high-throughput context pass.'}
            </p>
          </div>

          <div className="mb-6">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              Synthesis Depth
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'comprehensive', label: 'Comprehensive', desc: 'Full deep dive with sections' },
                { id: 'executive', label: 'Executive Brief', desc: 'High-level takeaways' },
                { id: 'technical', label: 'Technical Details', desc: 'Methodology & architecture' },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setSummaryFocus(opt.id as any)}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    summaryFocus === opt.id
                      ? 'border-blue-600 bg-white ring-2 ring-blue-600/20 text-slate-900 font-semibold'
                      : 'border-slate-200 bg-white hover:border-slate-300 text-slate-600'
                  }`}
                >
                  <span className="block text-xs">{opt.label}</span>
                  <span className="block text-[10px] text-slate-500 mt-0.5 truncate">{opt.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Blue CTA Button */}
          <button
            onClick={onAnalyze}
            disabled={isLoading}
            className="w-full py-3.5 px-6 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-sm transform active:scale-[0.99] transition-all flex items-center justify-center space-x-2"
          >
            <Sparkles className="w-4 h-4" />
            <span>Analyze Document & Stream Summary</span>
          </button>
        </div>
      )}
    </div>
  );
};
