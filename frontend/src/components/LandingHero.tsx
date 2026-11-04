import React from 'react';
import { Layers, Cpu, ArrowRight, CheckCircle2 } from 'lucide-react';
import type { SamplePaper } from '../utils/samplePapers';
import { SAMPLE_RESEARCH_PAPERS } from '../utils/samplePapers';

interface LandingHeroProps {
  onSelectSample: (paper: SamplePaper) => void;
}

export const LandingHero: React.FC<LandingHeroProps> = ({ onSelectSample }) => {
  return (
    <div className="text-center max-w-4xl mx-auto pt-6 pb-8 px-4 bg-white">
      {/* Pill Badge */}
      <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold mb-6">
        <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
        <span>Connected to Live FastAPI Document Intelligence Pipeline</span>
      </div>

      {/* Main Headline */}
      <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-[1.15]">
        Turn Dense Research Papers Into <br className="hidden sm:inline" />
        <span className="text-blue-600">Navigable, Structured Summaries</span>
      </h1>

      {/* Subtitle */}
      <p className="mt-5 text-base sm:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
        Upload multi-page PDFs or research publications. DocSummary routes your document to the optimal pipeline and streams structured insights with live table of contents navigation.
      </p>

      {/* Feature Badges */}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-2 sm:gap-3 text-xs text-slate-700">
        <span className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 shadow-sm">
          <Cpu className="w-3.5 h-3.5 text-blue-600" />
          <span>Small & Large Doc Pipelines</span>
        </span>
        <span className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 shadow-sm">
          <Layers className="w-3.5 h-3.5 text-blue-600" />
          <span>Hierarchical Section Synthesis</span>
        </span>
        <span className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 shadow-sm">
          <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
          <span>Real-time Token-by-Token Streaming</span>
        </span>
      </div>

      {/* Quick Try Sample Papers Section */}
      <div className="mt-8 p-5 rounded-2xl bg-white border border-slate-200 max-w-2xl mx-auto shadow-sm">
        <div className="flex items-center justify-between mb-3 text-left">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Test Documents
            </h3>
            <p className="text-xs text-slate-500">
              Select a sample research document or upload your own PDF below:
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {SAMPLE_RESEARCH_PAPERS.map((paper) => (
            <button
              key={paper.id}
              onClick={() => onSelectSample(paper)}
              className="group text-left p-3.5 rounded-xl border border-slate-200 bg-white hover:border-blue-500 hover:shadow-sm transition-all flex items-center justify-between"
            >
              <div className="min-w-0 pr-2">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-xs text-slate-800 group-hover:text-blue-600 truncate block">
                    {paper.id === 'deepseek-r1' ? 'DeepSeek-R1 (32 Pages)' : 'Attention Is All You Need (11 Pages)'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 truncate mt-0.5">
                  {paper.expectedPipeline === 'LARGE_DOC' ? 'Hierarchical Pipeline' : 'Single-Pass Pipeline'}
                </p>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
