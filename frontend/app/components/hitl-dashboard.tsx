"use client";

import { useState, useMemo } from "react";
import { ChevronLeft, ChevronRight, User, FileText, Check, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ReportPanel } from "./report-panel";
import { ValidationBadges } from "./validation-badges";
import { ActionButtons } from "./action-buttons";
import { EditPanel } from "./edit-panel";
import { EntityList } from "./entity-list";
import { ReportsSidebar, type ReportListItem } from "./reports-sidebar";
import { cn } from "@/lib/utils";

// Sample data - in production this would come from your API
const sampleReport = {
  id: "RPT-89012",
  patientId: "PAT-89012",
  patientName: "John Smith",
  date: "2024-01-15",
  originalReport: `CHEST X-RAY EXAMINATION

CLINICAL HISTORY: Persistent cough for 2 weeks.

FINDINGS:
There is a 5mm nodule identified in the right lower lobe. The nodule appears well-circumscribed with smooth margins. Mild opacification is noted in the pleural space, which may represent a small amount of pleural fluid or pleural thickening. The cardiac silhouette is within normal limits. No acute osseous abnormalities are identified. The visualized soft tissues are unremarkable.

IMPRESSION:
1. Small 5mm nodule in the right lower lobe - recommend follow-up CT in 3-6 months to assess stability.
2. Mild pleural opacification on the right side - clinical correlation recommended.
3. No acute cardiopulmonary process identified.`,
  
  aiSummary: `Your chest X-ray showed a few findings we want to share with you in plain terms.

We found a small spot (5mm) in the lower part of your right lung. This spot has smooth edges, which is generally a reassuring sign. Your doctor may want to do a follow-up scan in a few months to make sure it stays the same size.

There is also a small area that appears white on the X-ray near your lung lining on the right side. This could indicate a tiny amount of fluid or some thickening, and your doctor may want to discuss this with you.

The good news is that your heart looks normal in size, and there are no signs of an urgent lung problem. Your bones also look healthy.

Please discuss these findings with your healthcare provider who can give you personalized advice based on your complete medical history.`,

  entities: {
    findings: ["5mm nodule", "mild opacification", "well-circumscribed", "smooth margins"],
    anatomy: ["right lower lobe", "pleural space", "cardiac silhouette"],
    measurements: ["5mm"],
    uncertainty: ["may represent", "recommend follow-up"],
  },

  validationChecks: [
    { name: "Fidelity", status: "pass" as const, description: "All critical findings preserved" },
    { name: "Hallucination", status: "pass" as const, description: "No invented information detected" },
    { name: "Readability", status: "pass" as const, description: "Grade level: 6.8" },
    { name: "Safety", status: "pass" as const, description: "No alarmist language detected" },
  ],

  sentenceMapping: [
    { summary: 0, original: [0] },
    { summary: 1, original: [2, 3] },
    { summary: 2, original: [4] },
    { summary: 3, original: [5, 6] },
    { summary: 4, original: [7] },
  ],
};

type ReviewStatus = "pending" | "approved" | "rejected";

// Sample reports data - in production this would come from your API
const sampleReports: ReportListItem[] = [
  { id: "RPT-89012", patientId: "PAT-89012", patientName: "John Smith", date: "2024-01-15", status: "pending" },
  { id: "RPT-89011", patientId: "PAT-89011", patientName: "Jane Doe", date: "2024-01-14", status: "approved" },
  { id: "RPT-89010", patientId: "PAT-89010", patientName: "Robert Johnson", date: "2024-01-14", status: "pending" },
  { id: "RPT-89009", patientId: "PAT-89009", patientName: "Emily Williams", date: "2024-01-13", status: "rejected" },
  { id: "RPT-89008", patientId: "PAT-89008", patientName: "Michael Brown", date: "2024-01-13", status: "approved" },
  { id: "RPT-89007", patientId: "PAT-89007", patientName: "Sarah Davis", date: "2024-01-12", status: "pending" },
  { id: "RPT-89006", patientId: "PAT-89006", patientName: "David Miller", date: "2024-01-12", status: "pending" },
  { id: "RPT-89005", patientId: "PAT-89005", patientName: "Lisa Wilson", date: "2024-01-11", status: "approved" },
];

