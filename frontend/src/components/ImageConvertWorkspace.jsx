import { useState, useRef } from 'react';
import { Upload, RefreshCw, Loader2, ArrowLeftRight } from 'lucide-react';
import { API_URL } from '../config/api';
import ProcessingModal from './ProcessingModal';
import { useProcessingProgress } from '../hooks/useProcessingProgress';

// Used for both Image→PDF and Image format conversion (JPG↔PNG etc.)
const ImageConvertWorkspace = ({ mode = 'convert', onCancel }) => {
  const [files, setFiles] = useState([]);
  const [toFmt, setToFmt] = useState(mode === 'to-pdf' ? 'pdf' : 'png');
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const {
    progress,
    isProcessing,
    stepText,
    startProgress,
    finishProgress,
    resetProgress,
  } = useProcessingProgress({
    25: mode === 'to-pdf' ? 'Đang đọc và chuẩn hóa kích thước các ảnh...' : 'Đang giải mã điểm ảnh...',
    60: mode === 'to-pdf' ? 'Đang căn chỉnh tỷ lệ và ghép vào các trang PDF...' : 'Đang chuyển đổi bảng màu & nén định dạng mới...',
    85: 'Đang hoàn tất và đóng gói file...',
  });

  const accept = mode === 'to-pdf' ? 'image/*' : 'image/*';
  const multi = mode === 'to-pdf';

  const handleFiles = (fList) => { setFiles(Array.from(fList)); setStatus('idle'); setError(''); };

  const convert = async () => {
    if (!files.length) return;
    setStatus('loading'); setError('');
    startProgress(mode === 'to-pdf' ? `Đang đóng gói ${files.length} ảnh sang PDF...` : 'Đang chuyển đổi định dạng ảnh...');
    try {
      if (mode === 'to-pdf') {
        const form = new FormData();
        files.forEach(f => form.append('files', f));
        const res = await fetch(`${API_URL}/api/images-to-pdf`, { method: 'POST', body: form });
        if (!res.ok) throw new Error((await res.json()).detail || 'Lỗi');
        const blob = await res.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'converted.pdf';
        a.click();
      } else {
        for (const f of files) {
          const form = new FormData();
          form.append('file', f);
          form.append('to_format', toFmt);
          const res = await fetch(`${API_URL}/api/convert-image`, { method: 'POST', body: form });
          if (!res.ok) throw new Error((await res.json()).detail || 'Lỗi');
          const blob = await res.blob();
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = f.name.replace(/\.\w+$/, '') + '.' + toFmt;
          a.click();
        }
      }
      finishProgress(() => {
        setStatus('done');
      });
    } catch (e) {
      resetProgress();
      setError(e.message); setStatus('error');
    }
  };

  const title = mode === 'to-pdf' ? 'Hình ảnh → PDF' : 'Chuyển đổi định dạng ảnh';

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', padding: 24 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>{title}</h2>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 20, flexWrap: 'wrap' }}>
        <button className="btn btn-outline" onClick={() => inputRef.current?.click()}>
          <Upload size={14} style={{ marginRight: 6 }} /> Chọn {multi ? 'ảnh' : 'ảnh'}
        </button>
        <input ref={inputRef} type="file" accept={accept} multiple={multi} hidden
          onChange={e => handleFiles(e.target.files)} />
        {files.length > 0 && (
          <span style={{ fontSize: 13, color: '#4a5568' }}>{files.length} file đã chọn</span>
        )}
      </div>

      {mode === 'convert' && (
        <div style={{ marginBottom: 20 }}>
          <label style={{ fontSize: 13 }}>
            Chuyển sang:&nbsp;
            <select value={toFmt} onChange={e => setToFmt(e.target.value)}
              style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #e2e8f0' }}>
              <option value="png">PNG</option>
              <option value="jpg">JPG</option>
              <option value="webp">WEBP</option>
            </select>
          </label>
        </div>
      )}

      {files.length > 0 && (
        <div style={{ marginBottom: 16, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {files.map(f => (
            <div key={f.name} style={{ fontSize: 12, background: '#edf2f7', padding: '4px 10px', borderRadius: 20, color: '#4a5568' }}>
              {f.name}
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10 }}>
        <button className="btn btn-primary" onClick={convert} disabled={!files.length || status === 'loading'}>
          {status === 'loading'
            ? <><Loader2 size={14} className="spin" /> Đang xử lý...</>
            : <><ArrowLeftRight size={14} /> Chuyển đổi & Tải về</>}
        </button>
        <button className="btn btn-outline" onClick={onCancel}><RefreshCw size={14} style={{ marginRight: 6 }} /> Chọn lại</button>
      </div>

      {status === 'done' && <p style={{ color: '#38a169', marginTop: 12, fontSize: 13 }}>✓ Đã tải về thành công!</p>}
      {error && <p style={{ color: '#e53e3e', marginTop: 12, fontSize: 13 }}>{error}</p>}

      <ProcessingModal
        isOpen={isProcessing}
        progress={progress}
        title={mode === 'to-pdf' ? 'Đang đóng gói Hình ảnh sang PDF...' : 'Đang chuyển đổi định dạng ảnh...'}
        fileName={files.length > 0 ? `${files.length} ảnh đã chọn` : ''}
        stepText={stepText}
      />
    </div>
  );
};

export default ImageConvertWorkspace;
