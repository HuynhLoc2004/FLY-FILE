import { useState, useRef } from 'react';
import { Upload, Download, RefreshCw, Loader2, Scissors, Plus, Trash2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const SplitWorkspace = ({ initialFiles, onCancel }) => {
  const [file, setFile] = useState(initialFiles?.[0] || null);
  const [totalPages, setTotalPages] = useState(null);
  const [ranges, setRanges] = useState([{ from: '1', to: '1' }]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const handleFile = async (f) => {
    setFile(f); setStatus('idle'); setError('');
    // Quick page count via ArrayBuffer + PyMuPDF on backend isn't needed —
    // just read PDF trailer for page count client-side
    try {
      const { getDocument } = await import('pdfjs-dist');
      const buf = await f.arrayBuffer();
      const pdf = await getDocument({ data: buf }).promise;
      setTotalPages(pdf.numPages);
      setRanges([{ from: '1', to: String(pdf.numPages) }]);
    } catch {
      setTotalPages(null);
    }
  };

  const addRange = () => setRanges(r => [...r, { from: '', to: '' }]);
  const removeRange = (i) => setRanges(r => r.filter((_, idx) => idx !== i));
  const updateRange = (i, key, val) => setRanges(r => r.map((row, idx) => idx === i ? { ...row, [key]: val } : row));

  const split = async () => {
    if (!file) return;
    setStatus('loading'); setError('');
    try {
      const rangeStr = ranges
        .filter(r => r.from && r.to)
        .map(r => r.from === r.to ? r.from : `${r.from}-${r.to}`)
        .join(',');
      if (!rangeStr) throw new Error('Vui lòng nhập ít nhất một khoảng trang');

      const form = new FormData();
      form.append('file', file);
      form.append('ranges', rangeStr);
      const res = await fetch(`${API_URL}/api/split`, { method: 'POST', body: form });
      if (!res.ok) throw new Error((await res.json()).detail || 'Lỗi cắt PDF');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = file.name.replace(/\.pdf$/i, '') + '_split.zip';
      a.click();
      setStatus('done');
    } catch (e) {
      setError(e.message); setStatus('error');
    }
  };

  return (
    <div style={{ maxWidth: 560, margin: '40px auto', padding: 24 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Scissors size={20} /> Cắt PDF
      </h2>

      {/* File pick */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 20 }}>
        <button className="btn btn-outline" onClick={() => inputRef.current?.click()}>
          <Upload size={14} style={{ marginRight: 6 }} /> Chọn file PDF
        </button>
        <input ref={inputRef} type="file" accept=".pdf" hidden onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
        {file && (
          <span style={{ fontSize: 13, color: '#4a5568' }}>
            {file.name} {totalPages ? `· ${totalPages} trang` : ''}
          </span>
        )}
      </div>

      {/* Range builder */}
      {file && (
        <div style={{ marginBottom: 20 }}>
          <p style={{ fontSize: 13, color: '#718096', marginBottom: 10 }}>
            Mỗi dòng là một file PDF xuất ra. Nhập số trang (ví dụ: 1–3 → file gồm trang 1, 2, 3).
          </p>
          {ranges.map((r, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 13, color: '#718096', minWidth: 50 }}>File {i + 1}:</span>
              <span style={{ fontSize: 13 }}>Trang</span>
              <input
                type="number" min="1" max={totalPages || 9999} value={r.from}
                onChange={e => updateRange(i, 'from', e.target.value)}
                style={{ width: 60, padding: '4px 8px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 13 }}
              />
              <span style={{ fontSize: 13 }}>đến</span>
              <input
                type="number" min="1" max={totalPages || 9999} value={r.to}
                onChange={e => updateRange(i, 'to', e.target.value)}
                style={{ width: 60, padding: '4px 8px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 13 }}
              />
              {totalPages && (
                <span style={{ fontSize: 11, color: '#a0aec0' }}>/ {totalPages}</span>
              )}
              {ranges.length > 1 && (
                <button onClick={() => removeRange(i)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#e53e3e', padding: 4 }}>
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
          <button className="btn btn-outline" style={{ fontSize: 12, padding: '4px 12px', marginTop: 4 }} onClick={addRange}>
            <Plus size={13} style={{ marginRight: 4 }} /> Thêm phần
          </button>
        </div>
      )}

      <div style={{ display: 'flex', gap: 10 }}>
        <button className="btn btn-primary" onClick={split} disabled={!file || status === 'loading'}>
          {status === 'loading'
            ? <><Loader2 size={14} className="spin" /> Đang cắt...</>
            : <><Download size={14} /> Cắt & Tải về (.zip)</>}
        </button>
        <button className="btn btn-outline" onClick={onCancel}><RefreshCw size={14} style={{ marginRight: 6 }} /> Chọn lại</button>
      </div>

      {status === 'done' && <p style={{ color: '#38a169', marginTop: 12, fontSize: 13 }}>✓ Đã tải về file ZIP chứa các PDF!</p>}
      {error && <p style={{ color: '#e53e3e', marginTop: 12, fontSize: 13 }}>{error}</p>}
    </div>
  );
};

export default SplitWorkspace;
