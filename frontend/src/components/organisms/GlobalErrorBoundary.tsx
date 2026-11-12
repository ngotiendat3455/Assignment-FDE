"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertCircle, RotateCw } from "lucide-react";
import { Button } from "../atoms/Button";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackDescription?: string;
  reloadButtonText?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class GlobalErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("GlobalErrorBoundary intercepted runtime crash:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[40vh] p-8 text-center bg-white rounded-2xl border border-border m-6 shadow-xs animate-in fade-in">
          <div className="w-12 h-12 rounded-full bg-red-100 text-destructive flex items-center justify-center mb-4">
            <AlertCircle className="w-6 h-6" />
          </div>

          <h3 className="text-base font-bold text-foreground mb-1">
            {this.props.fallbackTitle || "Component Rendering Error"}
          </h3>

          <p className="text-xs text-muted-foreground max-w-md mb-4">
            {this.props.fallbackDescription ||
              this.state.error?.message ||
              "An unexpected error occurred while rendering this component."}
          </p>

          <Button
            variant="outline"
            size="sm"
            icon={RotateCw}
            onClick={() => this.setState({ hasError: false })}
          >
            {this.props.reloadButtonText || "Reload Component"}
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
