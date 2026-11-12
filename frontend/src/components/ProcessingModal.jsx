import { Loader2, CheckCircle2 } from 'lucide-react';

const ProcessingModal = ({
  isOpen,
  progress = 0,
  title = 'Đang xử lý tài liệu...',
  fileName = '',
  stepText = 'Vui lòng đợi trong giây lát...',
}) => {
  if (!isOpen) return null;

  const numericProgress = Math.min(100, Math.max(0, Math.round(progress)));
  const isDone = numericProgress >= 100;
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (numericProgress / 100) * circumference;

  return (
    <div className="processing-modal-overlay" role="dialog" aria-modal="true">
      <div className="processing-modal-card">
        {/* Circular Progress Ring with Center % */}
        <div className="processing-ring-container">
          <svg className="processing-ring-svg" width="116" height="116" viewBox="0 0 116 116">
            <circle
              className="processing-ring-bg"
              cx="58"
              cy="58"
              r={radius}
              strokeWidth="7"
            />
            <circle
              className="processing-ring-fill"
              cx="58"
              cy="58"
              r={radius}
              strokeWidth="7"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              transform="rotate(-90 58 58)"
            />
          </svg>
          <div className="processing-ring-center">
            {isDone ? (
              <CheckCircle2 size={40} className="processing-done-icon" />
            ) : (
              <div className="processing-number-wrap">
                <span className="processing-number">{numericProgress}</span>
                <span className="processing-percent-sign">%</span>
              </div>
            )}
          </div>
        </div>

        {/* Action Title */}
        <h3 className="processing-title">
          {isDone ? 'Xử lý hoàn tất!' : title}
        </h3>

        {/* File Name */}
        {fileName && (
          <p className="processing-filename" title={fileName}>
            {fileName}
          </p>
        )}

        {/* Linear Progress Bar */}
        <div className="processing-bar-track">
          <div
            className="processing-bar-fill"
            style={{ width: `${numericProgress}%` }}
          />
        </div>

        {/* Progress Step Subtext */}
        <div className="processing-step-row">
          {!isDone && <Loader2 size={14} className="spin processing-spinner" />}
          <span className="processing-step-text">
            {isDone ? 'Đang chuẩn bị hiển thị kết quả...' : stepText}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ProcessingModal;
