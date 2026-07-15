import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Use Vite's new URL() so the worker is bundled from node_modules — no CDN needed
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

const PdfRenderer = ({ file, pageNum = 1, scale = 1.0, onDocumentLoad, rotation = null, width, lazy = true }) => {
  const wrapperRef = useRef(null);
  const [shouldRender, setShouldRender] = useState(!lazy);
  const placeholderSize = useMemo(() => ({
    width: width || 120,
    height: Math.round((width || 120) * 1.41),
  }), [width]);

  useEffect(() => {
    if (!lazy) {
      return undefined;
    }

    const node = wrapperRef.current;
    if (!node) return undefined;

    const observer = new IntersectionObserver(([entry]) => {
      setShouldRender(entry.isIntersecting);
    }, {
      root: null,
      rootMargin: '650px 0px',
      threshold: 0.01,
    });

    observer.observe(node);
    return () => observer.disconnect();
  }, [lazy]);

  const onLoadSuccess = ({ numPages }) => {
    if (onDocumentLoad) onDocumentLoad(numPages);
  };

  const onLoadError = (err) => {
    console.error('react-pdf load error:', err);
  };

  const placeholder = (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      width: placeholderSize.width, height: placeholderSize.height,
      background: '#f1f5f9', borderRadius: 4, color: '#64748b',
      fontSize: 12, fontWeight: 800,
    }}>
      Trang {pageNum}
    </div>
  );

  return (
    <div ref={wrapperRef} style={{ width: placeholderSize.width, minHeight: placeholderSize.height }}>
      {!shouldRender ? placeholder : (
    <Document
      file={file}
      onLoadSuccess={onLoadSuccess}
      onLoadError={onLoadError}
      loading={
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: placeholderSize.width, height: placeholderSize.height,
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
          width: placeholderSize.width, height: placeholderSize.height,
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
        {...(rotation == null ? {} : { rotate: rotation })}
        width={width}
        devicePixelRatio={1}
        renderAnnotationLayer={false}
        renderTextLayer={false}
      />
    </Document>
      )}
    </div>
  );
};

const PdfPageThumbnailComponent = ({ pageNum = 1, rotation = null, width = 120 }) => {
  const wrapperRef = useRef(null);
  const [shouldRender, setShouldRender] = useState(false);
  const height = Math.round(width * 1.41);

  useEffect(() => {
    const node = wrapperRef.current;
    if (!node) return undefined;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setShouldRender(true);
        observer.disconnect();
      }
    }, {
      rootMargin: '220px 0px',
      threshold: 0.01,
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={wrapperRef} style={{ width, height }}>
      {shouldRender ? (
        <Page
          pageNumber={pageNum}
          {...(rotation == null ? {} : { rotate: rotation })}
          width={width}
          devicePixelRatio={1}
          renderAnnotationLayer={false}
          renderTextLayer={false}
          loading={<div className="split-page-skeleton" style={{ width, height }}>Trang {pageNum}</div>}
          error={<div className="split-page-skeleton split-page-render-error" style={{ width, height }}>Lỗi trang {pageNum}</div>}
        />
      ) : (
        <div className="split-page-skeleton" style={{ width, height }}>Trang {pageNum}</div>
      )}
    </div>
  );
};

export const PdfPageThumbnail = memo(PdfPageThumbnailComponent);
export default memo(PdfRenderer);
