"use client";

import { cn } from "@/lib/utils";

interface EntityListProps {
  entities: {
    findings: string[];
    anatomy: string[];
    measurements: string[];
    uncertainty: string[];
  };
}

export function EntityList({ entities }: EntityListProps) {
  const categories = [
    { key: "findings", label: "Findings", color: "bg-emerald-500" },
    { key: "anatomy", label: "Anatomy", color: "bg-sky-500" },
    { key: "measurements", label: "Measurements", color: "bg-violet-500" },
    { key: "uncertainty", label: "Uncertainty", color: "bg-amber-500" },
  ] as const;

  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold text-foreground">
        Extracted Entities
      </h3>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {categories.map(({ key, label, color }) => (
          <div key={key}>
            <div className="mb-2 flex items-center gap-2">
              <div className={cn("h-2 w-2 rounded-full", color)} />
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {label}
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(entities[key]?.length ?? 0) > 0 ? (
                entities[key].map((item, index) => (
                  <span
                    key={index}
                    className="rounded-md bg-secondary px-2.5 py-1 text-xs text-foreground"
                  >
                    {item}
                  </span>
                ))
              ) : (
                <span className="text-xs text-muted-foreground italic">None detected</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
