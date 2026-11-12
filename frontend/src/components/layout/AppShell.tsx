"use client";

import React from "react";
import { AppSidebar } from "../organisms/AppSidebar";
import { TopHeader } from "../organisms/TopHeader";
import { BreakpointLayout } from "./BreakpointLayout";
import { GlobalErrorBoundary } from "../organisms/GlobalErrorBoundary";

export interface AppShellProps {
  title: string;
  subtitle?: string;
  reviewQueueCount?: number;
  needsAttentionCount?: number;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  title,
  subtitle,
  reviewQueueCount = 17,
  needsAttentionCount = 3,
  children,
}) => {
  return (
    <BreakpointLayout>
      {() => (
        <div className="flex h-screen w-screen overflow-hidden bg-accent font-sans text-foreground antialiased">
          {/* Left Collapsible Sidebar */}
          <AppSidebar
            reviewQueueCount={reviewQueueCount}
            needsAttentionCount={needsAttentionCount}
          />

          {/* Main Content Viewport */}
          <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
            {/* Top Header */}
            <TopHeader title={title} subtitle={subtitle} />

            {/* Dynamic Canvas with Error Boundary and sleek scrolling */}
            <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
              <GlobalErrorBoundary>
                <div className="max-w-7xl mx-auto w-full">{children}</div>
              </GlobalErrorBoundary>
            </main>
          </div>
        </div>
      )}
    </BreakpointLayout>
  );
};
