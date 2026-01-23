"use client";

import { Textarea } from "@/components/ui/textarea";

interface EditPanelProps {
  value: string;
  onChange: (value: string) => void;
}

export function EditPanel({ value, onChange }: EditPanelProps) {
  return (
    <div className="flex h-full flex-col rounded-lg border-2 border-amber-400 bg-card shadow-sm">
      <div className="flex items-center gap-3 border-b border-border px-5 py-4">
        <div className="h-2.5 w-2.5 rounded-full bg-amber-500" />
        <h2 className="font-semibold text-foreground">
          Editing Summary
        </h2>
      </div>
      <div className="flex-1 p-5">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-full min-h-[300px] resize-none border-border bg-white text-foreground focus:border-amber-400 focus:ring-amber-400"
          placeholder="Edit the patient summary..."
        />
      </div>
    </div>
  );
}
