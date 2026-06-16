"use client";

import { useState } from "react";
import { CornerDownLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useFollowUp } from "@/lib/queries";
import { toast } from "sonner";

/**
 * Ask a follow-up that builds on this thread's prior report. The backend loads
 * the prior report as cached context and runs another agentic turn that
 * updates the report and appends to the thread.
 */
export function FollowUpBox({ researchId }: { researchId: string }) {
  const [question, setQuestion] = useState("");
  const followUp = useFollowUp(researchId);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    followUp.mutate(q, {
      onSuccess: () => {
        toast.success("Follow-up started");
        setQuestion("");
      },
      onError: (err) => toast.error(err.message),
    });
  }

  const busy = followUp.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <Textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask a follow-up that builds on this report…"
        className="min-h-20 resize-y"
        disabled={busy}
      />
      <div className="flex justify-end">
        <Button type="submit" size="sm" disabled={busy || !question.trim()}>
          {busy ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <CornerDownLeft className="h-3.5 w-3.5" />
          )}
          Ask follow-up
        </Button>
      </div>
    </form>
  );
}
