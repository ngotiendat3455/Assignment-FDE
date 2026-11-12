"use client";

import React from "react";
import { AppProviders } from "@/components/providers/AppProviders";
import { Error500View } from "@/components/organisms/ErrorViews";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="bg-accent text-foreground antialiased">
        <AppProviders>
          <div className="flex min-h-screen w-screen items-center justify-center p-6">
            <div className="w-full max-w-lg rounded-2xl border border-border bg-white shadow-xs">
              <Error500View errorMessage={error.message} onRetry={reset} />
            </div>
          </div>
        </AppProviders>
      </body>
    </html>
  );
}

