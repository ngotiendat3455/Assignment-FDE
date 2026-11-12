"use client";

import React from "react";
import { Error401View } from "@/components/organisms/ErrorViews";

export default function Unauthorized401Page() {
  return (
    <div className="flex min-h-screen w-screen items-center justify-center bg-accent p-6">
      <div className="w-full max-w-lg rounded-2xl border border-border bg-white shadow-xs">
        <Error401View />
      </div>
    </div>
  );
}

