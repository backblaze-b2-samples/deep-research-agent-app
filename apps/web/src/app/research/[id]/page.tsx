"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { ConversationView } from "@/components/research/conversation-view";
import { SourceCard } from "@/components/research/source-card";
import { FollowUpBox } from "@/components/research/follow-up-box";
import { ResearchStatusBadge } from "@/components/research/research-status-badge";
import { useResearch } from "@/lib/queries";

export default function ResearchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, isLoading, error, refetch } = useResearch(id);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  if (!data) return null;

  const { meta, turns } = data;
  const isRunning = meta.status === "pending" || meta.status === "running";
  // The thread's title is its original (root) question — follow-ups overwrite
  // meta.question with the latest one, so derive the title from the first turn.
  const rootQuestion = turns[0]?.question ?? meta.question;

  return (
    <div className="space-y-6">
      <div className="animate-fade-in border-b border-border pb-5 space-y-2">
        <Link
          href="/library"
          className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" /> Library
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="page-title">{rootQuestion}</h1>
          <ResearchStatusBadge status={meta.status} />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardContent className="p-6">
              <ConversationView meta={meta} turns={turns} />
            </CardContent>
          </Card>

          {meta.status === "complete" && (
            <Card>
              <CardHeader className="border-b border-border py-4 px-5">
                <CardTitle className="card-title">Ask a follow-up</CardTitle>
              </CardHeader>
              <CardContent className="p-5">
                <FollowUpBox researchId={id} />
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-3">
          <h2 className="card-title">
            Cached sources ({meta.sources.length})
          </h2>
          {meta.sources.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {isRunning
                ? "Sources will appear here as the agent reads them."
                : "No sources were cached for this research."}
            </p>
          ) : (
            <div className="space-y-3">
              {meta.sources.map((source) => (
                <SourceCard
                  key={source.source_id}
                  researchId={id}
                  source={source}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
