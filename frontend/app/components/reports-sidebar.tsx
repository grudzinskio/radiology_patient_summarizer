"use client";

import { FileText, CheckCircle2, XCircle, Clock, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface ReportListItem {
  id: string;
  patientId: string;
  patientName: string;
  date: string;
  status: "pending" | "approved" | "rejected";
}

interface ReportsSidebarProps {
  reports: ReportListItem[];
  currentReportId: string;
  onReportSelect: (reportId: string) => void;
  onCreateNew?: () => void;
}

export function ReportsSidebar({
  reports,
  currentReportId,
  onReportSelect,
  onCreateNew,
}: ReportsSidebarProps) {
  const getStatusIcon = (status: ReportListItem["status"]) => {
    switch (status) {
      case "approved":
        return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />;
      case "rejected":
        return <XCircle className="h-3.5 w-3.5 text-red-500" />;
      default:
        return <Clock className="h-3.5 w-3.5 text-amber-500" />;
    }
  };

  return (
    <div className="flex h-full w-64 flex-col border-r border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Reports</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          {reports.length} total
        </p>
      </div>
      <div className="border-b border-border p-2">
        <Button
          onClick={onCreateNew}
          className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
          size="sm"
        >
          <Sparkles className="h-3.5 w-3.5 mr-2" />
          Submit New Report
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {reports.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <FileText className="h-8 w-8 text-muted-foreground/50 mb-2" />
            <p className="text-xs text-muted-foreground">
              No reports yet
            </p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Submit a medical report to get started
            </p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {reports.map((report) => (
              <button
                key={report.id}
                onClick={() => onReportSelect(report.id)}
                className={cn(
                  "flex w-full items-start gap-2 rounded-md px-3 py-2.5 text-left transition-colors",
                  "hover:bg-muted/50",
                  currentReportId === report.id
                    ? "bg-primary/10 text-foreground"
                    : "text-muted-foreground"
                )}
              >
                <FileText className="mt-0.5 h-4 w-4 shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p
                      className={cn(
                        "truncate text-xs font-medium",
                        currentReportId === report.id
                          ? "text-foreground"
                          : "text-muted-foreground"
                      )}
                    >
                      {report.patientId}
                    </p>
                    {getStatusIcon(report.status)}
                  </div>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {report.patientName}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground/70">
                    {report.date}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
