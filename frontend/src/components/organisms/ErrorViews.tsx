"use client";

import React from "react";
import { Lock, ShieldAlert, AlertTriangle, RotateCw, LogIn, ArrowLeft } from "lucide-react";
import { Button } from "../atoms/Button";
import { useI18n } from "@/context/i18n";

export const Error401View: React.FC<{ onLoginRedirect?: () => void }> = ({
  onLoginRedirect,
}) => {
  const { t } = useI18n();

  const handleLogin = () => {
    if (onLoginRedirect) onLoginRedirect();
    else window.location.href = "/login";
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center animate-in fade-in">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-6 shadow-xs">
        <Lock className="w-8 h-8" />
      </div>

      <h2 className="text-xl font-bold text-foreground tracking-tight mb-2">
        {t("errors.401_title")}
      </h2>

      <p className="text-sm text-muted-foreground max-w-md leading-relaxed mb-6">
        {t("errors.401_desc")}
      </p>

      <Button variant="primary" icon={LogIn} onClick={handleLogin}>
        {t("errors.401_action")}
      </Button>
    </div>
  );
};

export const Error403View: React.FC<{ onBack?: () => void }> = ({ onBack }) => {
  const { t } = useI18n();

  const handleBack = () => {
    if (onBack) onBack();
    else window.location.href = "/workspace";
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center animate-in fade-in">
      <div className="w-16 h-16 rounded-2xl bg-amber-100 text-amber-700 flex items-center justify-center mb-6 shadow-xs">
        <ShieldAlert className="w-8 h-8" />
      </div>

      <h2 className="text-xl font-bold text-foreground tracking-tight mb-2">
        {t("errors.403_title")}
      </h2>

      <p className="text-sm text-muted-foreground max-w-md leading-relaxed mb-6">
        {t("errors.403_desc")}
      </p>

      <Button variant="outline" icon={ArrowLeft} onClick={handleBack}>
        {t("errors.403_action")}
      </Button>
    </div>
  );
};

export const Error500View: React.FC<{
  errorMessage?: string;
  onRetry?: () => void;
}> = ({
  errorMessage = "Failed to fetch /api/candidates - Status: 500 Connection Refused",
  onRetry,
}) => {
  const { t } = useI18n();

  const handleRetry = () => {
    if (onRetry) onRetry();
    else window.location.reload();
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center animate-in fade-in">
      <div className="w-16 h-16 rounded-2xl bg-red-100 text-destructive flex items-center justify-center mb-6 shadow-xs animate-pulse">
        <AlertTriangle className="w-8 h-8" />
      </div>

      <h2 className="text-xl font-bold text-foreground tracking-tight mb-2">
        {t("errors.500_title")}
      </h2>

      <p className="text-sm text-muted-foreground max-w-md leading-relaxed mb-4">
        {t("errors.500_desc")}
      </p>

      {errorMessage && (
        <div className="p-3 rounded-lg bg-muted border border-border text-xs font-mono text-muted-foreground max-w-lg mb-6 break-all">
          {errorMessage}
        </div>
      )}

      <Button variant="primary" icon={RotateCw} onClick={handleRetry}>
        {t("errors.500_action")}
      </Button>
    </div>
  );
};

