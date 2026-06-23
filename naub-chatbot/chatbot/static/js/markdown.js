/**
 * naub-markdown.js — lightweight Markdown → HTML renderer
 * Handles: bold, italic, inline code, code blocks, tables,
 *          ordered/unordered lists, headings, links, hr, line breaks.
 * No external dependencies.
 */
(function (global) {
  'use strict';

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderTable(block) {
    const lines = block.trim().split('\n').filter(Boolean);
    if (lines.length < 2) return '<p>' + escapeHtml(block) + '</p>';
    const headers = lines[0].split('|').map(c => c.trim()).filter(Boolean);
    // skip separator row (lines[1])
    const rows = lines.slice(2).map(line =>
      line.split('|').map(c => c.trim()).filter(Boolean)
    );
    const thead = '<thead><tr>' +
      headers.map(h => `<th>${renderInline(h)}</th>`).join('') +
      '</tr></thead>';
    const tbody = '<tbody>' +
      rows.map(row =>
        '<tr>' + row.map(cell => `<td>${renderInline(cell)}</td>`).join('') + '</tr>'
      ).join('') +
      '</tbody>';
    return `<table>${thead}${tbody}</table>`;
  }

  function renderInline(text) {
    // Escape HTML first (but preserve existing entities)
    let out = escapeHtml(text);
    // Inline code: `code`
    out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold+Italic: ***text*** or ___text___
    out = out.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    // Bold: **text** or __text__
    out = out.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/__(.+?)__/g, '<strong>$1</strong>');
    // Italic: *text* or _text_
    out = out.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
    out = out.replace(/_([^_\n]+)_/g, '<em>$1</em>');
    // Links: [text](url)
    out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return out;
  }

  function renderBlock(text) {
    // Normalize line endings
    text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    const lines = text.split('\n');
    const output = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // ── Fenced code block ──────────────────────────────
      if (/^```/.test(line)) {
        const lang = line.slice(3).trim();
        const codeLines = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) {
          codeLines.push(lines[i]);
          i++;
        }
        i++; // skip closing ```
        output.push(
          `<pre><code${lang ? ` class="lang-${lang}"` : ''}>${
            escapeHtml(codeLines.join('\n'))
          }</code></pre>`
        );
        continue;
      }

      // ── Table ──────────────────────────────────────────
      if (/^\|/.test(line)) {
        const tableLines = [];
        while (i < lines.length && /^\|/.test(lines[i])) {
          tableLines.push(lines[i]);
          i++;
        }
        output.push(renderTable(tableLines.join('\n')));
        continue;
      }

      // ── Headings ───────────────────────────────────────
      const heading = line.match(/^(#{1,6})\s+(.*)/);
      if (heading) {
        const level = heading[1].length;
        output.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
        i++;
        continue;
      }

      // ── HR ─────────────────────────────────────────────
      if (/^---+$/.test(line.trim())) {
        output.push('<hr>');
        i++;
        continue;
      }

      // ── Unordered list ─────────────────────────────────
      if (/^[*\-•]\s/.test(line)) {
        const items = [];
        while (i < lines.length && /^[*\-•]\s/.test(lines[i])) {
          items.push(`<li>${renderInline(lines[i].replace(/^[*\-•]\s/, ''))}</li>`);
          i++;
        }
        output.push(`<ul>${items.join('')}</ul>`);
        continue;
      }

      // ── Ordered list ───────────────────────────────────
      if (/^\d+\.\s/.test(line)) {
        const items = [];
        while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
          items.push(`<li>${renderInline(lines[i].replace(/^\d+\.\s/, ''))}</li>`);
          i++;
        }
        output.push(`<ol>${items.join('')}</ol>`);
        continue;
      }

      // ── Blank line ─────────────────────────────────────
      if (line.trim() === '') {
        i++;
        continue;
      }

      // ── Paragraph ──────────────────────────────────────
      const paraLines = [];
      while (i < lines.length && lines[i].trim() !== '' &&
             !/^[#`|*\-•]/.test(lines[i]) && !/^\d+\./.test(lines[i])) {
        paraLines.push(lines[i]);
        i++;
      }
      if (paraLines.length) {
        output.push(`<p>${renderInline(paraLines.join(' '))}</p>`);
      }
    }

    return output.join('\n');
  }

  // Export
  global.MarkdownRenderer = { render: renderBlock };

})(typeof window !== 'undefined' ? window : globalThis);
