import { useState, useRef, useCallback } from 'react';

/**
 * Custom hook to simulate smooth progress % updates while awaiting asynchronous API calls.
 */
export const useProcessingProgress = (customSteps = {}) => {
  const [progress, setProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [stepText, setStepText] = useState('');
  const intervalRef = useRef(null);

  const startProgress = useCallback((initialText = 'Đang bắt đầu xử lý...') => {
    setIsProcessing(true);
    setProgress(12);
    setStepText(initialText);

    if (intervalRef.current) clearInterval(intervalRef.current);

    intervalRef.current = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return prev;
        const remaining = 90 - prev;
        const increment = Math.max(0.6, remaining * 0.07);
        const next = Math.min(90, Math.round((prev + increment) * 10) / 10);

        if (next >= 70) {
          setStepText(customSteps[70] || 'Đang hoàn tất và đóng gói tài liệu...');
        } else if (next >= 40) {
          setStepText(customSteps[40] || 'Đang xử lý cấu trúc và nội dung trang...');
        } else if (next >= 20) {
          setStepText(customSteps[20] || 'Đang phân tích dữ liệu đầu vào...');
        }
        return next;
      });
    }, 180);
  }, [customSteps]);

  const finishProgress = useCallback((onFinish) => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    setProgress(100);
    setStepText('Hoàn thành 100%!');

    setTimeout(() => {
      setIsProcessing(false);
      setProgress(0);
      setStepText('');
      if (typeof onFinish === 'function') onFinish();
    }, 400);
  }, []);

  const resetProgress = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    setIsProcessing(false);
    setProgress(0);
    setStepText('');
  }, []);

  return {
    progress,
    isProcessing,
    stepText,
    startProgress,
    finishProgress,
    resetProgress,
  };
};

