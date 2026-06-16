"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Telescope, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { useStartResearch } from "@/lib/queries";
import { toast } from "sonner";

export function AskForm() {
  const [question, setQuestion] = useState("");
  const router = useRouter();
  const startResearch = useStartResearch();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    startResearch.mutate(q, {
      onSuccess: (res) => {
        toast.success("Research started");
        router.push(`/research/${res.research_id}`);
      },
      onError: (err) => toast.error(err.message),
    });
  }

  const busy = startResearch.isPending;

  return (
    <Card>
      <CardContent className="p-5">
        <form onSubmit={handleSubmit} className="space-y-3">
          <Textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a research question — e.g. 'What are the tradeoffs between object storage and block storage for AI training data?'"
            className="min-h-28 resize-y"
            disabled={busy}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit(e);
            }}
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              The agent plans, searches the web, reads sources, and writes a
              cited report. Every page, screenshot, and report is cached on B2.
            </p>
            <Button type="submit" size="sm" disabled={busy || !question.trim()}>
              {busy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Telescope className="h-3.5 w-3.5" />
              )}
              Research
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
