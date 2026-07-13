import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Download,
  Eye,
  FileText,
  Layers,
  Loader2,
  Plus,
  RefreshCw,
  RotateCcw,
  RotateCw,
  Scissors,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react';
import { API_URL } from '../config/api';
import PdfRenderer from './PdfRenderer';

const MAX_PREVIEW_GROUPS = 20;
const MAX_PREVIEW_PAGES_PER_GROUP = 12;
const PREVIEW_GROUP_BATCH_SIZE = 20;
const PREVIEW_PAGE_BATCH_SIZE = 12;
const MAX_VISIBLE_RANGE_ROWS = 40;
const RANGE_ROW_BATCH_SIZE = 40;

const readPdfPageCount = async (rawFile) => {
  const { getDocument } = await import('pdfjs-dist');
  const buf = await rawFile.arrayBuffer();
  const loadingTask = getDocument({ data: buf });
  const pdf = await loadingTask.promise;
  const pageCount = pdf.numPages;
  await pdf.destroy();
  return pageCount;
};

const clampPage = (value, totalPages) => {
  const page = Number.parseInt(value, 10);
  if (!Number.isFinite(page)) return null;
  if (!totalPages) return Math.max(1, page);
  return Math.min(Math.max(1, page), totalPages);
};

const buildPageGroupForRange = (range, totalPages) => {
  const from = clampPage(range.from, totalPages);
  const to = clampPage(range.to, totalPages);
  if (!from || !to) return null;

  const start = Math.min(from, to);
  const end = Math.max(from, to);
  return { start, end, pageCount: end - start + 1 };
};

