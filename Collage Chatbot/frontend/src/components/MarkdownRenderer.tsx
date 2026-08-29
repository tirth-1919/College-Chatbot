import React from 'react';
import { Copy, Check, ExternalLink } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  if (!content) return null;

  // Unescape HTML entities
  const unescapeHtml = (text: string) => {
    return text
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/&nbsp;/g, ' ');
  };

  const cleanContent = unescapeHtml(content);

  // Parse markdown blocks (code blocks, tables, headings, lists, paragraphs)
  const lines = cleanContent.split('\n');
  const elements: React.ReactNode[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // 1. Code block ```
    if (line.trim().startsWith('```')) {
      const lang = line.trim().replace(/^```/, '').trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      const codeText = codeLines.join('\n');
      elements.push(
        <div key={`code-${i}`} className="my-3 rounded-xl overflow-hidden bg-slate-950 border border-slate-800">
          {lang && (
            <div className="px-3.5 py-1.5 bg-slate-900 border-b border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
              <span>{lang}</span>
            </div>
          )}
          <pre className="p-3.5 text-xs sm:text-sm font-mono text-emerald-300 overflow-x-auto leading-relaxed">
            <code>{codeText}</code>
          </pre>
        </div>
      );
      continue;
    }

    // 2. Table | col | col |
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 2) {
        const headerCols = tableLines[0]
          .split('|')
          .slice(1, -1)
          .map(c => c.trim());
        const isSeparator = tableLines[1].includes('---');
        const dataRowStart = isSeparator ? 2 : 1;
        const bodyRows = tableLines.slice(dataRowStart).map(row =>
          row
            .split('|')
            .slice(1, -1)
            .map(c => c.trim())
        );

        elements.push(
          <div key={`table-${i}`} className="my-3 overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60 shadow-sm">
            <table className="w-full text-left text-xs sm:text-sm divide-y divide-slate-800">
              <thead className="bg-slate-900/90 text-slate-300 font-semibold">
                <tr>
                  {headerCols.map((h, hIdx) => (
                    <th key={hIdx} className="px-3.5 py-2.5">
                      {renderInlineFormatting(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {bodyRows.map((r, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-900/40 transition-colors">
                    {r.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3.5 py-2">
                        {renderInlineFormatting(cell)}
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

    // 3. Headings (#, ##, ###)
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-base sm:text-lg font-bold text-white mt-3.5 mb-1.5 flex items-center space-x-1.5">
          {renderInlineFormatting(line.replace('### ', ''))}
        </h3>
      );
      i++;
      continue;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="text-lg sm:text-xl font-bold text-white mt-4 mb-2">
          {renderInlineFormatting(line.replace('## ', ''))}
        </h2>
      );
      i++;
      continue;
    }
    if (line.startsWith('# ')) {
      elements.push(
        <h1 key={`h1-${i}`} className="text-xl sm:text-2xl font-extrabold text-white mt-4 mb-2">
          {renderInlineFormatting(line.replace('# ', ''))}
        </h1>
      );
      i++;
      continue;
    }

    // 4. Bullet lists (- or *)
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      const listItems: string[] = [];
      while (i < lines.length && (lines[i].trim().startsWith('- ') || lines[i].trim().startsWith('* '))) {
        listItems.push(lines[i].trim().replace(/^[-*]\s+/, ''));
        i++;
      }
      elements.push(
        <ul key={`ul-${i}`} className="my-2 space-y-1.5 list-disc list-inside text-slate-200 pl-1 text-xs sm:text-sm">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx} className="leading-relaxed">
              <span className="text-slate-100">{renderInlineFormatting(item)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // 5. Numbered lists (1. 2.)
    if (/^\d+\.\s+/.test(line.trim())) {
      const listItems: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        listItems.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i++;
      }
      elements.push(
        <ol key={`ol-${i}`} className="my-2 space-y-1.5 list-decimal list-inside text-slate-200 pl-1 text-xs sm:text-sm">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx} className="leading-relaxed">
              <span className="text-slate-100">{renderInlineFormatting(item)}</span>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // 6. Regular Paragraph or blank line
    if (line.trim() === '') {
      elements.push(<div key={`blank-${i}`} className="h-2" />);
      i++;
      continue;
    }

    elements.push(
      <p key={`p-${i}`} className="text-xs sm:text-sm leading-relaxed text-slate-100 my-1">
        {renderInlineFormatting(line)}
      </p>
    );
    i++;
  }

  return <div className={`space-y-1 text-slate-100 ${className}`}>{elements}</div>;
};

/**
 * Handles inline formatting: **bold**, *italic*, `code`, [link](url)
 */
function renderInlineFormatting(text: string): React.ReactNode {
  if (!text) return null;

  // Split tokens for bold, inline code, and links
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={match.index} className="font-bold text-white">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('*') && token.endsWith('*') && !token.startsWith('**')) {
      parts.push(
        <em key={match.index} className="italic text-slate-300">
          {token.slice(1, -1)}
        </em>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code key={match.index} className="px-1.5 py-0.5 rounded-md bg-slate-800 text-ait-gold font-mono text-xs">
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith('[') && token.includes('](') && token.endsWith(')')) {
      const linkTextMatch = token.match(/\[(.*?)\]\((.*?)\)/);
      if (linkTextMatch) {
        const linkText = linkTextMatch[1];
        const linkUrl = linkTextMatch[2];
        parts.push(
          <a
            key={match.index}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-ait-400 hover:text-ait-300 underline font-medium inline-flex items-center space-x-0.5"
          >
            <span>{linkText}</span>
            <ExternalLink className="w-3 h-3 inline ml-0.5 opacity-70" />
          </a>
        );
      } else {
        parts.push(token);
      }
    } else {
      parts.push(token);
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length === 1 ? parts[0] : parts;
}
