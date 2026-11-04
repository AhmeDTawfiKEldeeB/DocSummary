import React, { useState, useEffect, useRef } from 'react';
import type {
  TOCItem,
  PipelineType,
} from '../services';
import { TableOfContents } from './TableOfContents';
import { ExportDropdown } from './ExportDropdown';
import { renderMarkdown } from '../utils/markdownParser';
import confetti from 'canvas-confetti';
import {
  Copy,
  Check,
  RotateCcw,
  Clock,
  Sparkles,
  Layers,
  Zap,
  ArrowDown,
  ArrowUp,
  BookOpen,
} from 'lucide-react';

interface SummaryWorkspaceProps {
  filename: string;
  pipeline: PipelineType;
  totalPages: number;
  summaryText: string;
  isStreaming: boolean;
  isCompleted: boolean;
  tableOfContents: TOCItem[];
  tokenCount: number;
  elapsedSeconds: number;
  onReset: () => void;
  onToast: (type: 'success' | 'error' | 'info', title: string, description?: string) => void;
}

export const SummaryWorkspace: React.FC<SummaryWorkspaceProps> = ({
  filename,
  pipeline,
  totalPages,
  summaryText,
  isStreaming,
  isCompleted,
  tableOfContents,
  tokenCount,
  elapsedSeconds,
  onReset,
  onToast,
}) => {
  const [copied, setCopied] = useState(false);
  const [activeSectionId, setActiveSectionId] = useState<string>('');
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [showScrollTop, setShowScrollTop] = useState<boolean>(false);

  const canvasRef = useRef<HTMLDivElement | null>(null);
  const bottomMarkerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isCompleted) {
      confetti({
        particleCount: 40,
        spread: 60,
        origin: { y: 0.8 },
        colors: ['#2563EB', '#3B82F6', '#60A5FA', '#10B981'],
      });
    }
  }, [isCompleted]);

  useEffect(() => {
    if (isStreaming && autoScroll) {
      bottomMarkerRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [summaryText, isStreaming, autoScroll]);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      setShowScrollTop(scrollY > 400);

      const headingElements = tableOfContents
        .map((item) => document.getElementById(item.id))
        .filter((el): el is HTMLElement => el !== null);

      for (let i = headingElements.length - 1; i >= 0; i--) {
        const el = headingElements[i];
        const rect = el.getBoundingClientRect();
        if (rect.top <= 140) {
          setActiveSectionId(el.id);
          return;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [tableOfContents]);

  const handleSelectSection = (id: string) => {
    setAutoScroll(false);
    setActiveSectionId(id);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleCopy = async () => {
    if (!summaryText) return;
    try {
      await navigator.clipboard.writeText(summaryText);
      setCopied(true);
      onToast('success', 'Summary Copied', 'Full Markdown text copied to your clipboard.');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      onToast('error', 'Copy Failed', 'Clipboard write permission was denied.');
    }
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const scrollToBottom = () => {
    setAutoScroll(true);
    bottomMarkerRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const readingTimeMinutes = Math.max(1, Math.ceil(tokenCount / 220));

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 bg-white">
      {/* Sticky Top Header */}
      <div className="sticky top-16 z-30 mb-8 p-4 rounded-2xl bg-white border border-slate-200 shadow-sm transition-all">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Document metadata & status */}
          <div className="min-w-0">
            <div className="flex items-center space-x-2.5 flex-wrap gap-y-1">
              <h2 className="text-base sm:text-lg font-bold text-slate-900 truncate max-w-md">
                {filename}
              </h2>

              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                {pipeline === 'LARGE_DOC' ? (
                  <>
                    <Layers className="w-3 h-3 mr-1 text-blue-600" />
                    <span>Hierarchical Pipeline ({totalPages}p)</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-3 h-3 mr-1 text-blue-600" />
                    <span>Single-Pass Pipeline ({totalPages}p)</span>
                  </>
                )}
              </span>

              {isStreaming ? (
                <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">
                  <span className="w-2 h-2 rounded-full bg-blue-600" />
                  <span>Streaming Tokens...</span>
                </span>
              ) : isCompleted ? (
                <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <Check className="w-3 h-3 text-emerald-600" />
                  <span>Generation Complete</span>
                </span>
              ) : null}
            </div>

            {/* Live Stats Row */}
            <div className="flex items-center space-x-4 mt-2 text-xs text-slate-500 font-mono">
              <span className="flex items-center space-x-1">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                <span>{tokenCount.toLocaleString()} tokens</span>
              </span>
              <span>•</span>
              <span className="flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>{elapsedSeconds}s elapsed</span>
              </span>
              <span>•</span>
              <span className="flex items-center space-x-1">
                <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                <span>~{readingTimeMinutes} min read</span>
              </span>
            </div>
          </div>

          {/* Action Toolbar with Blue Buttons */}
          <div className="flex items-center space-x-2 sm:space-x-3 flex-wrap">
            <button
              onClick={handleCopy}
              disabled={!summaryText}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 transition-colors disabled:opacity-50"
              title="Copy markdown text to clipboard"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>

            {/* Export Dropdown with Blue button */}
            <ExportDropdown
              summaryMarkdown={summaryText}
              filename={filename}
              onSuccess={(format) => onToast('success', 'Download Started', `Exported as ${format}`)}
              onError={(msg) => onToast('error', 'Export Error', msg)}
            />

            {/* New Document Button with Blue button */}
            <button
              onClick={onReset}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>New Doc</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="flex flex-col md:flex-row items-start gap-8">
        {/* Table of Contents Sidebar */}
        <div className="w-full md:w-72 lg:w-80 md:sticky md:top-44 flex-shrink-0">
          <TableOfContents
            items={tableOfContents}
            activeId={activeSectionId}
            onSelectSection={handleSelectSection}
            isStreaming={isStreaming}
          />
        </div>

        {/* Markdown Content Canvas */}
        <main
          ref={canvasRef}
          className="flex-1 min-w-0 w-full bg-white rounded-2xl p-6 sm:p-10 border border-slate-200 shadow-sm transition-colors"
        >
          {summaryText ? (
            <article className="prose prose-slate max-w-none prose-headings:text-slate-900 prose-p:text-slate-700">
              {renderMarkdown(summaryText, isStreaming)}
            </article>
          ) : (
            <div className="py-20 text-center">
              <div className="w-8 h-8 rounded-full border-2 border-blue-600 border-t-transparent animate-spin mx-auto mb-3" />
              <p className="text-sm text-slate-500">
                Waiting for summary stream from the backend...
              </p>
            </div>
          )}

          <div ref={bottomMarkerRef} className="h-4" />
        </main>
      </div>

      {/* Floating Scroll Controls */}
      <div className="fixed bottom-6 left-6 z-40 flex items-center space-x-2">
        {isStreaming && (
          <button
            onClick={() => {
              if (!autoScroll) {
                scrollToBottom();
              } else {
                setAutoScroll(false);
              }
            }}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-full text-xs font-semibold shadow-md border transition-all ${
              autoScroll
                ? 'bg-blue-600 hover:bg-blue-700 text-white border-blue-700'
                : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
            }`}
          >
            <ArrowDown className={`w-3.5 h-3.5 ${autoScroll ? 'animate-bounce' : ''}`} />
            <span>{autoScroll ? 'Following Stream' : 'Stream Paused (Click to follow)'}</span>
          </button>
        )}

        {showScrollTop && (
          <button
            onClick={scrollToTop}
            className="p-2.5 rounded-full bg-white border border-slate-300 text-slate-700 shadow-md hover:bg-slate-50 transition-colors"
            title="Scroll to top"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
