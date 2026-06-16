import { Loader2 } from "lucide-react";
import type { ResearchStatus } from "@deep-research-agent-app/shared";

const STATUS: Record<
  ResearchStatus,
  { label: string; dot: string; spin?: boolean }
> = {
  pending: { label: "Queued", dot: "bg-muted-foreground", spin: true },
  running: { label: "Researching", dot: "bg-[var(--primary)]", spin: true },
  complete: { label: "Complete", dot: "bg-[var(--success)]" },
  failed: { label: "Failed", dot: "bg-destructive" },
};

export function ResearchStatusBadge({ status }: { status: ResearchStatus }) {
  const s = STATUS[status];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      {s.spin ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : (
        <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      )}
      {s.label}
    </span>
  );
}
