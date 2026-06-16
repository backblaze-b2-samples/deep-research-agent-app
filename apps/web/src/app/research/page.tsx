"use client";

import Link from "next/link";
import { ArrowRight, Telescope } from "lucide-react";
import { AskForm } from "@/components/research/ask-form";
import { ResearchGrid } from "@/components/library/research-grid";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useResearchLibrary } from "@/lib/queries";

export default function ResearchPage() {
  const { data: items = [], isLoading, error, refetch } = useResearchLibrary(6);

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Research</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Ask a question. The agent researches the web and writes a cited
          report — caching every source on Backblaze B2.
        </p>
      </div>

      <div className="animate-fade-in-up stagger-1">
        <AskForm />
      </div>

      <div className="animate-fade-in-up stagger-2 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="card-title">Recent research</h2>
          <Link
            href="/library"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View library
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={Telescope}
            title="No research yet"
            description="Ask your first question above to get started."
          />
        ) : (
          <ResearchGrid items={items} />
        )}
      </div>
    </div>
  );
}