export function HITLDashboard() {
  const [hoveredSentence, setHoveredSentence] = useState<number | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSummary, setEditedSummary] = useState(sampleReport.aiSummary);
  const [selectedReportId, setSelectedReportId] = useState(sampleReport.id);
  const [queuePosition] = useState({ current: 3, total: 12 });
  const [status, setStatus] = useState<ReviewStatus>("pending");

  // Get current report based on selection
  const currentReport = useMemo(() => {
    // In production, this would fetch from API based on selectedReportId
    return sampleReport;
  }, [selectedReportId]);

  const getHighlightedOriginalSentences = (): number[] => {
    if (hoveredSentence === null) return [];
    const mapping = currentReport.sentenceMapping.find(m => m.summary === hoveredSentence);
    return mapping?.original || [];
  };

  const getHighlightedSummarySentences = (): number[] => {
    if (hoveredSentence === null) return [];
    return [hoveredSentence];
  };

  const handleApprove = () => {
    setStatus("approved");
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditedSummary(currentReport.aiSummary);
  };

  const handleReject = () => {
    setStatus("rejected");
  };

  const handleSaveEdit = () => {
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedSummary(currentReport.aiSummary);
  };

  const resetReview = () => {
    setStatus("pending");
    setEditedSummary(sampleReport.aiSummary);
    setIsEditing(false);
  };

  // Status screens
  if (status !== "pending") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background p-8">
        <div className="rounded-lg border border-border bg-card p-8 text-center shadow-sm">
          <div
            className={cn(
              "mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full",
              status === "approved" ? "bg-primary/10" : "bg-destructive/10"
            )}
          >
            {status === "approved" ? (
              <Check className="h-8 w-8 text-primary" />
            ) : (
              <AlertCircle className="h-8 w-8 text-destructive" />
            )}
          </div>
          <h2 className="mb-2 text-xl font-semibold text-foreground">
            {status === "approved"
              ? "Summary Approved & Sent"
              : "Summary Flagged for Review"}
          </h2>
          <p className="mb-6 text-muted-foreground">
            {status === "approved"
              ? "The patient summary has been approved and queued for delivery."
              : "This report has been flagged and returned to the processing queue."}
          </p>
          <Button 
            onClick={resetReview} 
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            Review Another Report
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border bg-primary px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary-foreground" />
              <h1 className="text-lg font-semibold text-primary-foreground">
                Radiology AI Summary Review
              </h1>
            </div>
            <span className="text-primary-foreground/70">|</span>
            <span className="text-sm text-primary-foreground/80">
              Patient ID: {currentReport.patientId}
            </span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-primary-foreground/80">
              <User className="h-4 w-4" />
              <span>Dr. Sarah Chen</span>
            </div>
            <div className="flex items-center gap-2 rounded-md bg-primary-foreground/10 px-3 py-1.5">
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-primary-foreground hover:bg-primary-foreground/20"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm font-medium text-primary-foreground">
                {queuePosition.current} / {queuePosition.total}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-primary-foreground hover:bg-primary-foreground/20"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content with Sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <ReportsSidebar
          reports={sampleReports}
          currentReportId={selectedReportId}
          onReportSelect={setSelectedReportId}
        />

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto max-w-7xl space-y-6">
          {/* Validation Status */}
          <div className="flex items-center justify-between rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-muted-foreground">
                Validation Checks:
              </span>
              <ValidationBadges checks={currentReport.validationChecks} />
            </div>
            <div className="text-xs text-muted-foreground">
              Report Date: {currentReport.date}
            </div>
          </div>

          {/* Two-Column Layout */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Original Report */}
            <ReportPanel
              title="Original Radiologist Report"
              content={currentReport.originalReport}
              highlightedSentences={getHighlightedOriginalSentences()}
              variant="original"
            />

            {/* AI Summary or Edit Panel */}
            {isEditing ? (
              <EditPanel
                value={editedSummary}
                onChange={setEditedSummary}
              />
            ) : (
              <ReportPanel
                title="Validated AI Patient Summary"
                content={currentReport.aiSummary}
                highlightedSentences={getHighlightedSummarySentences()}
                onSentenceHover={setHoveredSentence}
                variant="summary"
              />
            )}
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between rounded-lg border-t border-border/50 bg-card p-4">
            <ActionButtons
              isEditing={isEditing}
              onApprove={handleApprove}
              onEdit={handleEdit}
              onReject={handleReject}
              onSaveEdit={handleSaveEdit}
              onCancelEdit={handleCancelEdit}
            />
            
            <div className="text-xs text-muted-foreground">
              <span className="text-primary">Tip:</span> Hover over summary sentences to see their source in the original report
            </div>
          </div>

          {/* Entity Extraction Panel */}
          <EntityList entities={currentReport.entities} />
          </div>
        </main>
      </div>
    </div>
  );
}
