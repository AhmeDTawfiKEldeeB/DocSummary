import React from 'react';
import { pdf } from '@react-pdf/renderer';
import {
  Document,
  Packer,
  Paragraph,
  HeadingLevel,
  TextRun,
  AlignmentType,
  BorderStyle,
} from 'docx';
import { SummaryPDF } from '../lib/pdf-export/summary-pdf';
import type { SummaryPdfInput, SummarySection } from '../lib/pdf-export/summary-pdf';
import { detectHeading } from './markdownParser';

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function cleanBaseName(filename: string): string {
  return filename.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9_-]/g, '_');
}

/**
 * Parses raw markdown into structured sections and items for @react-pdf/renderer
 */
function parseMarkdownToSections(markdown: string): SummarySection[] {
  const lines = markdown.split('\n');
  const sections: SummarySection[] = [];
  let currentSection: SummarySection = {
    heading: '',
    items: [],
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line || line === '---' || line === '***') {
      continue;
    }

    const nextLine = i + 1 < lines.length ? lines[i + 1] : undefined;
    const heading = detectHeading(line, nextLine);

    if (heading) {
      if (currentSection.items.length > 0 || currentSection.heading !== '') {
        sections.push(currentSection);
      }
      currentSection = {
        heading: heading.title,
        items: [],
      };
      continue;
    }

    // Bullet item
    if (line.startsWith('- ') || line.startsWith('* ') || line.startsWith('• ')) {
      const cleanBullet = line
        .replace(/^[-*•]\s+/, '')
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/`([^`]+)`/g, '$1')
        .trim();
      currentSection.items.push({
        type: 'bullet',
        text: cleanBullet,
      });
      continue;
    }

    // Regular paragraph / callout
    const cleanPara = line
      .replace(/^>\s*/, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/`([^`]+)`/g, '$1')
      .trim();

    if (cleanPara) {
      currentSection.items.push({
        type: 'paragraph',
        text: cleanPara,
      });
    }
  }

  if (currentSection.items.length > 0 || sections.length === 0) {
    sections.push(currentSection);
  }

  return sections;
}

/**
 * Export summary as PDF using @react-pdf/renderer (from pdf_export_skill)
 * Fixes character separation and renders vector typography with clean headers and footers.
 */
export async function exportToPdf(markdownContent: string, sourceFilename: string) {
  const baseName = cleanBaseName(sourceFilename);
  const sections = parseMarkdownToSections(markdownContent);

  const input: SummaryPdfInput = {
    type: 'summary',
    title: 'DocSummary — Executive Synthesis',
    documentName: sourceFilename,
    createdAt: new Date().toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }),
    sections,
  };

  const docElement = React.createElement(SummaryPDF, { input });
  const blob = await pdf(docElement as any).toBlob();
  downloadBlob(blob, `${baseName}_summary.pdf`);
}

/**
 * Export summary as Markdown (.md)
 */
export function exportToMarkdown(markdownContent: string, sourceFilename: string) {
  const baseName = cleanBaseName(sourceFilename);
  const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
  downloadBlob(blob, `${baseName}_summary.md`);
}

/**
 * Export summary as Plain Text (.txt)
 */
export function exportToTxt(markdownContent: string, sourceFilename: string) {
  const baseName = cleanBaseName(sourceFilename);
  const plainText = markdownContent
    .replace(/^#+\s+/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^>\s+/gm, '')
    .replace(/\[(.*?)\]\(.*?\)/g, '$1');

  const blob = new Blob([plainText], { type: 'text/plain;charset=utf-8' });
  downloadBlob(blob, `${baseName}_summary.txt`);
}

/**
 * Export summary as native Microsoft Word (.docx)
 */
export async function exportToDocx(markdownContent: string, sourceFilename: string) {
  const baseName = cleanBaseName(sourceFilename);
  const lines = markdownContent.split('\n');

  const children: Paragraph[] = [
    new Paragraph({
      text: 'DocSummary — Executive Synthesis',
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
      spacing: { after: 120 },
    }),
    new Paragraph({
      children: [
        new TextRun({
          text: `Source Document: ${sourceFilename} | Generated: ${new Date().toLocaleDateString()}`,
          italics: true,
          color: '64748B',
          size: 18,
        }),
      ],
      alignment: AlignmentType.CENTER,
      spacing: { after: 240 },
    }),
  ];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line || line === '---' || line === '***') continue;

    const nextLine = i + 1 < lines.length ? lines[i + 1] : undefined;
    const heading = detectHeading(line, nextLine);

    if (heading) {
      children.push(
        new Paragraph({
          text: heading.title,
          heading:
            heading.level === 1
              ? HeadingLevel.HEADING_1
              : heading.level === 2
              ? HeadingLevel.HEADING_2
              : HeadingLevel.HEADING_3,
          spacing: { before: 200, after: 100 },
        })
      );
      continue;
    }

    if (line.startsWith('- ') || line.startsWith('* ') || line.startsWith('• ')) {
      const text = line.replace(/^[-*•]\s+/, '').replace(/\*\*(.*?)\*\*/g, '$1');
      children.push(
        new Paragraph({
          text,
          bullet: { level: 0 },
          spacing: { after: 60 },
        })
      );
    } else if (line.startsWith('> ')) {
      const text = line.replace(/^>\s+/, '').replace(/\*\*(.*?)\*\*/g, '$1');
      children.push(
        new Paragraph({
          children: [
            new TextRun({
              text,
              italics: true,
              color: '334155',
            }),
          ],
          border: {
            left: {
              color: '2563EB',
              space: 12,
              style: BorderStyle.SINGLE,
              size: 24,
            },
          },
          spacing: { before: 100, after: 100 },
        })
      );
    } else {
      const cleanPara = line.replace(/\*\*(.*?)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1');
      children.push(
        new Paragraph({
          text: cleanPara,
          spacing: { after: 120 },
        })
      );
    }
  }

  const doc = new Document({
    sections: [
      {
        properties: {},
        children,
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  downloadBlob(blob, `${baseName}_summary.docx`);
}
