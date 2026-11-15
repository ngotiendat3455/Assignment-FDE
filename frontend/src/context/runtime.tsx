"use client";

import React, { createContext, useContext } from "react";

export interface RuntimeConfig {
  runtimeProfile: "OFFLINE_MOCK" | "LIVE_PRODUCTION" | "HYBRID_AUTO" | string;
  dispatchMode: "SANDBOX" | "LIVE_X" | string;
}

const DEFAULT_RUNTIME: RuntimeConfig = {
  runtimeProfile: "OFFLINE_MOCK",
  dispatchMode: "SANDBOX",
};

const RuntimeContext = createContext<RuntimeConfig>(DEFAULT_RUNTIME);

export function RuntimeProvider({
  initialRuntime,
  children,
}: {
  initialRuntime: RuntimeConfig;
  children: React.ReactNode;
}) {
  return (
    <RuntimeContext.Provider value={initialRuntime}>
      {children}
    </RuntimeContext.Provider>
  );
}

export function useRuntime(): RuntimeConfig {
  return useContext(RuntimeContext);
}

