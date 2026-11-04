import React from 'react';
import { X } from 'lucide-react';

interface BlueHandLoaderProps {
  onCancel?: () => void;
}

export const BlueHandLoader: React.FC<BlueHandLoaderProps> = ({ onCancel }) => {
  return (
    <div className="w-full max-w-md mx-auto p-8 rounded-2xl bg-white border border-slate-200 shadow-sm transition-all duration-300 flex flex-col items-center justify-center">
      {/* Optional Cancel button in top corner */}
      {onCancel && (
        <div className="w-full flex justify-end -mt-2 -mr-2 mb-2">
          <button
            onClick={onCancel}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            title="Cancel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Floating Animated Blue Hand & Document Art */}
      <div className="relative w-48 h-48 flex items-center justify-center my-4">
        {/* Target Document Silhouette */}
        <div className="absolute bottom-4 w-32 h-24 rounded-lg bg-white border border-slate-200 shadow-sm flex flex-col p-3 overflow-hidden">
          <div className="w-16 h-1.5 rounded-full bg-blue-600 mb-2" />
          <div className="w-24 h-1.5 rounded-full bg-slate-200 mb-1.5" />
          <div className="w-20 h-1.5 rounded-full bg-slate-200 mb-1.5" />
          <div className="w-26 h-1.5 rounded-full bg-slate-100" />

          {/* Scanning beam */}
          <div
            className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent shadow-[0_0_10px_rgba(37,99,235,0.9)] animate-hand-scan pointer-events-none"
            style={{ animationDuration: '2s' }}
          />
        </div>

        {/* Floating Blue Hand SVG Icon */}
        <div className="absolute -top-1 animate-hand-float z-10">
          <svg
            width="96"
            height="96"
            viewBox="0 0 100 100"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="transform -rotate-12"
          >
            {/* Outer Rotating Energy Ring */}
            <circle
              cx="50"
              cy="50"
              r="44"
              stroke="#2563EB"
              strokeWidth="1.5"
              strokeDasharray="4 4"
              className="opacity-40 animate-spin"
              style={{ animationDuration: '14s' }}
            />

            {/* Hand Silhouette */}
            <path
              d="M50 88 C40 88 35 78 35 68 L36 52 C36 48 39 45 43 45 C46 45 48 47 49 50 L49 32 C49 28 52 25 56 25 C60 25 63 28 63 32 L63 50 C64 48 66 46 68 46 C72 46 75 49 75 53 L75 68 C75 79 66 88 50 88 Z"
              fill="#2563EB"
            />

            <path
              d="M50 88 C40 88 35 78 35 68 L36 52 C36 48 39 45 43 45 C46 45 48 47 49 50 L49 32 C49 28 52 25 56 25 C60 25 63 28 63 32 L63 36 C64 34 66 33 68 33 C72 33 75 36 75 40 L75 44 C76 43 78 42 80 42 C84 42 87 45 87 49 L87 65 C87 77 75 88 50 88 Z"
              stroke="#1D4ED8"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Scanner Emitter Light */}
            <circle cx="56" cy="25" r="4.5" fill="#60A5FA" />
            <circle cx="56" cy="25" r="2.5" fill="#FFFFFF" />

            {/* Scanning beam line */}
            <line
              x1="56"
              y1="29"
              x2="56"
              y2="58"
              stroke="#3B82F6"
              strokeWidth="2.5"
              strokeLinecap="round"
              className="animate-pulse"
            />
          </svg>
        </div>
      </div>

      {/* Smooth Loading Indicator Bar */}
      <div className="w-48 bg-slate-100 rounded-full h-1.5 overflow-hidden relative mt-4">
        <div className="h-full bg-blue-600 rounded-full w-1/2 animate-[pulse_1.5s_ease-in-out_infinite]" />
      </div>
    </div>
  );
};
