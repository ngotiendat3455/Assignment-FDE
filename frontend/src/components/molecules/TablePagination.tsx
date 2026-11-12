"use client";

import React from "react";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { useI18n } from "@/context/i18n";

export interface TablePaginationProps {
  currentPage: number;
  pageSize: number;
  totalItems: number;
  pageSizeOptions?: number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  className?: string;
}

export const TablePagination: React.FC<TablePaginationProps> = ({
  currentPage,
  pageSize,
  totalItems,
  pageSizeOptions = [10, 25, 50],
  onPageChange,
  onPageSizeChange,
  className = "",
}) => {
  const { t } = useI18n();
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(totalItems, currentPage * pageSize);

  const canGoPrev = currentPage > 1;
  const canGoNext = currentPage < totalPages;

  return (
    <div
      className={`flex flex-col sm:flex-row items-center justify-between gap-4 py-3 px-4 border-t border-border bg-white text-xs text-muted-foreground select-none ${className}`}
    >
      <div className="flex items-center gap-4">
        <span>
          {t("table.showing")}{" "}
          <strong className="text-foreground">{startItem}</strong> {t("table.to")}{" "}
          <strong className="text-foreground">{endItem}</strong> {t("table.of")}{" "}
          <strong className="text-foreground">{totalItems}</strong> {t("table.records")}
        </span>

        <div className="flex items-center gap-2">
          <span>{t("table.rows_per_page")}</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="bg-white border border-border rounded px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
          >
            {pageSizeOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          disabled={!canGoPrev}
          onClick={() => onPageChange(1)}
          className="p-1.5 rounded hover:bg-muted text-muted-foreground disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title={t("table.first_page")}
        >
          <ChevronsLeft className="w-4 h-4" />
        </button>

        <button
          type="button"
          disabled={!canGoPrev}
          onClick={() => onPageChange(currentPage - 1)}
          className="flex items-center gap-1 px-2.5 py-1 rounded border border-border hover:bg-muted text-foreground disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span>{t("table.prev")}</span>
        </button>

        <div className="px-2 py-1 font-mono font-medium text-foreground">
          {currentPage} / {totalPages}
        </div>

        <button
          type="button"
          disabled={!canGoNext}
          onClick={() => onPageChange(currentPage + 1)}
          className="flex items-center gap-1 px-2.5 py-1 rounded border border-border hover:bg-muted text-foreground disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium"
        >
          <span>{t("table.next")}</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          disabled={!canGoNext}
          onClick={() => onPageChange(totalPages)}
          className="p-1.5 rounded hover:bg-muted text-muted-foreground disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title={t("table.last_page")}
        >
          <ChevronsRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
