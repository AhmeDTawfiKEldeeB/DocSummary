import React, { useState, useRef, useEffect } from 'react';
import {
  Download,
  FileCode,
  FileText,
  FileDown,
  Layers,
  ChevronDown,
  Loader2,
} from 'lucide-react';
import {
  exportToMarkdown,
  exportToTxt,
  exportToPdf,
  exportToDocx,
} from '../utils/exportUtils';

interface ExportDropdownProps {
  summaryMarkdown: string;
  filename: string;
  onSuccess: (formatName: string) => void;
  onError: (msg: string) => void;
}

export const ExportDropdown: React.FC<ExportDropdownProps> = ({
  summaryMarkdown,
  filename,
  onSuccess,
  onError,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const handleExport = async (format: 'md' | 'txt' | 'pdf' | 'docx') => {
    if (!summaryMarkdown) {
      onError('No summary content available to export.');
      return;
    }

    try {
      setExportingFormat(format);
      if (format === 'md') {
        exportToMarkdown(summaryMarkdown, filename);
        onSuccess('Markdown (.md)');
      } else if (format === 'txt') {
        exportToTxt(summaryMarkdown, filename);
        onSuccess('Plain Text (.txt)');
      } else if (format === 'pdf') {
        exportToPdf(summaryMarkdown, filename);
        onSuccess('PDF Document (.pdf)');
      } else if (format === 'docx') {
        await exportToDocx(summaryMarkdown, filename);
        onSuccess('Microsoft Word (.docx)');
      }
      setIsOpen(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Export failed';
      onError(`Failed to export ${format.toUpperCase()}: ${msg}`);
    } finally {
      setExportingFormat(null);
    }
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={!summaryMarkdown || !!exportingFormat}
        className="flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {exportingFormat ? (
          <Loader2 className="w-4 h-4 animate-spin text-white" />
        ) : (
          <Download className="w-4 h-4 text-white" />
        )}
        <span>Export</span>
        <ChevronDown className="w-3.5 h-3.5 text-white/80" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 rounded-xl bg-white border border-slate-200 shadow-xl p-1.5 z-50">
          <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Available Formats
          </div>

          <button
            onClick={() => handleExport('pdf')}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-colors text-left"
          >
            <FileDown className="w-4 h-4 text-rose-500" />
            <div>
              <div className="font-semibold">PDF Document (.pdf)</div>
              <div className="text-[10px] text-slate-400">Paginated with headers & styles</div>
            </div>
          </button>

          <button
            onClick={() => handleExport('docx')}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-colors text-left"
          >
            <Layers className="w-4 h-4 text-blue-600" />
            <div>
              <div className="font-semibold">Word Document (.docx)</div>
              <div className="text-[10px] text-slate-400">Microsoft Word document</div>
            </div>
          </button>

          <button
            onClick={() => handleExport('md')}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-colors text-left"
          >
            <FileCode className="w-4 h-4 text-emerald-500" />
            <div>
              <div className="font-semibold">Markdown (.md)</div>
              <div className="text-[10px] text-slate-400">Raw formatted markdown</div>
            </div>
          </button>

          <button
            onClick={() => handleExport('txt')}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-colors text-left"
          >
            <FileText className="w-4 h-4 text-slate-500" />
            <div>
              <div className="font-semibold">Plain Text (.txt)</div>
              <div className="text-[10px] text-slate-400">Clean unformatted text</div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
};
