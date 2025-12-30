"use client";
import React, { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { twMerge } from "tailwind-merge";

const cn = (...classNames: (string | undefined)[]) => {
  return twMerge(classNames);
};

export const BackgroundBeams = ({
  className,
}: {
  className?: string;
}) => {
  const [paths, setPaths] = useState<string[]>([]);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const generatePaths = () => {
      if (!containerRef.current) return;
      const { clientWidth, clientHeight } = containerRef.current;
      const newPaths: string[] = [];
      const numberOfBeams = 50;
      for (let i = 0; i < numberOfBeams; i++) {
        const startX = Math.random() * clientWidth;
        const startY = Math.random() * clientHeight;
        const endX = Math.random() * clientWidth;
        const endY = Math.random() * clientHeight;
        const controlX1 = (startX + endX) / 2 + Math.random() * 200 - 100;
        const controlY1 = (startY + endY) / 2 + Math.random() * 200 - 100;
        const d = `M${startX},${startY} C${controlX1},${controlY1} ${controlX1},${controlY1} ${endX},${endY}`;
        newPaths.push(d);
      }
      setPaths(newPaths);
    };

    generatePaths();
    window.addEventListener("resize", generatePaths);

    return () => {
      window.removeEventListener("resize", generatePaths);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={cn(
        "h-full w-full absolute inset-0 z-0 overflow-hidden",
        className
      )}
    >
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        preserveAspectRatio="none"
      >
        {paths.map((d, index) => (
          <motion.path
            key={index}
            d={d}
            strokeWidth="0.5"
            stroke="rgba(255, 255, 255, 0.1)"
            initial={{ pathLength: 0 }}
            animate={{
              pathLength: 1,
              transition: {
                duration: Math.random() * 10 + 5,
                ease: "easeInOut",
                repeat: Infinity,
                repeatType: "reverse",
              },
            }}
          />
        ))}
      </svg>
    </div>
  );
};
