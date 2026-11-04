import React, { useState } from 'react';
import type { TOCItem } from '../services';
import { ListTree, ChevronRight, ChevronDown, Compass } from 'lucide-react';

interface TableOfContentsProps {
  items: TOCItem[];
  activeId?: string;
  onSelectSection: (id: string) => void;
  isStreaming: boolean;
}

export const TableOfContents: React.FC<TableOfContentsProps> = ({
  items,
  activeId,
  onSelectSection,
  isStreaming,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside
      className={`transition-all duration-200 flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm ${
        isCollapsed ? 'w-14' : 'w-full md:w-72 lg:w-80'
      }`}
    >
      <div className="p-4 border-b border-slate-100 flex items-center justify-between">
        <div className={`flex items-center space-x-2 ${isCollapsed ? 'hidden' : 'flex'}`}>
          <Compass className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
            Table of Contents
          </h3>
          {isStreaming && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600"></span>
            </span>
          )}
        </div>

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors mx-auto md:mx-0"
          title={isCollapsed ? 'Expand Table of Contents' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <ListTree className="w-4 h-4 text-blue-600" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {!isCollapsed && (
        <div className="p-3 max-h-[calc(100vh-220px)] overflow-y-auto space-y-1">
          {items.length === 0 ? (
            <div className="p-4 text-center">
              <p className="text-xs text-slate-400 italic">
                {isStreaming ? 'Detecting headings as stream arrives...' : 'No sections detected'}
              </p>
            </div>
          ) : (
            items.map((item) => {
              const isActive = activeId === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectSection(item.id)}
                  className={`w-full text-left rounded-lg transition-all duration-150 flex items-start group ${
                    item.level === 1
                      ? 'py-2 px-3 text-xs font-bold tracking-tight'
                      : item.level === 2
                      ? 'py-1.5 pl-6 pr-3 text-xs font-medium'
                      : 'py-1 pl-9 pr-3 text-[11px]'
                  } ${
                    isActive
                      ? 'bg-blue-50 text-blue-600 font-semibold border-l-2 border-blue-600'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <span className="truncate block flex-1">{item.title}</span>
                  {isActive && (
                    <ChevronRight className="w-3.5 h-3.5 text-blue-600 ml-1 flex-shrink-0 mt-0.5" />
                  )}
                </button>
              );
            })
          )}
        </div>
      )}
    </aside>
  );
};
