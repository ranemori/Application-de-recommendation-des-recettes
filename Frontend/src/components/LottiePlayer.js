import React, { useEffect, useRef } from 'react';
import lottie from 'lottie-web';

export default function LottiePlayer({ animationData, loop = true, autoplay = true, className, style }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const anim = lottie.loadAnimation({
      container: containerRef.current,
      renderer: 'svg',
      loop,
      autoplay,
      animationData,
    });
    return () => anim.destroy();
  }, [animationData, loop, autoplay]);

  return <div ref={containerRef} className={className} style={style} />;
}