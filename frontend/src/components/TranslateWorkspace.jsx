import React, { useState, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import {
  Upload, Download, Loader2,
  Languages, FileText, AlertCircle, RefreshCw,
  ZoomIn, ZoomOut, Tag
} from 'lucide-react';
import { API_URL } from '../config/api';

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;


// ── Dropzone ──────────────────────────────────────────────────────────────────
const Dropzone = ({ onFiles }) => {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
    if (files.length) onFiles(files[0]);
  };

  return (
    <div
      className={`translate-dropzone ${dragging ? 'dragging' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input ref={inputRef} type="file" accept=".pdf" hidden onChange={e => e.target.files?.[0] && onFiles(e.target.files[0])} />
      <div className="translate-dropzone-icon">
        <Languages size={48} strokeWidth={1.5} />
      </div>
      <h2 className="translate-dropzone-title">Dịch tài liệu PDF</h2>
      <p className="translate-dropzone-sub">
        Hỗ trợ: Hợp đồng lao động · Học bạ · Giấy kết hôn · Giấy khai sinh · Giấy ủy quyền · Hộ chiếu/Visa
      </p>
      <button className="btn btn-primary translate-upload-btn">
        <Upload size={16} /> Chọn file PDF
      </button>
      <p className="translate-dropzone-hint">hoặc kéo thả file vào đây · Không giới hạn kích thước</p>
    </div>
  );
};

// ── HTML Page Renderer ────────────────────────────────────────────────────────
const HtmlTranslatedPage = ({ html, pageNum, onHtmlEdit, registerPageRef, previewBold, previewLineHeight }) => (
  <div className="translated-page-shell" data-page-number={pageNum}>
    <div className="translated-page-label">Trang {pageNum}</div>
    <div
      ref={(el) => registerPageRef(pageNum, el)}
      className={`translated-page-content translated-page-content-editable${previewBold ? ' translation-preview-bold' : ''}${previewLineHeight ? ' translation-preview-line-height' : ''}`}
      contentEditable={true}
      suppressContentEditableWarning={true}
      style={{
        color: '#1a202c',
        '--translation-preview-line-height': previewLineHeight || undefined,
      }}
      onBlur={(e) => onHtmlEdit(pageNum, e.currentTarget.innerHTML)}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  </div>
);

// ── Block Renderer (legacy fallback) ─────────────────────────────────────────
const TranslatedPage = ({ pageData, pageNum, onBlockEdit }) => (
  <div className="translated-page-content" style={{ fontFamily: '"Times New Roman", Times, serif', color: '#1a202c' }}>
    {pageData.blocks.map((block, i) => {
      if (block.type === 'table') {
        const borderless = block.borderless;
        const borderStyle = borderless ? 'none' : '1px solid #a0aec0';
        const cellFontSize = block.font_size ? `${block.font_size}pt` : '12pt';
        const colWidths = block.col_widths || null;
        return (
          <div key={i} className="translated-table-wrapper" style={{ margin: borderless ? '3px 0' : '8px 0', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', border: borderStyle }}>
              <tbody>
                {block.translated_cells.map((row, rIdx) => (
                  <tr key={rIdx} style={{ borderBottom: borderless ? 'none' : '1px solid #a0aec0' }}>
                    {row.map((cell, cIdx) => (
                      <td
                        key={cIdx}
                        contentEditable={true}
                        suppressContentEditableWarning={true}
                        onBlur={(e) => onBlockEdit(pageNum, i, e.target.innerText, rIdx, cIdx)}
                        style={{
                          border: borderStyle,
                          padding: borderless ? '1px 6px 1px 0' : '5px 8px',
                          fontSize: cellFontSize,
                          verticalAlign: 'top',
                          outline: 'none',
                          background: '#fff',
                          whiteSpace: 'pre-wrap',
                          lineHeight: '1.5',
                          width: colWidths ? colWidths[cIdx] : undefined,
                        }}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }

      const isHeading = block.is_heading;
      const align = block.align || 'left';
      const isBold = block.is_bold;
      const fontSize = block.font_size ? `${block.font_size}pt` : (isHeading ? '13pt' : '12pt');
      const marginBottom = block.margin_bottom !== undefined ? `${block.margin_bottom}px` : (isHeading ? '8px' : '4px');
      const marginTop = block.margin_top !== undefined ? `${block.margin_top}px` : '0px';
      const lineHeight = block.font_size && block.font_size >= 16 ? '1.3' : '1.6';

      return (
        <div
          key={i}
          className={`translated-block ${isHeading ? 'translated-heading' : 'translated-para'}`}
          contentEditable={true}
          suppressContentEditableWarning={true}
          onBlur={(e) => onBlockEdit(pageNum, i, e.target.innerText)}
          style={{
            fontSize,
            fontWeight: (isHeading || isBold) ? 'bold' : 'normal',
            textAlign: align,
            marginTop,
            marginBottom,
            lineHeight,
            whiteSpace: 'pre-wrap',
            outline: 'none',
            padding: '1px 2px',
            borderRadius: '3px',
            borderBottom: '1px dashed transparent',
            transition: 'background-color 0.15s ease',
          }}
          onFocus={(e) => { e.target.style.borderBottom = '1px dashed #3182ce'; e.target.style.backgroundColor = '#f7fafc'; }}
          onBlurCapture={(e) => { e.target.style.borderBottom = '1px dashed transparent'; e.target.style.backgroundColor = 'transparent'; }}
        >
          {block.translated}
        </div>
      );
    })}
  </div>
);

// ── Main Component ────────────────────────────────────────────────────────────
const TranslateWorkspace = () => {
  const [file, setFile] = useState(null);
  const [objectUrl, setObjectUrl] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | configuring | loading | done | error
  const [errorMsg, setErrorMsg] = useState('');
  const [result, setResult] = useState(null);
  const [pdfNumPages, setPdfNumPages] = useState(null);
  const [pdfScale, setPdfScale] = useState(1.0);
  const [progress, setProgress] = useState(0);
  const [loadingStep, setLoadingStep] = useState('');
  const [previewBold, setPreviewBold] = useState(false);
  const [previewLineHeight, setPreviewLineHeight] = useState(null);
  const [selectedRangeMode, setSelectedRangeMode] = useState('all'); // 'all' | 'custom'
  const [customRangeText, setCustomRangeText] = useState('');

  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(480);
  const translatedPageRefs = useRef({});
  const savedEditorRangeRef = useRef(null);
  const savedEditorRootRef = useRef(null);

  React.useEffect(() => {
    const rememberEditorSelection = () => {
      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) return;

      const range = selection.getRangeAt(0);
      let node = range.commonAncestorContainer;
      if (node.nodeType === Node.TEXT_NODE) node = node.parentElement;
      const editableRoot = node?.closest?.('.translated-page-content-editable');
      if (!editableRoot) return;

      savedEditorRangeRef.current = range.cloneRange();
      savedEditorRootRef.current = editableRoot;
    };

    document.addEventListener('selectionchange', rememberEditorSelection);
    return () => document.removeEventListener('selectionchange', rememberEditorSelection);
  }, []);

  React.useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        setContainerWidth(Math.floor(entries[0].contentRect.width - 32));
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [file, status]);

  const parseSelectedPages = (mode, customStr, total) => {
    if (mode === 'all') {
      return Array.from({ length: total }, (_, i) => i + 1);
    }
    const pages = new Set();
    const parts = (customStr || '').replace(/\s+/g, '').split(',');
    for (const part of parts) {
      if (!part) continue;
      if (part.includes('-')) {
        const [s, e] = part.split('-');
        const start = parseInt(s, 10) || 1;
        const end = parseInt(e, 10) || total;
        for (let i = Math.max(1, start); i <= Math.min(total, end); i++) {
          pages.add(i);
        }
      } else {
        const p = parseInt(part, 10);
        if (p >= 1 && p <= total) pages.add(p);
      }
    }
    return pages.size > 0 ? Array.from(pages).sort((a, b) => a - b) : Array.from({ length: total }, (_, i) => i + 1);
  };

  const startTranslation = async (targetFile, mode = selectedRangeMode, total = pdfNumPages) => {
    const fileToUse = targetFile || file;
    if (!fileToUse) return;

    setStatus('loading');
    setErrorMsg('');
    setProgress(5);
    setLoadingStep('Đang chuẩn bị dịch tài liệu...');

    const totalPages = total || pdfNumPages || 1;
    const targetPages = parseSelectedPages(mode, customRangeText, totalPages);

    // Chunk size: 2 pages per batch guarantees fast response (< 8s) and zero timeouts
    const CHUNK_SIZE = 2;
    const chunks = [];
    for (let i = 0; i < targetPages.length; i += CHUNK_SIZE) {
      chunks.push(targetPages.slice(i, i + CHUNK_SIZE));
    }

    const allPages = [];
    const failedPages = [];

    try {
      for (let chunkIdx = 0; chunkIdx < chunks.length; chunkIdx++) {
        const chunk = chunks[chunkIdx];
        const chunkLabel = chunk.length === 1 ? `trang ${chunk[0]}` : `trang ${chunk[0]}-${chunk[chunk.length - 1]}`;
        const currentPct = Math.min(95, Math.round((chunkIdx / chunks.length) * 90) + 5);

        setProgress(currentPct);
        setLoadingStep(`Đang dịch ${chunkLabel} (${chunkIdx + 1}/${chunks.length} đợt)...`);

        const formData = new FormData();
        formData.append('file', fileToUse);
        formData.append('pages', chunk.join(','));

        const res = await fetch(`${API_URL}/api/translate-pdf/html`, {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `Lỗi khi dịch ${chunkLabel}` }));
          throw new Error(err.detail || `Lỗi khi dịch ${chunkLabel}`);
        }

        const data = await res.json();
        if (data.pages && Array.isArray(data.pages)) {
          allPages.push(...data.pages);
        }
        if (data.failed_pages && Array.isArray(data.failed_pages)) {
          failedPages.push(...data.failed_pages);
        }
      }

      setProgress(100);
      setLoadingStep('Hoàn thành bản dịch!');

      allPages.sort((a, b) => a.page_num - b.page_num);

      setTimeout(() => {
        setResult({
          original_filename: fileToUse.name,
          total_pages: allPages.length,
          total_doc_pages: totalPages,
          mode: 'html',
          pages: allPages,
          failed_pages: failedPages,
        });
        setStatus('done');
      }, 350);
    } catch (err) {
      setErrorMsg(err.message || 'Quá trình dịch bị lỗi');
      setStatus('error');
    }
  };

  const handleFile = async (f) => {
    setFile(f);
    setObjectUrl(URL.createObjectURL(f));
    setResult(null);
    setErrorMsg('');

    try {
      const arrayBuffer = await f.arrayBuffer();
      const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
      const pdf = await loadingTask.promise;
      const numPages = pdf.numPages || 1;
      setPdfNumPages(numPages);
      setCustomRangeText(`1-${Math.min(numPages, 5)}`);

      if (numPages <= 2) {
        await startTranslation(f, 'all', numPages);
      } else {
        setStatus('configuring');
      }
    } catch (e) {
      console.warn('Could not inspect PDF page count', e);
      setPdfNumPages(1);
      await startTranslation(f, 'all', 1);
    }
  };

  const handleReset = () => {
    setFile(null);
    setObjectUrl(null);
    setResult(null);
    setStatus('idle');
    setErrorMsg('');
    setPreviewBold(false);
    setPreviewLineHeight(null);
    setSelectedRangeMode('all');
    setCustomRangeText('');
  };

  const downloadTranslation = () => {
    if (!result) return;
    const isHtmlModeLocal = result.mode === 'html';
    let text = `BILINGUAL TRANSLATION — ${result.original_filename}\n`;
    if (!isHtmlModeLocal) {
      text += `Document type: ${result.doc_type_label}  |  Translator: ${(result.translator || 'gemini').toUpperCase()}\n`;
    }
    text += '='.repeat(70) + '\n\n';
    result.pages.forEach(page => {
      text += `--- Page ${page.page_num} ---\n\n`;
      if (isHtmlModeLocal) {
        // Strip HTML tags for plain text export
        const tmp = document.createElement('div');
        const el = translatedPageRefs.current[page.page_num];
        tmp.innerHTML = el ? el.innerHTML : (page.translated_html || '');
        text += (tmp.textContent || tmp.innerText || '') + '\n\n';
      } else {
        page.blocks?.forEach(b => {
          if (b.type === 'table') {
            text += `[TABLE]\n`;
            b.translated_cells.forEach((row, ri) => {
              text += `  Row ${ri + 1}: ${row.join(' | ')}\n`;
            });
            text += '\n';
          } else {
            text += `[VI] ${b.original}\n`;
            text += `[EN] ${b.translated}\n\n`;
          }
        });
      }
    });
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (file?.name?.replace(/\.pdf$/i, '') || 'translation') + '_bilingual.txt';
    a.click();
  };

  const handleBlockEdit = (pageNum, blockIdx, newText, rIdx = null, cIdx = null) => {
    if (!result) return;
    setResult(prev => {
      const nextResult = JSON.parse(JSON.stringify(prev));
      const page = nextResult.pages.find(p => p.page_num === pageNum);
      if (page) {
        const block = page.blocks[blockIdx];
        if (block) {
          if (block.type === 'table' && rIdx !== null && cIdx !== null) {
            block.translated_cells[rIdx][cIdx] = newText;
          } else {
            block.translated = newText;
          }
        }
      }
      return nextResult;
    });
  };

  const registerPageRef = (pageNum, el) => {
    if (!el) {
      delete translatedPageRefs.current[pageNum];
      return;
    }
    translatedPageRefs.current[pageNum] = el;
  };

  const handleHtmlEdit = (pageNum, newHtml) => {
    setResult(prev => {
      if (!prev) return prev;
      const nextResult = JSON.parse(JSON.stringify(prev));
      const targetPage = nextResult.pages.find(p => p.page_num === pageNum);
      if (targetPage) {
        targetPage.translated_html = newHtml;
      }
      return nextResult;
    });
  };

  const formatTranslatedHtml = (html) => {
    if (!previewBold && !previewLineHeight) return html;

    const formattingRules = [
      previewBold ? 'font-weight:700 !important;' : '',
      previewLineHeight ? `line-height:${previewLineHeight} !important;` : '',
    ].join('');

    return `<div class="translation-export-format"><style>.translation-export-format,.translation-export-format *{${formattingRules}}</style>${html}</div>`;
  };

  const downloadPdf = async () => {
    if (!result) return;
    try {
      const mergedResult = JSON.parse(JSON.stringify(result));
      Object.entries(translatedPageRefs.current).forEach(([pageNum, el]) => {
        const page = mergedResult.pages?.find(p => p.page_num === Number(pageNum));
        if (page && el) page.translated_html = formatTranslatedHtml(el.innerHTML);
      });
      const res = await fetch(`${API_URL}/api/translate-pdf/download-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ result: mergedResult }),
      });
      if (!res.ok) {
        const responseError = await res.json().catch(() => null);
        throw new Error(responseError?.detail || 'Không thể tạo file PDF');
      }
      const blob = await res.blob();
      const a = document.createElement('a');
      const downloadUrl = URL.createObjectURL(blob);
      a.href = downloadUrl;
      a.download = (result.original_filename?.replace(/\.pdf$/i, '') || 'translation') + '_translated.pdf';
      a.click();
      URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      alert(err.message);
    }
  };

  const downloadDocx = async () => {
    if (!result) return;
    try {
      const htmlPages = Object.entries(translatedPageRefs.current).map(([pageNum, el]) => ({
        page_num: Number(pageNum),
        translated_html: formatTranslatedHtml(el?.innerHTML || ''),
      }));

      const mergedResult = JSON.parse(JSON.stringify(result));
      if (htmlPages.length > 0) {
        htmlPages.forEach(({ page_num, translated_html }) => {
          const page = mergedResult.pages?.find((p) => p.page_num === page_num);
          if (page) {
            page.translated_html = translated_html;
          }
        });
      }

      const res = await fetch(`${API_URL}/api/translate-pdf/download-edited-docx`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ result: mergedResult }),
      });
      if (!res.ok) throw new Error('Không thể tải file Word');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (result.original_filename?.replace(/\.pdf$/i, '') || 'translation') + '_translated.docx';
      a.click();
    } catch (err) {
      alert(err.message);
    }
  };

  if (status === 'idle') return <Dropzone onFiles={handleFile} />;

  if (status === 'configuring') {
    return (
      <div className="translate-status-screen" style={{ minHeight: 'calc(100vh - 120px)', padding: '24px 16px' }}>
        <div className="translate-config-card" style={{
          maxWidth: '560px',
          width: '100%',
          background: 'rgba(15, 23, 42, 0.75)',
          border: '1px solid rgba(148, 163, 184, 0.2)',
          borderRadius: '20px',
          padding: '28px 24px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
          color: '#f8fafc',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '20px' }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, #38bdf8, #0ea5e9)',
              display: 'grid',
              placeItems: 'center',
              color: '#020617',
              flexShrink: 0,
            }}>
              <FileText size={24} />
            </div>
            <div style={{ minWidth: 0 }}>
              <h3 style={{ fontSize: '18px', margin: '0 0 4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#f8fafc' }}>
                {file?.name}
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#94a3b8' }}>
                <span>{(file?.size ? (file.size / 1024 / 1024).toFixed(2) + ' MB' : '')}</span>
                <span>•</span>
                <span style={{
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  fontWeight: 600,
                  fontSize: '12px',
                }}>
                  {pdfNumPages} trang
                </span>
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '22px' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', color: '#e2e8f0' }}>
              Tùy chọn dịch cho tài liệu:
            </div>

            {/* Option 1: All pages */}
            <label style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              padding: '14px',
              borderRadius: '12px',
              border: `1px solid ${selectedRangeMode === 'all' ? '#38bdf8' : 'rgba(148, 163, 184, 0.2)'}`,
              background: selectedRangeMode === 'all' ? 'rgba(56, 189, 248, 0.08)' : 'rgba(2, 6, 23, 0.4)',
              cursor: 'pointer',
              marginBottom: '10px',
              transition: 'all 0.2s ease',
            }}>
              <input
                type="radio"
                name="rangeMode"
                checked={selectedRangeMode === 'all'}
                onChange={() => setSelectedRangeMode('all')}
                style={{ marginTop: '3px', accentColor: '#38bdf8' }}
              />
              <div>
                <div style={{ fontWeight: 600, fontSize: '14px', color: '#f8fafc' }}>
                  Dịch toàn bộ tài liệu ({pdfNumPages} trang)
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '3px' }}>
                  Tự động chia đợt thông minh (2 trang/đợt) chống nghẽn và đảm bảo không bao giờ bị timeout.
                </div>
              </div>
            </label>

            {/* Option 2: Custom range */}
            <label style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              padding: '14px',
              borderRadius: '12px',
              border: `1px solid ${selectedRangeMode === 'custom' ? '#38bdf8' : 'rgba(148, 163, 184, 0.2)'}`,
              background: selectedRangeMode === 'custom' ? 'rgba(56, 189, 248, 0.08)' : 'rgba(2, 6, 23, 0.4)',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}>
              <input
                type="radio"
                name="rangeMode"
                checked={selectedRangeMode === 'custom'}
                onChange={() => setSelectedRangeMode('custom')}
                style={{ marginTop: '3px', accentColor: '#38bdf8' }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '14px', color: '#f8fafc' }}>
                  Dịch theo khoảng trang tùy chọn
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '3px', marginBottom: '8px' }}>
                  Ví dụ: 1-3 (dịch 3 trang đầu) hoặc 1,3,5
                </div>
                {selectedRangeMode === 'custom' && (
                  <input
                    type="text"
                    value={customRangeText}
                    onChange={(e) => setCustomRangeText(e.target.value)}
                    placeholder={`1-${Math.min(pdfNumPages || 5, 5)}`}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid rgba(56, 189, 248, 0.4)',
                      background: '#090e1a',
                      color: '#f8fafc',
                      fontSize: '13px',
                      outline: 'none',
                    }}
                    onClick={(e) => e.stopPropagation()}
                  />
                )}
              </div>
            </label>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{
                flex: 1,
                padding: '12px',
                borderRadius: '12px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
              onClick={() => startTranslation(file, selectedRangeMode, pdfNumPages)}
            >
              <Languages size={18} /> Bắt đầu dịch ngay
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{
                padding: '12px 18px',
                borderRadius: '12px',
                background: 'rgba(148, 163, 184, 0.15)',
                color: '#e2e8f0',
                border: 'none',
                cursor: 'pointer',
              }}
              onClick={handleReset}
            >
              Đổi file
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'loading') {
    const cuteTips = [
      '☕ Hệ thống đang pha một ly tiếng Anh thật mượt cho bạn...',
      '🧠 AI đang cân từng dấu chấm phẩy để bản dịch đẹp hơn...',
      '✨ Chỉnh bố cục để file nhìn chuyên nghiệp như bản công chứng...',
      '🎯 Sắp xong rồi, chuẩn bị tải về nhé!'
    ];
    const tipIndex = Math.min(cuteTips.length - 1, Math.floor(progress / 25));

    return (
      <div className="translate-loading-stage">
        <div className="translate-loading-glow translate-loading-glow-1" />
        <div className="translate-loading-glow translate-loading-glow-2" />

        <div className="translate-loading-card">
          <div className="translate-loading-head">
            <div className="translate-loading-spinner-wrap">
              <Loader2 size={32} className="spin" />
            </div>
            <div>
              <h3 className="translate-loading-title">Đang dịch tài liệu cho bạn ✨</h3>
              <p className="translate-loading-file">{file?.name}</p>
            </div>
          </div>

          <div className="translate-loading-progress-wrap">
            <div className="translate-loading-progress-meta">
              <span>{loadingStep}</span>
              <span>{progress}%</span>
            </div>
            <div className="translate-loading-progress-bar">
              <div className="translate-loading-progress-fill" style={{ width: `${progress}%` }} />
            </div>
          </div>

          <p className="translate-loading-tip">{cuteTips[tipIndex]}</p>

          <div className="translate-loading-skeleton-grid">
            <div className="translate-loading-skeleton-page">
              <div className="translate-loading-skeleton-title">📄 Bản gốc</div>
              <div className="skeleton-line w-90" />
              <div className="skeleton-line w-70" />
              <div className="skeleton-line w-85" />
              <div className="skeleton-line w-60" />
              <div className="skeleton-line w-80" />
            </div>
            <div className="translate-loading-skeleton-page">
              <div className="translate-loading-skeleton-title">🌐 Bản dịch</div>
              <div className="skeleton-line w-80" />
              <div className="skeleton-line w-65" />
              <div className="skeleton-line w-90" />
              <div className="skeleton-line w-70" />
              <div className="skeleton-line w-85" />
            </div>
          </div>

          <div className="translate-loading-bottom">
            <div className="translate-loading-mini-cards">
              <div className="loading-mini-card">
                <div className="loading-mini-emoji">🧩</div>
                <div>
                  <div className="loading-mini-title">Giữ nguyên bố cục</div>
                  <div className="loading-mini-sub">Canh lề · khoảng cách · bảng biểu</div>
                </div>
              </div>
              <div className="loading-mini-card">
                <div className="loading-mini-emoji">📚</div>
                <div>
                  <div className="loading-mini-title">Thuật ngữ chuyên ngành</div>
                  <div className="loading-mini-sub">Ưu tiên văn phong hồ sơ pháp lý</div>
                </div>
              </div>
              <div className="loading-mini-card">
                <div className="loading-mini-emoji">🛡️</div>
                <div>
                  <div className="loading-mini-title">Xử lý an toàn</div>
                  <div className="loading-mini-sub">Tài liệu của bạn đang được xử lý cục bộ</div>
                </div>
              </div>
            </div>

            <div className="translate-loading-fun-strip">
              <span className="fun-dot" />
              <span className="fun-text">Gần xong rồi… chuẩn bị nhận bản dịch đẹp lung linh ✨</span>
              <span className="fun-dot" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="translate-status-screen">
        <AlertCircle size={48} color="#e53e3e" />
        <h3 style={{ color: '#e53e3e' }}>Dịch thất bại</h3>
        <p>{errorMsg}</p>
        <button className="btn btn-outline" onClick={handleReset} style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <RefreshCw size={15} /> Thử lại
        </button>
      </div>
    );
  }

  const isHtmlMode = result.mode === 'html';

  return (
    <div className="translate-result-container">
      <div className="translate-result-topbar">
        <div className="translate-topbar-left">
          <span className="translate-filename">{result.original_filename}</span>
          <span className="translate-meta">
            {result.total_pages} trang · {isHtmlMode ? '🟣 Gemini HTML' : (result.translator === 'deepl' ? '🔵 DeepL' : '🟢 Google Translate')}
            {result.failed_pages?.length > 0 && (
              <span style={{ color: '#e53e3e', marginLeft: 8 }}>
                · {result.failed_pages.length} trang chưa dịch được ({result.failed_pages.join(', ')})
              </span>
            )}
          </span>
        </div>
        <div className="translate-topbar-right">
          <div className="translate-zoom-controls">
            <button className="toolbar-icon-btn" onClick={() => setPdfScale(s => Math.max(0.5, s - 0.2))} title="Thu nhỏ">
              <ZoomOut size={15} />
            </button>
            <span style={{ fontSize: 12, minWidth: 40, textAlign: 'center' }}>{Math.round(pdfScale * 100)}%</span>
            <button className="toolbar-icon-btn" onClick={() => setPdfScale(s => Math.min(2.5, s + 0.2))} title="Phóng to">
              <ZoomIn size={15} />
            </button>
          </div>
          <button className="btn btn-outline" style={{ fontSize: 13, padding: '6px 14px', display: 'flex', gap: 6 }} onClick={handleReset}>
            <RefreshCw size={14} /> Dịch file khác
          </button>
        </div>
      </div>

      <div className="translate-panels">
        {/* LEFT: original pages — independent scroll */}
        <div className="translate-panel-col translate-panel-col-left" ref={containerRef}>
          <div className="translate-col-header">
            <FileText size={14} /> Bản gốc (Tiếng Việt)
          </div>
          <div className="translate-col-scroll">
            <Document file={objectUrl} onLoadSuccess={({ numPages }) => setPdfNumPages(numPages)}>
              {Array.from({ length: pdfNumPages || 0 }, (_, idx) => (
                <div key={idx + 1} className="translate-original-page-block">
                  <div className="translate-page-label">Trang {idx + 1}</div>
                  <Page
                    pageNumber={idx + 1}
                    scale={pdfScale}
                    width={Math.min(560, containerWidth)}
                    renderTextLayer={false}
                    renderAnnotationLayer={false}
                  />
                </div>
              ))}
            </Document>
          </div>
        </div>

        {/* RIGHT: grouped translations — independent scroll */}
        <div className="translate-panel-col translate-panel-col-right">
          <div className="translate-col-header">
            <Languages size={14} /> Bản dịch (English)
          </div>
          <div className="translate-col-scroll">
            {(result.pages || [])
              .filter(p => p.is_group_lead !== false)
              .map(page => (
                <div key={page.page_num} className="translate-translated-block">
                  <div className="translate-page-label">
                    Trang {page.group_pages?.length > 1
                      ? `${page.group_pages[0]}–${page.group_pages[page.group_pages.length - 1]}`
                      : page.page_num}
                  </div>
                  {isHtmlMode ? (
                    <HtmlTranslatedPage
                      html={page.translated_html || ''}
                      pageNum={page.page_num}
                      onHtmlEdit={handleHtmlEdit}
                      registerPageRef={registerPageRef}
                      previewBold={previewBold}
                      previewLineHeight={previewLineHeight}
                    />
                  ) : (
                    <div className="translated-page-shell">
                      <TranslatedPage
                        pageData={page}
                        pageNum={page.page_num}
                        onBlockEdit={handleBlockEdit}
                      />
                    </div>
                  )}
                </div>
              ))
            }
          </div>
        </div>
      </div>

      <div className="translate-pager translate-editor-toolbar">
        <button
          type="button"
          className={`btn btn-outline${previewBold ? ' translate-format-active' : ''}`}
          aria-pressed={previewBold}
          onClick={() => setPreviewBold(current => !current)}
        >
          <Tag size={14} style={{ marginRight: 6 }} /> Tô đậm
        </button>
        {['1.3', '1.5', '1.8'].map(lineHeight => (
          <button
            key={lineHeight}
            type="button"
            className={`btn btn-outline${previewLineHeight === lineHeight ? ' translate-format-active' : ''}`}
            aria-pressed={previewLineHeight === lineHeight}
            onClick={() => setPreviewLineHeight(current => current === lineHeight ? null : lineHeight)}
          >
            Giãn dòng {lineHeight}
          </button>
        ))}

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" style={{ fontSize: 13, padding: '6px 14px', display: 'flex', gap: 6 }} onClick={downloadDocx}>
            <Download size={14} /> Tải DOCX
          </button>
          <button className="btn btn-primary" style={{ fontSize: 13, padding: '6px 14px', display: 'flex', gap: 6, background: '#38a169', borderColor: '#38a169' }} onClick={downloadPdf}>
            <Download size={14} /> Tải PDF
          </button>
          <button className="btn btn-outline" style={{ fontSize: 13, padding: '6px 14px', display: 'flex', gap: 6 }} onClick={downloadTranslation}>
            <Download size={14} /> Tải .txt
          </button>
        </div>
      </div>
    </div>
  );
};

export default TranslateWorkspace;
