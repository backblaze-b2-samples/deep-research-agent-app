"use client";

import { Loader2, Telescope } from "lucide-react";
import type { ReportMeta } from "@deep-research-agent-app/shared";

/**
 * Live progress while a run is pending/running: shows how many sources have
 * been fetched and cached to B2 so far. The page polls the detail endpoint,
 * and the service writes sources incrementally, so this count climbs in
 * near-real-time.
 */
export function RunStatus({ meta }: { meta: ReportMeta }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <div className="relative">
        <Telescope className="h-8 w-8 text-muted-foreground" />
        <Loader2 className="absolute -right-2 -top-2 h-4 w-4 animate-spin text-[var(--primary)]" />
      </div>
      <div>
        <p className="font-medium text-sm">
          {meta.status === "pending" ? "Queued…" : "Researching…"}
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          {meta.sources.length} source
          {meta.sources.length === 1 ? "" : "s"} fetched and cached on B2 so far
        </p>
      </div>
    </div>
  );
}
