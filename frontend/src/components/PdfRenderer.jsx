import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Use Vite's new URL() so the worker is bundled from node_modules — no CDN needed
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

const PdfRenderer = ({ file, pageNum = 1, scale = 1.0, onDocumentLoad, rotation = 0, width }) => {
  const onLoadSuccess = ({ numPages }) => {
    if (onDocumentLoad) onDocumentLoad(numPages);
  };

  const onLoadError = (err) => {
    console.error('react-pdf load error:', err);
  };

  return (
    <Document
      file={file}
      onLoadSuccess={onLoadSuccess}
      onLoadError={onLoadError}
      loading={
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: width || 120, height: Math.round((width || 120) * 1.41),
          background: '#f1f5f9', borderRadius: 4
        }}>
          <div className="pdf-loading-dots">
            <span /><span /><span />
          </div>
        </div>
      }
      error={
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', color: '#e53e3e', fontSize: 12, textAlign: 'center',
          width: width || 120, height: Math.round((width || 120) * 1.41),
          gap: 6
        }}>
          <span style={{ fontSize: 22 }}>⚠️</span>
          Không thể tải PDF
        </div>
      }
    >
      <Page
        pageNumber={pageNum}
        scale={scale}
        rotate={rotation}
        width={width}
        renderAnnotationLayer={false}
        renderTextLayer={false}
      />
    </Document>
  );
};

export default PdfRenderer;
