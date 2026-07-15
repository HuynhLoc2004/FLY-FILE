import { useRef, useState } from 'react';
import {
  Download, FileText, Loader2, RefreshCw, RotateCcw, RotateCw,
  Scissors, Undo2, Upload,
} from 'lucide-react';
import { API_URL } from '../config/api';
import { Document } from 'react-pdf';
import { PdfPageThumbnail } from './PdfRenderer';

const SplitWorkspace = ({ initialFiles, onCancel }) => {
  const [file, setFile] = useState(initialFiles?.[0] || null);
  const [totalPages, setTotalPages] = useState(null);
  const [removedPages, setRemovedPages] = useState(() => new Set());
  const [pageRotations, setPageRotations] = useState({});
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const resetSelection = () => {
    setRemovedPages(new Set());
    setPageRotations({});
    setStatus('idle');
    setError('');
  };

  const loadFile = (rawFile) => {
    setFile(rawFile);
    setTotalPages(null);
    resetSelection();
  };

  const toggleRemovedPage = (pageNumber) => {
    setRemovedPages((current) => {
      const next = new Set(current);
      if (next.has(pageNumber)) next.delete(pageNumber);
      else next.add(pageNumber);
      return next;
    });
    setStatus('idle');
    setError('');
  };

  const rotatePage = (pageNumber, angle) => {
    if (removedPages.has(pageNumber)) return;
    setPageRotations((current) => ({
      ...current,
      [pageNumber]: ((current[pageNumber] || 0) + angle + 360) % 360,
    }));
  };

  const restoreAllPages = () => {
    setRemovedPages(new Set());
    setStatus('idle');
    setError('');
  };

  const downloadResult = async () => {
    if (!file || !totalPages) return;
    if (!removedPages.size) {
      setError('Hãy bấm icon cái kéo trên ít nhất một trang cần cắt bỏ.');
      return;
    }
    if (removedPages.size >= totalPages) {
      setError('Không thể cắt bỏ toàn bộ trang. Hãy giữ lại ít nhất một trang.');
      return;
    }
    setStatus('loading');
    setError('');
    try {
      const rotations = Object.fromEntries(Object.entries(pageRotations).filter(
        ([page, rotation]) => rotation && !removedPages.has(Number(page)),
      ));
      const form = new FormData();
      form.append('file', file);
      form.append('removed_pages', JSON.stringify([...removedPages].sort((a, b) => a - b)));
      form.append('page_rotations', JSON.stringify(rotations));
      const response = await fetch(`${API_URL}/api/remove-pages`, { method: 'POST', body: form });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Không thể cắt trang PDF');
      }
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = file.name.replace(/\.pdf$/i, '') + '_da_cat_trang.pdf';
      anchor.click();
      URL.revokeObjectURL(url);
      setStatus('done');
    } catch (downloadError) {
      setError(downloadError.message);
      setStatus('error');
    }
  };

  const remainingPageCount = Math.max(0, (totalPages || 0) - removedPages.size);
  const pages = totalPages ? Array.from({ length: totalPages }, (_, index) => index + 1) : [];

  return (
    <div className="split-workspace">
      <div className="split-header">
        <div>
          <p className="split-eyebrow">Cắt bỏ trang PDF</p>
          <h2><Scissors size={22} /> Chọn đúng trang cần cắt bỏ</h2>
          <span>Bấm icon cái kéo trên từng trang. Các trang còn lại giữ nguyên nội dung và thứ tự gốc.</span>
        </div>
        <button className="btn btn-outline" onClick={onCancel}><RefreshCw size={14} /> Chọn lại</button>
      </div>

      <div className="split-layout">
        <aside className="split-control-panel">
          <div className="split-file-picker">
            <button className="btn btn-outline" onClick={() => inputRef.current?.click()}>
              <Upload size={14} /> Chọn file PDF
            </button>
            <input ref={inputRef} type="file" accept=".pdf,application/pdf" hidden
              onChange={(event) => event.target.files?.[0] && loadFile(event.target.files[0])} />
            {file && (
              <div className="split-file-meta">
                <FileText size={16} />
                <div><strong>{file.name}</strong><span>{totalPages ? `${totalPages} trang` : 'Đang đọc các trang...'}</span></div>
              </div>
            )}
          </div>

          {file && totalPages && (
            <>
              <div className="split-instruction">
                <Scissors size={18} />
                <div><strong>Cách cắt trang</strong><span>Bấm nút kéo ngay trên trang muốn bỏ. Bấm lại để hoàn tác.</span></div>
              </div>
              <div className="split-summary">
                <div>{totalPages} trang gốc</div>
                <div className={removedPages.size ? 'split-summary-removed' : ''}>{removedPages.size} trang sẽ bị cắt bỏ</div>
                <div>{remainingPageCount} trang được giữ lại</div>
              </div>
              {removedPages.size > 0 && (
                <button type="button" className="btn btn-outline" onClick={restoreAllPages}>
                  <Undo2 size={14} /> Khôi phục tất cả trang
                </button>
              )}
              <button className="btn btn-primary" onClick={downloadResult}
                disabled={status === 'loading' || !removedPages.size || !remainingPageCount}>
                {status === 'loading'
                  ? <><Loader2 size={14} className="spin" /> Đang tạo file...</>
                  : <><Download size={14} /> Tải PDF sau khi cắt</>}
              </button>
            </>
          )}
        </aside>

        <main className="split-preview-panel">
          {!file ? (
            <div className="split-empty-preview">
              <Scissors size={42} /><strong>Chọn một PDF để hiện toàn bộ trang</strong>
              <span>Mỗi trang sẽ có nút kéo riêng để bạn chọn cắt bỏ.</span>
            </div>
          ) : (
            <Document
              className="split-pdf-document"
              file={file}
              onLoadSuccess={({ numPages }) => setTotalPages(numPages)}
              onLoadError={() => setError('Không đọc được các trang trong file PDF. Vui lòng chọn file khác.')}
              loading={<div className="split-empty-preview"><Loader2 size={36} className="spin" /><strong>Đang mở file PDF...</strong></div>}
              error={<div className="split-empty-preview"><strong>Không thể mở file PDF</strong><span>Vui lòng kiểm tra và chọn lại file.</span></div>}
            >
              {totalPages && (
                <>
                  <div className="split-preview-head">
                    <div><p>Toàn bộ trang trong file</p><h3>Giữ nguyên số trang gốc từ 1 đến {totalPages}</h3></div>
                    <span className="split-page-count">{remainingPageCount}/{totalPages} trang được giữ</span>
                  </div>
                  <div className="split-all-pages-grid">
                    {pages.map((pageNumber) => {
                      const isRemoved = removedPages.has(pageNumber);
                      return (
                        <article className={`split-page-card${isRemoved ? ' split-page-card-removed' : ''}`} key={pageNumber}>
                          <div className="split-page-preview">
                            <PdfPageThumbnail pageNum={pageNumber} width={150} rotation={pageRotations[pageNumber] || null} />
                            <button type="button" className="split-cut-page-button"
                              onClick={() => toggleRemovedPage(pageNumber)}
                              aria-label={isRemoved ? `Khôi phục trang ${pageNumber}` : `Cắt bỏ trang ${pageNumber}`}
                              title={isRemoved ? 'Bấm để khôi phục trang' : 'Cắt bỏ trang này'}>
                              {isRemoved ? <Undo2 size={18} /> : <Scissors size={18} />}
                            </button>
                            {isRemoved && <div className="split-removed-label">Đã cắt</div>}
                          </div>
                          <div className="split-page-footer">
                            <span>Trang {pageNumber}</span>
                            <div>
                              <button type="button" disabled={isRemoved} onClick={() => rotatePage(pageNumber, 270)} aria-label={`Xoay trái trang ${pageNumber}`}><RotateCcw size={14} /></button>
                              <button type="button" disabled={isRemoved} onClick={() => rotatePage(pageNumber, 90)} aria-label={`Xoay phải trang ${pageNumber}`}><RotateCw size={14} /></button>
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </>
              )}
            </Document>
          )}
          {status === 'done' && <p className="split-status-success">Đã tải PDF mới. Các trang được giữ nguyên theo đúng thứ tự ban đầu.</p>}
          {error && <p className="split-status-error">{error}</p>}
        </main>
      </div>
    </div>
  );
};

export default SplitWorkspace;
