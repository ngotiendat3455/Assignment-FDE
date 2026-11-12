"use client";

import React from "react";
import { Inbox } from "lucide-react";
import { TablePagination } from "../molecules/TablePagination";
import { useI18n } from "@/context/i18n";

export const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className = "", ...props }, ref) => (
    <div className="w-full overflow-x-auto rounded-xl border border-border bg-white shadow-xs">
      <table ref={ref} className={`w-full text-left border-collapse text-sm ${className}`} {...props} />
    </div>
  )
);
Table.displayName = "Table";

export const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className = "", ...props }, ref) => (
    <thead ref={ref} className={`bg-muted/80 border-b border-border text-xs uppercase tracking-wider text-muted-foreground select-none ${className}`} {...props} />
  )
);
TableHeader.displayName = "TableHeader";

export const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
  ({ className = "", ...props }, ref) => (
    <th ref={ref} className={`py-3 px-4 font-semibold text-dark-secondary ${className}`} {...props} />
  )
);
TableHead.displayName = "TableHead";

export const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className = "", ...props }, ref) => (
    <tbody ref={ref} className={`divide-y divide-border ${className}`} {...props} />
  )
);
TableBody.displayName = "TableBody";

export const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className = "", ...props }, ref) => (
    <tr ref={ref} className={`hover:bg-muted/40 transition-colors ${className}`} {...props} />
  )
);
TableRow.displayName = "TableRow";

export const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className = "", ...props }, ref) => (
    <td ref={ref} className={`py-3.5 px-4 text-foreground align-middle ${className}`} {...props} />
  )
);
TableCell.displayName = "TableCell";

export const TableEmptyState: React.FC<{
  title?: string;
  description?: string;
  colSpan?: number;
}> = ({
  title,
  description,
  colSpan = 6,
}) => {
  const { t } = useI18n();
  const displayTitle = title || t("table.empty_title");
  const displayDesc = description || t("table.empty_desc");

  return (
    <tr>
      <td colSpan={colSpan} className="py-12 px-4 text-center">
        <div className="flex flex-col items-center justify-center space-y-2">
          <div className="p-3 rounded-full bg-muted text-muted-foreground">
            <Inbox className="w-6 h-6" />
          </div>
          <p className="text-sm font-semibold text-foreground">{displayTitle}</p>
          <p className="text-xs text-muted-foreground max-w-sm">{displayDesc}</p>
        </div>
      </td>
    </tr>
  );
};

export const TableLoadingSkeleton: React.FC<{
  rows?: number;
  colSpan?: number;
}> = ({ rows = 4, colSpan = 6 }) => (
  <>
    {Array.from({ length: rows }).map((_, idx) => (
      <tr key={idx} className="animate-pulse">
        <td colSpan={colSpan} className="py-4 px-4">
          <div className="h-4 bg-muted rounded w-full"></div>
        </td>
      </tr>
    ))}
  </>
);

export { TablePagination };
