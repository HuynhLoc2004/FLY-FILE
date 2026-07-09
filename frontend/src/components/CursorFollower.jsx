import { useEffect, useRef } from 'react';

const interactiveSelector = [
  'a',
  'button',
  'input',
  'select',
  'textarea',
  '[role="button"]',
  '.tool-card',
  '.file-card',
  '.page-card',
  '.mobile-nav-item',
  '.header-nav-item',
].join(',');

const CursorFollower = () => {
  const ringRef = useRef(null);
  const dotRef = useRef(null);
  const frameRef = useRef(0);
  const isRunningRef = useRef(false);
  const targetRef = useRef({ x: 0, y: 0 });
  const currentRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!canHover || reduceMotion) return undefined;

    const ring = ringRef.current;
    const dot = dotRef.current;
    if (!ring || !dot) return undefined;

    const moveCursor = () => {
      const current = currentRef.current;
      const target = targetRef.current;

      const deltaX = target.x - current.x;
      const deltaY = target.y - current.y;

      current.x += deltaX * 0.22;
      current.y += deltaY * 0.22;

      ring.style.transform = `translate3d(${current.x}px, ${current.y}px, 0) translate(-50%, -50%)`;
      dot.style.transform = `translate3d(${target.x}px, ${target.y}px, 0) translate(-50%, -50%)`;

      if (Math.abs(deltaX) < 0.2 && Math.abs(deltaY) < 0.2) {
        isRunningRef.current = false;
        frameRef.current = 0;
        return;
      }

      frameRef.current = window.requestAnimationFrame(moveCursor);
    };

    const handlePointerMove = (event) => {
      targetRef.current.x = event.clientX;
      targetRef.current.y = event.clientY;
      ring.classList.add('visible');
      dot.classList.add('visible');

      if (!isRunningRef.current) {
        isRunningRef.current = true;
        frameRef.current = window.requestAnimationFrame(moveCursor);
      }
    };

    const handlePointerOver = (event) => {
      if (event.target.closest(interactiveSelector)) {
        ring.classList.add('hovering');
      }
    };

    const handlePointerOut = (event) => {
      if (event.target.closest(interactiveSelector)) {
        ring.classList.remove('hovering');
      }
    };

    const handlePointerLeave = () => {
      ring.classList.remove('visible', 'hovering');
      dot.classList.remove('visible');
    };

    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    window.addEventListener('pointerover', handlePointerOver, { passive: true });
    window.addEventListener('pointerout', handlePointerOut, { passive: true });
    document.documentElement.addEventListener('mouseleave', handlePointerLeave);

    return () => {
      if (frameRef.current) {
        window.cancelAnimationFrame(frameRef.current);
      }
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerover', handlePointerOver);
      window.removeEventListener('pointerout', handlePointerOut);
      document.documentElement.removeEventListener('mouseleave', handlePointerLeave);
    };
  }, []);

  return (
    <>
      <div className="cursor-follower-ring" ref={ringRef} aria-hidden="true" />
      <div className="cursor-follower-dot" ref={dotRef} aria-hidden="true" />
    </>
  );
};

export default CursorFollower;