const SplitWorkspace = ({ initialFiles, onCancel }) => {
  const [file, setFile] = useState(initialFiles?.[0] || null);
  const [totalPages, setTotalPages] = useState(null);
  const [ranges, setRanges] = useState([{ from: '1', to: '1' }]);
  const [pageRotations, setPageRotations] = useState({});
  const [visibleGroupCount, setVisibleGroupCount] = useState(MAX_PREVIEW_GROUPS);
  const [visiblePagesByGroup, setVisiblePagesByGroup] = useState({});
  const [visibleRangeCount, setVisibleRangeCount] = useState(MAX_VISIBLE_RANGE_ROWS);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const handleFile = async (rawFile) => {
    setFile(rawFile);
    setStatus('idle');
    setError('');
    setPageRotations({});
    setVisibleGroupCount(MAX_PREVIEW_GROUPS);
    setVisiblePagesByGroup({});
    setVisibleRangeCount(MAX_VISIBLE_RANGE_ROWS);

    try {
      const pageCount = await readPdfPageCount(rawFile);
      setTotalPages(pageCount);
      setRanges([{ from: '1', to: String(pageCount) }]);
    } catch {
      setTotalPages(null);
      setRanges([{ from: '1', to: '1' }]);
      setError('Không đọc được số trang. Bạn vẫn có thể nhập khoảng trang thủ công.');
    }
  };

  useEffect(() => {
    const rawFile = initialFiles?.[0];
    if (!rawFile) return undefined;

    let isCancelled = false;
    const loadInitialFile = async () => {
      try {
        const pageCount = await readPdfPageCount(rawFile);
        if (isCancelled) return;
        setTotalPages(pageCount);
        setRanges([{ from: '1', to: String(pageCount) }]);
      } catch {
        if (isCancelled) return;
        setTotalPages(null);
        setRanges([{ from: '1', to: '1' }]);
        setError('Không đọc được số trang. Bạn vẫn có thể nhập khoảng trang thủ công.');
      }
    };

    loadInitialFile();
    return () => {
      isCancelled = true;
    };
  }, [initialFiles]);

  const normalizedGroups = useMemo(() => ranges
    .map((range, index) => {
      const pageGroup = buildPageGroupForRange(range, totalPages);
      if (!pageGroup) return null;
      return {
        id: `part-${index}`,
        index,
        ...pageGroup,
      };
    })
    .filter(Boolean), [ranges, totalPages]);

  const previewGroups = useMemo(() => normalizedGroups.slice(0, visibleGroupCount), [normalizedGroups, visibleGroupCount]);
  const hiddenPreviewGroupCount = Math.max(0, normalizedGroups.length - previewGroups.length);
  const selectedPageCount = normalizedGroups.reduce((sum, group) => sum + group.pageCount, 0);
  const rotatedPageCount = Object.values(pageRotations).filter(Boolean).length;
  const visibleRanges = ranges.slice(0, visibleRangeCount);
  const hiddenRangeCount = Math.max(0, ranges.length - visibleRanges.length);

  const resetPreviewWindow = () => {
    setVisibleGroupCount(MAX_PREVIEW_GROUPS);
    setVisiblePagesByGroup({});
    setVisibleRangeCount(MAX_VISIBLE_RANGE_ROWS);
  };

  const addRange = () => {
    setRanges((current) => [...current, { from: '', to: '' }]);
    resetPreviewWindow();
  };
  const removeRange = (index) => {
    setRanges((current) => current.filter((_, rowIndex) => rowIndex !== index));
    resetPreviewWindow();
  };
  const updateRange = (index, key, value) => {
    setRanges((current) => current.map((row, rowIndex) => (
      rowIndex === index ? { ...row, [key]: value } : row
    )));
    resetPreviewWindow();
  };

  const rotatePage = (pageNumber, angle) => {
    setPageRotations((current) => ({
      ...current,
      [pageNumber]: ((current[pageNumber] || 0) + angle + 360) % 360,
    }));
  };

  const showMoreGroups = () => {
    setVisibleGroupCount((current) => Math.min(current + PREVIEW_GROUP_BATCH_SIZE, normalizedGroups.length));
  };

  const showMorePages = (groupId, total) => {
    setVisiblePagesByGroup((current) => {
      const currentCount = current[groupId] || MAX_PREVIEW_PAGES_PER_GROUP;
      return {
        ...current,
        [groupId]: Math.min(currentCount + PREVIEW_PAGE_BATCH_SIZE, total),
      };
    });
  };

  const showMoreRanges = () => {
    setVisibleRangeCount((current) => Math.min(current + RANGE_ROW_BATCH_SIZE, ranges.length));
  };

  const applySuggestion = (mode) => {
    if (!totalPages) return;

    if (mode === 'all') {
      setRanges([{ from: '1', to: String(totalPages) }]);
      resetPreviewWindow();
      return;
    }

    if (mode === 'each') {
      setRanges(Array.from({ length: totalPages }, (_, index) => {
        const page = String(index + 1);
        return { from: page, to: page };
      }));
      resetPreviewWindow();
      return;
    }

    if (mode === 'first-rest') {
      setRanges(totalPages > 1
        ? [{ from: '1', to: '1' }, { from: '2', to: String(totalPages) }]
        : [{ from: '1', to: '1' }]);
      resetPreviewWindow();
      return;
    }

    const chunkSize = mode === 'pairs' ? 2 : 5;
    const chunks = [];
    for (let start = 1; start <= totalPages; start += chunkSize) {
      chunks.push({ from: String(start), to: String(Math.min(totalPages, start + chunkSize - 1)) });
    }
    setRanges(chunks);
    resetPreviewWindow();
  };

  const split = async () => {
    if (!file) return;
    setStatus('loading');
    setError('');

    try {
      if (!normalizedGroups.length) throw new Error('Vui lòng nhập ít nhất một khoảng trang');

      const rangeStr = normalizedGroups
        .map((group) => {
          const first = group.start;
          const last = group.end;
          return first === last ? String(first) : `${first}-${last}`;
        })
        .join(',');

      const activeRotations = Object.fromEntries(
        Object.entries(pageRotations).filter(([, rotation]) => rotation)
      );

      const form = new FormData();
      form.append('file', file);
      form.append('ranges', rangeStr);
      form.append('page_rotations', JSON.stringify(activeRotations));

      const res = await fetch(`${API_URL}/api/split`, { method: 'POST', body: form });
      if (!res.ok) throw new Error((await res.json()).detail || 'Lỗi cắt PDF');

      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = file.name.replace(/\.pdf$/i, '') + '_split.zip';
      a.click();
      URL.revokeObjectURL(a.href);
      setStatus('done');
    } catch (e) {
      setError(e.message);
      setStatus('error');
    }
  };

  return (
    <div className="split-workspace">
      <div className="split-header">
        <div>
          <p className="split-eyebrow">Cắt PDF có xem trước</p>
          <h2><Scissors size={22} /> Cắt file thành bộ hồ sơ riêng</h2>
          <span>Chọn khoảng trang, xem từng file sắp xuất, xoay trang sai chiều rồi tải ZIP.</span>
        </div>
        <button className="btn btn-outline" onClick={onCancel}>
          <RefreshCw size={14} /> Chọn lại
        </button>
      </div>

      <div className="split-layout">
        <aside className="split-control-panel">
          <div className="split-file-picker">
            <button className="btn btn-outline" onClick={() => inputRef.current?.click()}>
              <Upload size={14} /> Chọn file PDF
            </button>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf"
              hidden
              onChange={(event) => event.target.files?.[0] && handleFile(event.target.files[0])}
            />
            {file && (
              <div className="split-file-meta">
                <FileText size={16} />
                <div>
                  <strong>{file.name}</strong>
                  <span>{totalPages ? `${totalPages} trang` : 'Chưa xác định số trang'}</span>
                </div>
              </div>
            )}
          </div>

          {file && (
            <>
              <div className="split-suggestions">
                <div className="split-panel-title">
                  <Sparkles size={16} />
                  Đề xuất cắt nhanh
                </div>
                <button type="button" onClick={() => applySuggestion('all')} disabled={!totalPages}>Giữ nguyên 1 file</button>
                <button type="button" onClick={() => applySuggestion('each')} disabled={!totalPages}>Mỗi trang 1 file</button>
                <button type="button" onClick={() => applySuggestion('first-rest')} disabled={!totalPages}>Trang đầu + phần còn lại</button>
                <button type="button" onClick={() => applySuggestion('pairs')} disabled={!totalPages}>Từng cặp 2 trang</button>
                <button type="button" onClick={() => applySuggestion('chunks')} disabled={!totalPages}>Mỗi 5 trang</button>
              </div>

              <div className="split-range-panel">
                <div className="split-panel-title">
                  <Layers size={16} />
                  Khoảng trang xuất ra
                </div>
                {visibleRanges.map((range, index) => (
                  <div key={`range-${index}`} className="split-range-row">
                    <span>File {index + 1}</span>
                    <input
                      type="number"
                      min="1"
                      max={totalPages || 9999}
                      value={range.from}
                      onChange={(event) => updateRange(index, 'from', event.target.value)}
                      aria-label={`Trang bắt đầu file ${index + 1}`}
                    />
                    <small>đến</small>
                    <input
                      type="number"
                      min="1"
                      max={totalPages || 9999}
                      value={range.to}
                      onChange={(event) => updateRange(index, 'to', event.target.value)}
                      aria-label={`Trang kết thúc file ${index + 1}`}
                    />
                    {ranges.length > 1 && (
                      <button type="button" className="split-icon-danger" onClick={() => removeRange(index)} aria-label={`Xóa file ${index + 1}`}>
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                ))}
                {hiddenRangeCount > 0 && (
                  <button type="button" className="btn btn-outline split-add-range" onClick={showMoreRanges}>
                    Hiện thêm {Math.min(RANGE_ROW_BATCH_SIZE, hiddenRangeCount)} khoảng
                  </button>
                )}
                <button className="btn btn-outline split-add-range" onClick={addRange}>
                  <Plus size={14} /> Thêm file cắt
                </button>
              </div>

              <div className="split-summary">
                <div><Eye size={16} /> {normalizedGroups.length} file cắt</div>
                <div>{selectedPageCount} trang sẽ được xuất</div>
                <div>{rotatedPageCount} trang đã xoay</div>
              </div>
            </>
          )}
        </aside>

        <main className="split-preview-panel">
          {!file ? (
            <div className="split-empty-preview">
              <Scissors size={42} />
              <strong>Chọn một PDF để xem trước bản cắt</strong>
              <span>Các file sắp xuất sẽ hiện ở đây trước khi tải về.</span>
            </div>
          ) : (
            <>
              <div className="split-preview-head">
                <div>
                  <p>Bản xem trước cắt file</p>
                  <h3>User sẽ nhìn thấy từng phần trước khi xuất</h3>
                </div>
                <button className="btn btn-primary" onClick={split} disabled={!file || status === 'loading' || normalizedGroups.length === 0}>
                  {status === 'loading'
                    ? <><Loader2 size={14} className="spin" /> Đang cắt...</>
                    : <><Download size={14} /> Xuất ZIP</>}
                </button>
              </div>

              <div className="split-preview-list">
                {previewGroups.map((group) => {
                  const visiblePageCount = visiblePagesByGroup[group.id] || MAX_PREVIEW_PAGES_PER_GROUP;
                  const visiblePages = Array.from(
                    { length: Math.min(visiblePageCount, group.pageCount) },
                    (_, index) => group.start + index
                  );
                  const hiddenPageCount = Math.max(0, group.pageCount - visiblePages.length);

                  return (
                    <section className="split-preview-group" key={group.id}>
                      <div className="split-preview-group-head">
                        <strong>File {group.index + 1}</strong>
                        <span>
                          Trang {group.start}
                          {group.pageCount > 1 ? `-${group.end}` : ''}
                          {' '}· {group.pageCount} trang
                        </span>
                      </div>
                      <div className="split-page-strip">
                        {visiblePages.map((pageNumber) => (
                          <div className="split-page-card" key={`${group.id}-${pageNumber}`}>
                            <div className="split-page-preview">
                              <PdfRenderer
                                file={file}
                                pageNum={pageNumber}
                                width={132}
                                rotation={pageRotations[pageNumber] || null}
                              />
                            </div>
                            <div className="split-page-footer">
                              <span>Trang {pageNumber}</span>
                              <div>
                                <button type="button" onClick={() => rotatePage(pageNumber, 270)} aria-label={`Xoay trái trang ${pageNumber}`}>
                                  <RotateCcw size={14} />
                                </button>
                                <button type="button" onClick={() => rotatePage(pageNumber, 180)} aria-label={`Lật trang ${pageNumber}`}>
                                  180
                                </button>
                                <button type="button" onClick={() => rotatePage(pageNumber, 90)} aria-label={`Xoay phải trang ${pageNumber}`}>
                                  <RotateCw size={14} />
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                        {hiddenPageCount > 0 && (
                          <div className="split-page-card split-page-overflow">
                            <button
                              type="button"
                              className="split-page-preview"
                              onClick={() => showMorePages(group.id, group.pageCount)}
                            >
                              <strong>+{hiddenPageCount}</strong>
                              <span>Hiện thêm trang</span>
                            </button>
                          </div>
                        )}
                      </div>
                    </section>
                  );
                })}
                {hiddenPreviewGroupCount > 0 && (
                  <div className="split-preview-limit-note">
                    <span>Còn {hiddenPreviewGroupCount} file cắt chưa hiện thumbnail để tránh quá tải trình duyệt. Khi xuất ZIP vẫn cắt đầy đủ theo các khoảng đã nhập.</span>
                    <button type="button" onClick={showMoreGroups}>Hiện thêm file</button>
                  </div>
                )}
              </div>
            </>
          )}

          {status === 'done' && <p className="split-status-success">Đã tải về file ZIP chứa các PDF đã cắt.</p>}
          {error && <p className="split-status-error">{error}</p>}
        </main>
      </div>
    </div>
  );
};

export default SplitWorkspace;
