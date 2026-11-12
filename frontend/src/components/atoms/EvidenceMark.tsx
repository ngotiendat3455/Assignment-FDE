"use client";

import React from "react";

export interface EvidenceMarkProps {
  text: string;
  snippet?: string | null;
  className?: string;
}

export const EvidenceMark: React.FC<EvidenceMarkProps> = ({
  text,
  snippet,
  className = "",
}) => {
  if (!snippet || !snippet.trim() || !text) {
    return <span className={className}>{text}</span>;
  }

  const cleanSnippet = snippet.trim();
  const lowerText = text.toLowerCase();
  const lowerSnippet = cleanSnippet.toLowerCase();

  const matchIndex = lowerText.indexOf(lowerSnippet);

  if (matchIndex === -1) {
    // If not exact substring, render text normally
    return <span className={className}>{text}</span>;
  }

  const before = text.slice(0, matchIndex);
  const matched = text.slice(matchIndex, matchIndex + cleanSnippet.length);
  const after = text.slice(matchIndex + cleanSnippet.length);

  return (
    <span className={className}>
      {before}
      <mark className="bg-amber-100 text-amber-950 font-medium px-1 py-0.5 rounded-xs border-b-2 border-amber-400 select-all">
        {matched}
      </mark>
      {after}
    </span>
  );
};

