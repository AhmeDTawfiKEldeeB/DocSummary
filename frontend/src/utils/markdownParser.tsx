import React from 'react';
import type { TOCItem } from '../services/types';

/**
 * Creates a URL-friendly anchor slug from heading text
 */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');
}

export interface HeadingMatch {
  title: string;
  level: number;
}

/**
 * Detects whether a given line is a section heading.
 * Handles:
 * 1. Markdown syntax (#, ##, ###)
 * 2. Bold standalone headings: **Heading** or **Heading:**
 * 3. Plain standalone title lines followed by bullets or content (e.g. "Equipment & Allowances")
 */
export function detectHeading(line: string, nextLine?: string): HeadingMatch | null {
  const trimmed = line.trim();
  if (!trimmed) return null;

  // 1. Standard markdown syntax (#, ##, ###)
  const mdMatch = trimmed.match(/^(#{1,3})\s+(.*)$/);
  if (mdMatch) {
    const title = mdMatch[2].replace(/\*\*/g, '').trim();
    return { level: mdMatch[1].length, title };
  }

  // 2. Bold single-line heading: **Title** or **Title:**
  const boldMatch = trimmed.match(/^\*\*([^*]+)\*\*:?$/);
  if (boldMatch) {
    const rawTitle = boldMatch[1].trim();
    if (rawTitle.length >= 2 && rawTitle.length <= 80) {
      const cleanTitle = rawTitle.replace(/:$/, '').trim();
      return { level: 2, title: cleanTitle };
    }
  }

  // 3. Numbered headings like "1. Core Architectural Innovations" or "1.1 Introduction"
  const numberedMatch = trimmed.match(/^(\d+\.?\d*)\s+([A-Z][\w\s&/,-]+)$/);
  if (numberedMatch && trimmed.length <= 70) {
    return { level: 2, title: trimmed };
  }

  // 4. Standalone Title Case line (e.g. "Equipment & Allowances", "Data Security", "Key Findings")
  if (
    trimmed.length >= 3 &&
    trimmed.length <= 65 &&
    !trimmed.startsWith('-') &&
    !trimmed.startsWith('*') &&
    !trimmed.startsWith('•') &&
    !trimmed.startsWith('>') &&
    !trimmed.startsWith('|') &&
    !trimmed.endsWith('.') &&
    !trimmed.endsWith(',') &&
    !trimmed.endsWith(';') &&
    /^[A-Z0-9]/.test(trimmed)
  ) {
    const nextTrimmed = nextLine ? nextLine.trim() : '';
    const isFollowedByList =
      nextTrimmed.startsWith('- ') ||
      nextTrimmed.startsWith('* ') ||
      nextTrimmed.startsWith('• ') ||
      nextTrimmed.startsWith('1. ');

    const endsWithColon = trimmed.endsWith(':');
    const words = trimmed.split(/\s+/);

    const looksLikeTitle =
      words.length <= 8 &&
      (isFollowedByList ||
        endsWithColon ||
        words.every(
          (w) =>
            /^[A-Z0-9&/(-]/.test(w) ||
            ['and', 'or', 'of', 'in', 'for', 'to', 'the', 'with', '&', 'vs'].includes(
              w.toLowerCase()
            )
        ));

    if (looksLikeTitle) {
      return {
        level: 2,
        title: trimmed.replace(/:$/, '').trim(),
      };
    }
  }

  return null;
}

/**
 * Extracts Table of Contents items from raw markdown dynamically
 */
export function extractTOC(markdown: string): TOCItem[] {
  const items: TOCItem[] = [];
  const lines = markdown.split('\n');
  const counts = new Map<string, number>();

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const nextLine = i + 1 < lines.length ? lines[i + 1] : undefined;
    const match = detectHeading(rawLine, nextLine);

    if (match && match.title) {
      let slug = slugify(match.title);
      const count = counts.get(slug) || 0;
      counts.set(slug, count + 1);
      if (count > 0) {
        slug = `${slug}-${count}`;
      }

      items.push({
        id: slug,
        title: match.title,
        level: match.level,
      });
    }
  }

  return items;
}

/**
 * Formats inline text with bold, italic, and inline code
 */
export function renderInline(text: string): React.ReactNode[] {
  const regex = /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g;
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={idx} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return (
        <em key={idx} className="italic text-slate-800">
          {part.slice(1, -1)}
        </em>
      );
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 text-xs font-mono bg-slate-100 border border-slate-200 rounded text-blue-600"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

/**
 * Renders full Markdown into structured React elements with heading IDs matching TOC
 */
export function renderMarkdown(markdown: string, isStreaming: boolean): React.ReactNode {
  const lines = markdown.split('\n');
  const elements: React.ReactNode[] = [];
  const headingCounts = new Map<string, number>();

  let i = 0;
  while (i < lines.length) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line) {
      i++;
      continue;
    }

    // Horizontal Rule
    if (line === '---' || line === '***') {
      elements.push(
        <hr key={`hr-${i}`} className="my-6 border-slate-200" />
      );
      i++;
      continue;
    }

    // Heading Detection (Markdown #, Bold single-line, or Standalone title)
    const nextLine = i + 1 < lines.length ? lines[i + 1] : undefined;
    const headingMatch = detectHeading(line, nextLine);

    if (headingMatch) {
      let slug = slugify(headingMatch.title);
      const count = headingCounts.get(slug) || 0;
      headingCounts.set(slug, count + 1);
      if (count > 0) slug = `${slug}-${count}`;

      if (headingMatch.level === 1) {
        elements.push(
          <h1
            key={`h1-${i}`}
            id={slug}
            className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 mt-7 mb-3 scroll-mt-24 pb-2 border-b border-slate-200"
          >
            {renderInline(headingMatch.title)}
          </h1>
        );
      } else if (headingMatch.level === 2) {
        elements.push(
          <h2
            key={`h2-${i}`}
            id={slug}
            className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 mt-6 mb-2.5 scroll-mt-24 flex items-center"
          >
            <span className="w-1.5 h-4 bg-blue-600 rounded-full inline-block mr-2" />
            <span>{renderInline(headingMatch.title)}</span>
          </h2>
        );
      } else {
        elements.push(
          <h3
            key={`h3-${i}`}
            id={slug}
            className="text-base font-semibold text-slate-800 mt-5 mb-2 scroll-mt-24"
          >
            {renderInline(headingMatch.title)}
          </h3>
        );
      }
      i++;
      continue;
    }

    // Blockquote / Callout Box
    if (line.startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s*/, ''));
        i++;
      }
      elements.push(
        <div
          key={`quote-${i}`}
          className="my-4 p-4 rounded-xl border-l-4 border-blue-600 bg-slate-50 text-slate-700 text-sm leading-relaxed"
        >
          {quoteLines.map((q, idx) => (
            <p key={idx} className={idx > 0 ? 'mt-1.5' : ''}>
              {renderInline(q)}
            </p>
          ))}
        </div>
      );
      continue;
    }

    // Bullet List Items
    if (line.startsWith('- ') || line.startsWith('* ') || line.startsWith('• ')) {
      const listItems: string[] = [];
      while (
        i < lines.length &&
        (lines[i].trim().startsWith('- ') ||
          lines[i].trim().startsWith('* ') ||
          lines[i].trim().startsWith('• '))
      ) {
        const itemText = lines[i].trim().replace(/^[-*•]\s+/, '');
        listItems.push(itemText);
        i++;
      }
      elements.push(
        <ul key={`ul-${i}`} className="my-3 space-y-2 list-none pl-1">
          {listItems.map((item, idx) => (
            <li key={idx} className="flex items-start text-sm sm:text-base text-slate-700 leading-relaxed">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-2 mr-3 flex-shrink-0" />
              <span>{renderInline(item)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Table Detection
    if (line.startsWith('|') && line.endsWith('|')) {
      const tableRows: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableRows.push(lines[i].trim());
        i++;
      }

      if (tableRows.length >= 2) {
        const parseRow = (rowStr: string) =>
          rowStr
            .slice(1, -1)
            .split('|')
            .map((c) => c.trim());

        const headerCells = parseRow(tableRows[0]);
        const bodyRows = tableRows.slice(2).map(parseRow);

        elements.push(
          <div key={`table-${i}`} className="my-5 overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-700">
                <tr>
                  {headerCells.map((cell, cIdx) => (
                    <th key={cIdx} className="px-4 py-2.5 font-semibold">
                      {renderInline(cell)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {bodyRows.map((cells, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-50 transition-colors">
                    {cells.map((c, cIdx) => (
                      <td key={cIdx} className="px-4 py-2 text-slate-600">
                        {renderInline(c)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // Standard Paragraph
    elements.push(
      <p
        key={`p-${i}`}
        className="my-2.5 text-sm sm:text-base text-slate-700 leading-relaxed max-w-prose"
      >
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return (
    <div className="relative">
      {elements}
      {isStreaming && (
        <span
          className="inline-block w-2.5 h-4.5 ml-1 bg-blue-600 rounded-sm animate-pulse align-middle shadow-sm"
          aria-hidden="true"
        />
      )}
    </div>
  );
}
