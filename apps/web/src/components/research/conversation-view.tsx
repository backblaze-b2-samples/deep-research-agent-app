"use client";

import { AlertTriangle } from "lucide-react";
import { ErrorState } from "@/components/ui/error-state";
import { ReportView } from "@/components/research/report-view";
import { RunStatus } from "@/components/research/run-status";
import type {
  ReportMeta,
  ResearchTurnView,
} from "@deep-research-agent-app/shared";

/**
 * Renders a research thread as a full conversation: every completed turn shows
 * the question that was asked and the report it produced, oldest first. A turn
 * that is still in flight (the latest follow-up, or the very first run) shows
 * the active question followed by live status; a failed run shows the error.
 *
 * This is what keeps prior questions and answers visible across follow-ups —
 * the page used to render only the latest report, so earlier turns vanished.
 */
function QuestionBubble({ question }: { question: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-[var(--primary)] px-4 py-2.5 text-left text-sm text-[var(--primary-foreground)]">
        {question}
      </div>
    </div>
  );
}

export function ConversationView({
  meta,
  turns,
}: {
  meta: ReportMeta;
  turns: ResearchTurnView[];
}) {
  const isRunning = meta.status === "pending" || meta.status === "running";
  const isFailed = meta.status === "failed";

  if (turns.length === 0 && !isRunning && !isFailed) {
    return (
      <p className="text-sm text-muted-foreground">No report was produced.</p>
    );
  }

  return (
    <div className="space-y-8">
      {turns.map((turn, i) => (
        <div key={turn.report_id || i} className="space-y-4">
          <QuestionBubble question={turn.question} />
          {turn.report_markdown ? (
            <ReportView markdown={turn.report_markdown} />
          ) : (
            <p className="text-sm text-muted-foreground">
              The report for this turn is no longer available.
            </p>
          )}
          {(i < turns.length - 1 || isRunning || isFailed) && (
            <hr className="border-border" />
          )}
        </div>
      ))}

      {/* The active turn: question already submitted, run still in flight. */}
      {isRunning && (
        <div className="space-y-4">
          <QuestionBubble question={meta.question} />
          <RunStatus meta={meta} />
        </div>
      )}

      {isFailed && (
        <div className="space-y-4">
          <QuestionBubble question={meta.question} />
          <ErrorState
            icon={AlertTriangle}
            title="Research failed"
            description={meta.error || "The run did not complete."}
          />
        </div>
      )}
    </div>
  );
}
