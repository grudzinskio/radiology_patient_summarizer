"use client";

import { Check, Pencil, X, Send, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ActionButtonsProps {
  isEditing: boolean;
  onApprove: () => void;
  onEdit: () => void;
  onReject: () => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
}

export function ActionButtons({
  isEditing,
  onApprove,
  onEdit,
  onReject,
  onSaveEdit,
  onCancelEdit,
}: ActionButtonsProps) {
  if (isEditing) {
    return (
      <div className="flex items-center gap-3">
        <Button
          onClick={onSaveEdit}
          className="bg-emerald-600 text-white hover:bg-emerald-700"
        >
          <Check className="mr-2 h-4 w-4" />
          Save Changes
        </Button>
        <Button
          onClick={onCancelEdit}
          variant="outline"
          className="border-border bg-transparent text-foreground hover:bg-muted"
        >
          <RotateCcw className="mr-2 h-4 w-4" />
          Discard
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Button
        onClick={onApprove}
        className="bg-emerald-600 text-white hover:bg-emerald-700"
      >
        <Send className="mr-2 h-4 w-4" />
        Approve & Send
      </Button>
      <Button
        onClick={onEdit}
        className="bg-amber-500 text-white hover:bg-amber-600"
      >
        <Pencil className="mr-2 h-4 w-4" />
        Edit
      </Button>
      <Button
        onClick={onReject}
        className="bg-red-600 text-white hover:bg-red-700"
      >
        <X className="mr-2 h-4 w-4" />
        Reject
      </Button>
    </div>
  );
}
