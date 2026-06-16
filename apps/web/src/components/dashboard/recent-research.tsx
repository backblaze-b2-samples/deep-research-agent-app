"use client";

import Link from "next/link";
import { ArrowRight, Telescope } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ResearchStatusBadge } from "@/components/research/research-status-badge";
import { useResearchLibrary } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export function RecentResearch() {
  const { data: items = [], isLoading, error, refetch } = useResearchLibrary(8);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Research</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/library"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View library
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={Telescope}
            title="No research yet"
            description="Head to Research to ask your first question."
          />
        ) : (
          <ul className="divide-y divide-border">
            {items.map((item) => (
              <li key={item.research_id}>
                <Link
                  href={`/research/${item.research_id}`}
                  className="flex items-center justify-between gap-3 px-5 py-3 table-row-hover"
                >
                  <span className="font-medium text-sm truncate flex-1">
                    {item.question}
                  </span>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {item.source_count} sources
                  </span>
                  <span className="whitespace-nowrap">
                    <ResearchStatusBadge status={item.status} />
                  </span>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {formatDate(item.created_at)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
