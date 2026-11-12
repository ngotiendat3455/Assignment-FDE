"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, FileSpreadsheet, AlertCircle, X } from "lucide-react";
import { Button } from "../atoms/Button";
import { useI18n } from "@/context/i18n";

export interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  acceptedFileTypes?: string;
  maxSizeMB?: number;
  className?: string;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  onFileSelect,
  acceptedFileTypes = ".csv",
  maxSizeMB = 5,
  className = "",
}) => {
  const { t } = useI18n();
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSelect = (file: File) => {
    setErrorMessage(null);

    if (!file.name.endsWith(".csv")) {
      setErrorMessage(t("dropzone.err_csv_only"));
      return;
    }

    if (file.size > maxSizeMB * 1024 * 1024) {
      setErrorMessage(t("dropzone.err_max_size"));
      return;
    }

    setSelectedFile(file);
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelect(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const clearFile = () => {
    setSelectedFile(null);
    setErrorMessage(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className={`w-full ${className}`}>
      <input
        ref={inputRef}
        type="file"
        accept={acceptedFileTypes}
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            validateAndSelect(e.target.files[0]);
          }
        }}
      />

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !selectedFile && inputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center p-8 rounded-2xl border-2 border-dashed transition-all cursor-pointer ${
          isDragOver
            ? "border-primary bg-primary/5"
            : selectedFile
            ? "border-positive/50 bg-green-50/30"
            : errorMessage
            ? "border-destructive/50 bg-red-50/30"
            : "border-border hover:border-primary/60 bg-white"
        }`}
      >
        {selectedFile ? (
          <div className="flex items-center gap-4 w-full max-w-md p-3 rounded-xl bg-white border border-border shadow-xs">
            <div className="p-2.5 rounded-lg bg-green-100 text-positive">
              <FileSpreadsheet className="w-5 h-5 shrink-0" />
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-foreground truncate">
                {selectedFile.name}
              </p>
              <p className="text-xs text-muted-foreground">
                {(selectedFile.size / 1024).toFixed(1)} KB • {t("dropzone.ready")}
              </p>
            </div>

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                clearFile();
              }}
              className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <UploadCloud className="w-6 h-6" />
            </div>

            <div>
              <p className="text-sm font-medium text-foreground">
                {t("dropzone.drag_title")}{" "}
                <span className="text-primary font-semibold hover:underline">
                  {t("dropzone.browse")}
                </span>
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {t("dropzone.subtitle")}
              </p>
            </div>

            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={(e) => {
                e.stopPropagation();
                inputRef.current?.click();
              }}
            >
              {t("actions.select_file")}
            </Button>
          </div>
        )}

        {errorMessage && (
          <div className="flex items-center gap-1.5 text-xs text-destructive mt-3">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}
      </div>
    </div>
  );
};
