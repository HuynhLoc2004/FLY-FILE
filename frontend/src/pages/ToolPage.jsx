import { lazy, Suspense, useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  UploadCloud, ChevronDown,
  FolderArchive, Minimize2, Scissors, FileText, FileCheck2,
  FileImage, Image, RefreshCw, Languages,
  Zap, ShieldCheck, Sparkles
} from 'lucide-react';

const MergeWorkspace = lazy(() => import('../components/MergeWorkspace'));
const PdfToWordWorkspace = lazy(() => import('../components/PdfToWordWorkspace'));
const PdfToImageWorkspace = lazy(() => import('../components/PdfToImageWorkspace'));
const WordToPdfWorkspace = lazy(() => import('../components/WordToPdfWorkspace'));
const ImageConvertWorkspace = lazy(() => import('../components/ImageConvertWorkspace'));
const SplitWorkspace = lazy(() => import('../components/SplitWorkspace'));
const TranslateWorkspace = lazy(() => import('../components/TranslateWorkspace'));
const CompressWorkspace = lazy(() => import('../components/CompressWorkspace'));

const ToolLoading = () => (
  <div className="loading-mini-card tool-loading-card">
    Đang mở công cụ...
  </div>
);

const ToolPage = () => {
  const { toolId } = useParams();
  const [isDragActive, setIsDragActive] = useState(false);
  const [files, setFiles] = useState([]);

  const toolConfig = {
    'merge': {
      title: 'Gộp PDF',
      desc: 'Ghép nối nhiều tài liệu PDF thành một file duy nhất theo thứ tự mong muốn.',
      icon: <FolderArchive size={28} />,
      color: '#3b82f6',
      formats: ['PDF'],
      accept: '.pdf',
      multiple: true,
      hint: 'Kéo thả các file PDF của bạn vào đây',
    },
    'compress': {
      title: 'Nén PDF',
      desc: 'Giảm dung lượng file PDF tối đa mà vẫn giữ độ nét chuẩn in ấn của chữ và ảnh.',
      icon: <Minimize2 size={28} />,
      color: '#10b981',
      formats: ['PDF'],
      accept: '.pdf',
      multiple: false,
      hint: 'Kéo thả file PDF cần nén vào đây',
    },
    'split': {
      title: 'Cắt & Tách PDF',
      desc: 'Trích xuất, tách trang hoặc loại bỏ các trang không cần thiết trong file PDF.',
      icon: <Scissors size={28} />,
      color: '#f59e0b',
      formats: ['PDF'],
      accept: '.pdf',
      multiple: false,
      hint: 'Kéo thả file PDF cần cắt vào đây',
    },
    'pdf-to-word': {
      title: 'PDF sang Word',
      desc: 'Chuyển đổi file PDF sang định dạng Word (.docx) để dễ dàng biên tập và chỉnh sửa.',
      icon: <FileText size={28} />,
      color: '#6366f1',
      formats: ['PDF'],
      accept: '.pdf',
      multiple: false,
      hint: 'Kéo thả file PDF cần chuyển sang Word vào đây',
    },
    'word-to-pdf': {
      title: 'Word sang PDF',
      desc: 'Đóng gói tài liệu Word (.docx, .doc) thành PDF chuẩn, bảo toàn trọn vẹn font chữ và bảng biểu.',
      icon: <FileCheck2 size={28} />,
      color: '#059669',
      formats: ['DOCX', 'DOC'],
      accept: '.doc,.docx',
      multiple: false,
      hint: 'Kéo thả file Word (.docx, .doc) vào đây',
    },
    'pdf-to-image': {
      title: 'PDF sang Hình ảnh',
      desc: 'Chuyển đổi từng trang tài liệu PDF thành hình ảnh JPG độ phân giải cao.',
      icon: <FileImage size={28} />,
      color: '#ec4899',
      formats: ['PDF'],
      accept: '.pdf',
      multiple: false,
      hint: 'Kéo thả file PDF cần xuất ảnh vào đây',
    },
    'image-to-pdf': {
      title: 'Hình ảnh sang PDF',
      desc: 'Tập hợp các hình ảnh JPG, PNG, WEBP thành một file PDF duy nhất ngăn nắp.',
      icon: <Image size={28} />,
      color: '#8b5cf6',
      formats: ['JPG', 'PNG', 'WEBP'],
      accept: '.jpg,.jpeg,.png,.webp',
      multiple: true,
      hint: 'Kéo thả các file hình ảnh vào đây',
    },
    'convert-image': {
      title: 'Chuyển đổi ảnh',
      desc: 'Chuyển đổi định dạng hình ảnh nhanh chóng qua lại giữa JPG, PNG và WEBP.',
      icon: <RefreshCw size={28} />,
      color: '#06b6d4',
      formats: ['JPG', 'PNG', 'WEBP'],
      accept: '.jpg,.jpeg,.png,.webp',
      multiple: false,
      hint: 'Kéo thả hình ảnh cần chuyển đổi vào đây',
    },
    'translate': {
      title: 'Dịch thuật tài liệu PDF',
      desc: 'Dịch song ngữ tài liệu PDF giữ nguyên bố cục bằng trí tuệ nhân tạo Gemini AI.',
      icon: <Languages size={28} />,
      color: '#38bdf8',
      formats: ['PDF', 'DOCX'],
      accept: '.pdf,.docx',
      multiple: false,
      hint: 'Kéo thả file tài liệu cần dịch vào đây',
    },
  };

  const config = toolConfig[toolId] || {
    title: 'Công cụ tài liệu',
    desc: 'Xử lý và chuyển đổi định dạng tài liệu nhanh chóng, an toàn.',
    icon: <UploadCloud size={28} />,
    color: '#38bdf8',
    formats: ['PDF'],
    accept: '.pdf',
    multiple: false,
    hint: 'Kéo thả file của bạn vào đây',
  };

  // Global drag listener for initial state
  useEffect(() => {
    if (files.length > 0) return; // Managed by workspace if files exist

    const handleDragOver = (e) => {
      e.preventDefault();
      setIsDragActive(true);
    };

    const handleDragLeave = (e) => {
      e.preventDefault();
      if (e.clientX === 0 && e.clientY === 0) {
        setIsDragActive(false);
      }
    };

    const handleDrop = (e) => {
      e.preventDefault();
      setIsDragActive(false);
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        setFiles(Array.from(e.dataTransfer.files));
      }
    };

    window.addEventListener('dragover', handleDragOver);
    window.addEventListener('dragleave', handleDragLeave);
    window.addEventListener('drop', handleDrop);

    return () => {
      window.removeEventListener('dragover', handleDragOver);
      window.removeEventListener('dragleave', handleDragLeave);
      window.removeEventListener('drop', handleDrop);
    };
  }, [files.length]);

  const onFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
    }
  };

  const workspaceClassName = files.length > 0 && toolId === 'merge'
    ? 'merge-workspace-wrapper'
    : `tool-workspace${files.length > 0 && toolId === 'split' ? ' split-tool-workspace' : ''}`;

  return (
    <div className={workspaceClassName}>
      <Suspense fallback={<ToolLoading />}>
        {/* Tools that manage their own full-page UI */}
        {toolId === 'translate' ? (
          <TranslateWorkspace />
        ) : toolId === 'pdf-to-word' ? (
          <PdfToWordWorkspace />
        ) : files.length === 0 ? (
          <div className="tool-page-container">
            <div className="tool-page-header">
              <div
                className="tool-page-badge"
                style={{
                  backgroundColor: `${config.color || '#38bdf8'}1e`,
                  color: config.color || '#38bdf8',
                  boxShadow: `0 8px 24px ${config.color || '#38bdf8'}26`,
                }}
              >
                {config.icon}
              </div>
              <h1 className="tool-page-title">{config.title}</h1>
              <p className="tool-page-desc">{config.desc}</p>
            </div>

            <div
              className={`dropzone ${isDragActive ? 'active' : ''}`}
              onClick={() => document.getElementById('file-upload').click()}
            >
              <UploadCloud className="dropzone-icon" size={54} />
              <button className="dropzone-btn" type="button">
                Chọn file <ChevronDown size={18} style={{ marginLeft: '6px' }} />
              </button>
              <input
                type="file"
                id="file-upload"
                accept={config.accept}
                multiple={Boolean(config.multiple)}
                style={{ display: 'none' }}
                onChange={onFileChange}
              />
              <div className="dropzone-hint">{config.hint}</div>
              <div className="dropzone-formats">
                <span className="dropzone-formats-label">Định dạng hỗ trợ:</span>
                {config.formats.map((f) => (
                  <span
                    key={f}
                    className="format-badge ml-1"
                    style={{
                      backgroundColor: `${config.color || '#38bdf8'}1e`,
                      color: config.color || '#38bdf8',
                    }}
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>

            <div className="tool-page-trust-row">
              <div className="trust-item">
                <Zap size={15} />
                <span>Xử lý siêu tốc</span>
              </div>
              <div className="trust-item">
                <ShieldCheck size={15} />
                <span>Bảo mật an toàn 100%</span>
              </div>
              <div className="trust-item">
                <Sparkles size={15} />
                <span>Bảo toàn định dạng</span>
              </div>
            </div>
          </div>
        ) : toolId === 'merge' ? (
          <MergeWorkspace initialFiles={files} onCancel={() => setFiles([])} />
        ) : toolId === 'split' ? (
          <SplitWorkspace initialFiles={files} onCancel={() => setFiles([])} />
        ) : toolId === 'compress' ? (
          <CompressWorkspace initialFiles={files} onCancel={() => setFiles([])} />
        ) : toolId === 'word-to-pdf' ? (
          <WordToPdfWorkspace initialFiles={files} onCancel={() => setFiles([])} />
        ) : toolId === 'pdf-to-image' ? (
          <PdfToImageWorkspace initialFiles={files} onCancel={() => setFiles([])} />
        ) : toolId === 'image-to-pdf' ? (
          <ImageConvertWorkspace mode="to-pdf" onCancel={() => setFiles([])} />
        ) : toolId === 'convert-image' ? (
          <ImageConvertWorkspace mode="convert" onCancel={() => setFiles([])} />
        ) : (
          <div style={{ textAlign: 'center', marginTop: '50px' }}>
            <h3>Đã chọn {files.length} file</h3>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {files.map((f) => (
                <li key={f.name}>
                  {f.name} ({(f.size / 1024 / 1024).toFixed(2)} MB)
                </li>
              ))}
            </ul>
            <div style={{ marginTop: '20px', display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button className="btn btn-primary">Xử lý ngay ({config.title})</button>
              <button className="btn btn-outline" onClick={() => setFiles([])}>Hủy</button>
            </div>
          </div>
        )}
      </Suspense>
    </div>
  );
};

export default ToolPage;
