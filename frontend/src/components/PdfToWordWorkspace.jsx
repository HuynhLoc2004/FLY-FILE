import { useEffect, useState, useRef } from 'react';
import { renderAsync } from 'docx-preview';
import {
  FileText, Download, RefreshCw, Loader2,
  AlertCircle, UploadCloud, CheckCircle2, Eye,
} from 'lucide-react';
import { API_URL } from '../config/api';
import ProcessingModal from './ProcessingModal';

const DOCX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';


const PdfToWordWorkspace = () => {
  const [file, setFile]               = useState(null);
  const [status, setStatus]           = useState('idle'); // idle|loading|done|error
  const [progress, setProgress]       = useState(0);
  const [loadingStep, setLoadingStep] = useState('');
  const [errorMsg, setErrorMsg]       = useState('');
  const [resultBlob, setResultBlob]   = useState(null);
  const [resultName, setResultName]   = useState('');
  const [dragging, setDragging]       = useState(false);
  const [previewStatus, setPreviewStatus] = useState('idle'); // idle|loading|ready|error
  const [previewError, setPreviewError] = useState('');
  const inputRef = useRef(null);
  const previewRef = useRef(null);

  useEffect(() => {
    if (status !== 'done' || !resultBlob || !previewRef.current) return undefined;

    let cancelled = false;
    const container = previewRef.current;
    container.innerHTML = '';
    setPreviewStatus('loading');
    setPreviewError('');

    renderAsync(resultBlob, container, container, {
      className: 'docx',
      inWrapper: true,
      breakPages: true,
      ignoreWidth: false,
      ignoreHeight: false,
      ignoreFonts: false,
      renderHeaders: true,
      renderFooters: true,
    })
      .then(() => {
        if (!cancelled) setPreviewStatus('ready');
      })
      .catch((error) => {
        if (cancelled) return;
        container.innerHTML = '';
        setPreviewError(error?.message || 'Không thể hiển thị bản xem trước.');
        setPreviewStatus('error');
      });

    return () => {
      cancelled = true;
      container.innerHTML = '';
    };
  }, [status, resultBlob]);

  const formatSize = (b) => {
    if (!b) return '0 B';
    const k = 1024, s = ['B','KB','MB','GB'];
    const i = Math.floor(Math.log(b) / Math.log(k));
    return (b / Math.pow(k, i)).toFixed(1) + ' ' + s[i];
  };

  const isPdf = (f) => f && f.name.toLowerCase().endsWith('.pdf');

  // ── convert ─────────────────────────────────────────────────────────────────
  const convert = async (f) => {
    if (!f || !isPdf(f)) return;
    setFile(f);
    setStatus('loading');
    setProgress(0);
    setErrorMsg('');

    let p = 0;
    const steps = [
      { t: 20, msg: 'Đang phân tích cấu trúc PDF...' },
      { t: 50, msg: 'Đang nhận diện bảng biểu và định dạng...' },
      { t: 80, msg: 'Đang tạo file Word...' },
      { t: 98, msg: 'Hoàn thiện tài liệu...' },
    ];
    const timer = setInterval(() => {
      if (p < 25) p += Math.floor(Math.random() * 6) + 4;
      else if (p < 70) p += Math.floor(Math.random() * 3) + 1;
      else if (p < 97) p += 1;
      if (p > 97) p = 97;
      setProgress(p);
      setLoadingStep((steps.find(s => p < s.t) || steps[3]).msg);
    }, 200);

    try {
      const fd = new FormData();
      fd.append('file', f);
      const res = await fetch(`${API_URL}/api/pdf-to-word`, { method: 'POST', body: fd });
      clearInterval(timer);
      if (!res.ok) {
        const responseText = await res.text();
        let detail = responseText;
        try { detail = JSON.parse(responseText).detail || responseText; } catch { /* plain-text server error */ }
        throw new Error(detail || `Chuyển đổi thất bại (HTTP ${res.status})`);
      }
      const blob = await res.blob();
      const contentType = res.headers.get('content-type') || blob.type;
      if (!blob.size || !contentType.toLowerCase().includes(DOCX_CONTENT_TYPE)) {
        throw new Error('Máy chủ không trả về file Word hợp lệ. Vui lòng thử lại.');
      }
      setResultBlob(blob);
      setResultName(f.name.replace(/\.pdf$/i, '') + '.docx');
      setProgress(100);
      setTimeout(() => setStatus('done'), 350);
    } catch (err) {
      clearInterval(timer);
      setErrorMsg(err.message);
      setStatus('error');
    }
  };

  // ── file pick handlers ───────────────────────────────────────────────────────
  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (!f) return;
    if (!isPdf(f)) { alert('Vui lòng chọn file PDF'); return; }
    convert(f);
  };

  const handleChange = (e) => {
    const f = e.target.files?.[0];
    if (f) convert(f);
  };

  const reset = () => {
    setFile(null);
    setStatus('idle');
    setResultBlob(null);
    setResultName('');
    setErrorMsg('');
    setProgress(0);
    setPreviewStatus('idle');
    setPreviewError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  const download = () => {
    if (!resultBlob) return;
    const a = document.createElement('a');
    const objectUrl = URL.createObjectURL(resultBlob);
    a.href = objectUrl;
    a.download = resultName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  };

  // ── idle: dropzone ───────────────────────────────────────────────────────────
  if (status === 'idle') return (
    <div
      className={`dropzone${dragging ? ' active' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={(e) => { if (e.currentTarget.contains(e.relatedTarget)) return; setDragging(false); }}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      style={{ cursor: 'pointer' }}
    >
      <input ref={inputRef} type="file" accept=".pdf" hidden onChange={handleChange} />
      <UploadCloud className="dropzone-icon" size={60} />
      <button className="dropzone-btn" onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}>
        Chọn file PDF
      </button>
      <div className="dropzone-hint">hoặc kéo thả file PDF vào đây</div>
      <div className="dropzone-formats">
        Định dạng hỗ trợ:&nbsp;
        <span className="format-badge ml-1" style={{ background: '#fee2e2', color: '#ef4444' }}>PDF</span>
      </div>
    </div>
  );

  // ── loading ──────────────────────────────────────────────────────────────────
  if (status === 'loading') return (
    <ProcessingModal
      isOpen={true}
      progress={progress}
      title="Đang chuyển đổi PDF sang Word..."
      fileName={file?.name}
      stepText={loadingStep}
    />
  );

  // ── error ────────────────────────────────────────────────────────────────────
  if (status === 'error') return (
    <div style={{ maxWidth: 500, margin: '80px auto', padding: 36, background: '#fff', borderRadius: 12, boxShadow: '0 4px 20px rgba(0,0,0,0.08)', textAlign: 'center' }}>
      <AlertCircle size={48} style={{ color: '#e53e3e', margin: '0 auto 16px' }} />
      <h3 style={{ fontSize: 18, fontWeight: 600, color: '#e53e3e', marginBottom: 8 }}>Chuyển đổi thất bại</h3>
      <p style={{ fontSize: 13, color: '#4a5568', marginBottom: 24 }}>{errorMsg}</p>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <button className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 6 }} onClick={() => convert(file)}>
          <RefreshCw size={15} /> Thử lại
        </button>
        <button className="btn btn-outline" onClick={reset}>Chọn file khác</button>
      </div>
    </div>
  );

  // ── done ─────────────────────────────────────────────────────────────────────
  return (
    <div className="pdf-word-result-workspace">
      <div className="pdf-word-result-heading">
        <div className="pdf-word-success-icon"><CheckCircle2 size={30} /></div>
        <div>
          <h3>Chuyển đổi thành công!</h3>
          <p>{file?.name}</p>
        </div>
      </div>

      <div className="pdf-word-result-grid">
        <aside className="pdf-word-result-sidebar">
          <div className="pdf-word-file-card">
            <div className="pdf-word-file-icon">
              <FileText size={24} />
            </div>
            <div className="pdf-word-file-meta">
              <strong>{resultName}</strong>
              <span>Microsoft Word (.docx) · {formatSize(resultBlob?.size)}</span>
            </div>
          </div>

          <div className="pdf-word-result-note">
            <Eye size={17} />
            <p>Bản xem trước giúp kiểm tra nhanh nội dung. File tải xuống vẫn giữ định dạng DOCX để chỉnh sửa trong Word.</p>
          </div>

          <div className="pdf-word-result-actions">
            <button className="btn btn-primary" onClick={download}>
              <Download size={16} /> Tải file Word
            </button>
            <button className="btn btn-outline" onClick={reset}>
              <RefreshCw size={14} /> Chuyển file khác
            </button>
          </div>
        </aside>

        <section className="pdf-word-preview-panel">
          <header className="pdf-word-preview-header">
            <div>
              <Eye size={18} />
              <strong>Xem trước tài liệu Word</strong>
            </div>
            <span>{previewStatus === 'ready' ? 'Đã tải xong' : 'DOCX preview'}</span>
          </header>

          <div className="pdf-word-preview-viewport">
            {previewStatus === 'loading' && (
              <div className="pdf-word-preview-state">
                <Loader2 size={28} className="pdf-word-preview-spinner" />
                <span>Đang tạo bản xem trước...</span>
              </div>
            )}
            {previewStatus === 'error' && (
              <div className="pdf-word-preview-state pdf-word-preview-error">
                <AlertCircle size={28} />
                <strong>Không thể xem trước tài liệu</strong>
                <span>{previewError}</span>
                <small>Bạn vẫn có thể tải file Word bằng nút bên trái.</small>
              </div>
            )}
            <div
              ref={previewRef}
              className={`docx-preview-wrapper pdf-word-preview-content${previewStatus === 'ready' ? ' is-ready' : ''}`}
            />
          </div>
        </section>
      </div>
    </div>
  );
};

export default PdfToWordWorkspace;
