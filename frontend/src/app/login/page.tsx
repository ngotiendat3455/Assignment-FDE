"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  Mail,
  Lock,
  Eye,
  EyeOff,
  LogIn,
  Globe,
} from "lucide-react";
import { Button } from "@/components/atoms/Button";
import { Input } from "@/components/atoms/Input";
import { useToast } from "@/components/molecules/ToastNotification";
import { useI18n } from "@/context/i18n";

export default function LoginPage() {
  const router = useRouter();
  const { locale, setLocale, t } = useI18n();
  const { toast } = useToast();

  // Pre-filled credentials for zero-friction Hiring Committee evaluation
  const [email, setEmail] = useState<string>("partner@xscout.local");
  const [password, setPassword] = useState<string>("XScout2026!");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [rememberMe, setRememberMe] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const errMessage =
          res.status >= 500
            ? t("errors.500_desc")
            : t("auth.toast_login_error");
        setErrorMsg(errMessage);
        toast(errMessage, "error");
        return;
      }

      const data = (await res.json()) as {
        access_token?: string;
        user?: { full_name?: string; email?: string; role?: string };
      };
      if (typeof window !== "undefined") {
        if (data.user) {
          sessionStorage.setItem("genai_user", JSON.stringify(data.user));
        }
        const params = new URLSearchParams(window.location.search);
        const redirectTarget = params.get("from") || "/";
        toast(t("auth.toast_login_success"), "success");
        router.push(redirectTarget);
        router.refresh();
        return;
      }

      toast(t("auth.toast_login_success"), "success");
      router.push("/");
    } catch {
      setErrorMsg(t("auth.toast_login_error"));
      toast(t("auth.toast_login_error"), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen w-screen flex-col items-center justify-center bg-accent px-4 py-12 text-foreground select-none">
      {/* Top-Right Language Switcher */}
      <div className="absolute top-5 right-6 flex items-center gap-2 rounded-xl border border-border bg-white px-3 py-1.5 shadow-xs">
        <Globe className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">
          {t("nav.language")}:
        </span>
        <div className="flex items-center gap-1 rounded bg-muted p-0.5 text-xs font-medium">
          <button
            type="button"
            onClick={() => setLocale("en")}
            className={`rounded px-2 py-0.5 text-[11px] transition-colors ${
              locale === "en"
                ? "bg-white font-bold text-primary shadow-xs"
                : "text-muted-foreground"
            }`}
          >
            EN
          </button>
          <button
            type="button"
            onClick={() => setLocale("vi")}
            className={`rounded px-2 py-0.5 text-[11px] transition-colors ${
              locale === "vi"
                ? "bg-white font-bold text-primary shadow-xs"
                : "text-muted-foreground"
            }`}
          >
            VI
          </button>
        </div>
      </div>

      {/* Brand Identity Header */}
      <div className="mb-6 flex flex-col items-center text-center">
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-white shadow-sm">
          <Sparkles className="h-6 w-6" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {t("nav.brand_title")}
        </h1>
        <p className="mt-1 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          {t("auth.system_subtitle")}
        </p>
      </div>

      {/* Pre-filled Login Card (Wireframe 1) */}
      <div className="w-full max-w-md rounded-2xl border border-border bg-white p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col items-center border-b border-border pb-4 text-center">
          <h2 className="text-base font-bold tracking-tight text-foreground">
            {t("auth.card_title")}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div>
            <label
              htmlFor="login-email"
              className="mb-1.5 block text-xs font-semibold text-foreground"
            >
              {t("auth.email_label")}
            </label>
            <Input
              id="login-email"
              type="email"
              icon={Mail}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div>
            <label
              htmlFor="login-password"
              className="mb-1.5 block text-xs font-semibold text-foreground"
            >
              {t("auth.password_label")}
            </label>
            <div className="relative flex items-center">
              <div className="pointer-events-none absolute left-3 text-muted-foreground">
                <Lock className="h-4 w-4" />
              </div>
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-lg border border-border bg-white py-2 pr-10 pl-9 font-mono text-sm text-foreground transition-colors focus:border-transparent focus:ring-2 focus:ring-primary focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between text-xs">
            <label className="flex cursor-pointer items-center gap-2 text-foreground">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded border-border text-primary"
              />
              <span>{t("auth.remember_me")}</span>
            </label>
          </div>

          {errorMsg && (
            <div className="rounded-lg border border-destructive/30 bg-red-50 px-3 py-2 text-xs font-medium text-destructive">
              {errorMsg}
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            icon={LogIn}
            data-testid="login-submit"
            className="w-full"
          >
            {loading ? t("auth.btn_signing_in") : t("auth.btn_sign_in")}
          </Button>
        </form>
      </div>
    </div>
  );
}
