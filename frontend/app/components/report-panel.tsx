"use client";

import { cn } from "@/lib/utils";

interface ReportPanelProps {
  title: string;
  content: string;
  highlightedSentences?: number[];
  onSentenceHover?: (index: number | null) => void;
  variant?: "original" | "summary";
}

export function ReportPanel({
  title,
  content,
  highlightedSentences = [],
  onSentenceHover,
  variant = "original",
}: ReportPanelProps) {
  const sentences = content.split(/(?<=[.!?])\s+/).filter(Boolean);

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-card shadow-sm">
      <div className="flex items-center gap-3 border-b border-border px-5 py-4">
        <div
          className={cn(
            "h-2.5 w-2.5 rounded-full",
            variant === "original" ? "bg-amber-500" : "bg-emerald-600"
          )}
        />
        <h2 className="font-semibold text-foreground">
          {title}
        </h2>
      </div>
      <div className="flex-1 overflow-auto p-5">
        <div className="space-y-1 leading-relaxed text-foreground">
          {sentences.map((sentence, index) => (
            <span
              key={index}
              onMouseEnter={() => onSentenceHover?.(index)}
              onMouseLeave={() => onSentenceHover?.(null)}
              className={cn(
                "inline rounded transition-all duration-200",
                highlightedSentences.includes(index) && variant === "original" &&
                  "bg-amber-200 text-amber-900",
                highlightedSentences.includes(index) && variant === "summary" &&
                  "bg-sky-200 text-sky-900",
                variant === "summary" && "cursor-pointer hover:bg-muted"
              )}
            >
              {sentence}{" "}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
