"use client";

import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ValidationCheck {
  name: string;
  status: "pass" | "fail" | "warning";
  description: string;
}

interface ValidationBadgesProps {
  checks: ValidationCheck[];
}

export function ValidationBadges({ checks }: ValidationBadgesProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {checks.map((check) => (
        <div
          key={check.name}
          className={cn(
            "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
            check.status === "pass" &&
              "bg-emerald-100 text-emerald-700",
            check.status === "fail" &&
              "bg-red-100 text-red-700",
            check.status === "warning" &&
              "bg-amber-100 text-amber-700"
          )}
          title={check.description}
        >
          {check.status === "pass" && <CheckCircle2 className="h-3.5 w-3.5" />}
          {check.status === "fail" && <XCircle className="h-3.5 w-3.5" />}
          {check.status === "warning" && (
            <AlertTriangle className="h-3.5 w-3.5" />
          )}
          {check.name}
        </div>
      ))}
    </div>
  );
}
