"use client";

import React, { useState, useEffect } from "react";

export type BreakpointMode = "mobile" | "tablet" | "desktop" | "wide";

export interface BreakpointLayoutProps {
  children: (props: { mode: BreakpointMode; width: number }) => React.ReactNode;
}

export const BreakpointLayout: React.FC<BreakpointLayoutProps> = ({ children }) => {
  const [width, setWidth] = useState<number>(typeof window !== "undefined" ? window.innerWidth : 1280);

  useEffect(() => {
    const handleResize = () => setWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  let mode: BreakpointMode = "desktop";
  if (width < 768) {
    mode = "mobile";
  } else if (width < 1024) {
    mode = "tablet";
  } else if (width >= 1536) {
    mode = "wide";
  }

  return <>{children({ mode, width })}</>;
};

