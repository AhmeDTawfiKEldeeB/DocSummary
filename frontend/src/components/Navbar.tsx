import React from 'react';
import { FileText, RotateCcw } from 'lucide-react';

interface NavbarProps {
  onReset?: () => void;
  canReset?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onReset, canReset }) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand identity */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={onReset}>
          <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <span className="text-base font-bold tracking-tight text-slate-900">
              DocSummary
            </span>
            <p className="text-[11px] text-slate-500 hidden sm:block">
              AI Document & Research Paper Summarization
            </p>
          </div>
        </div>

        {/* Right Action Controls */}
        <div className="flex items-center space-x-3">
          {canReset && (
            <button
              onClick={onReset}
              className="flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-xl transition-colors shadow-sm"
              title="Upload another document"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>New Doc</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
