"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FileText, Loader2, Sparkles } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { toast } from "sonner";

interface SubmitReportFormProps {
  onSuccess?: (summaryId: string) => void;
  forceOpen?: boolean;
}

export function SubmitReportForm({ onSuccess, forceOpen = false }: SubmitReportFormProps) {
  const [medicalReport, setMedicalReport] = useState("");
  const [patientId, setPatientId] = useState("");
  const [reportId, setReportId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  
  // Use forceOpen if provided, otherwise use internal state
  const showForm = forceOpen || isOpen;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!medicalReport.trim()) {
      toast.error("Please enter a medical report");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await api.summarizeReport(
        medicalReport,
        patientId || null,
        reportId || null
      );
      
      toast.success("Report submitted successfully!", {
        description: `Summary ID: ${response.summary_id}`,
      });
      
      // Reset form
      setMedicalReport("");
      setPatientId("");
      setReportId("");
      if (!forceOpen) {
        setIsOpen(false);
      }
      
      // Refresh reports list and select new report
      if (onSuccess) {
        onSuccess(response.summary_id);
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to submit report";
      toast.error("Failed to submit report", {
        description: message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const loadSampleReport = () => {
    setMedicalReport(`CHEST X-RAY EXAMINATION

CLINICAL HISTORY: Persistent cough for 2 weeks.

FINDINGS:
There is a 5mm nodule identified in the right lower lobe. The nodule appears well-circumscribed with smooth margins. Mild opacification is noted in the pleural space, which may represent a small amount of pleural fluid or pleural thickening. The cardiac silhouette is within normal limits. No acute osseous abnormalities are identified. The visualized soft tissues are unremarkable.

IMPRESSION:
1. Small 5mm nodule in the right lower lobe - recommend follow-up CT in 3-6 months to assess stability.
2. Mild pleural opacification on the right side - clinical correlation recommended.
3. No acute cardiopulmonary process identified.`);
    setPatientId("PAT-89012");
    setReportId("RPT-89012");
    setIsOpen(true);
  };

  if (!showForm && !forceOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        className="bg-primary text-primary-foreground hover:bg-primary/90"
      >
        <Sparkles className="h-4 w-4 mr-2" />
        Submit New Report
      </Button>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">Submit Medical Report</h3>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsOpen(false)}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="medical-report" className="text-sm font-medium text-foreground mb-2 block">
            Medical Report <span className="text-destructive">*</span>
          </label>
          <Textarea
            id="medical-report"
            value={medicalReport}
            onChange={(e) => setMedicalReport(e.target.value)}
            placeholder="Paste the radiology or medical report here..."
            className="min-h-[200px] font-mono text-sm"
            required
            disabled={isSubmitting}
          />
          <p className="text-xs text-muted-foreground mt-1">
            Enter the complete medical report text
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="patient-id" className="text-sm font-medium text-foreground mb-2 block">
              Patient ID (Optional)
            </label>
            <input
              id="patient-id"
              type="text"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              placeholder="PAT-12345"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              disabled={isSubmitting}
            />
          </div>
          <div>
            <label htmlFor="report-id" className="text-sm font-medium text-foreground mb-2 block">
              Report ID (Optional)
            </label>
            <input
              id="report-id"
              type="text"
              value={reportId}
              onChange={(e) => setReportId(e.target.value)}
              placeholder="RPT-12345"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              disabled={isSubmitting}
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={loadSampleReport}
            disabled={isSubmitting}
          >
            Load Sample Report
          </Button>
          <div className="flex gap-2">
            {!forceOpen && (
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsOpen(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              disabled={isSubmitting || !medicalReport.trim()}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate Summary
                </>
              )}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
