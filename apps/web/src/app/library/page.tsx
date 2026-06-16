"use client";

import { useState } from "react";
import Link from "next/link";
import { Library as LibraryIcon, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ResearchGrid } from "@/components/library/research-grid";
import { ResearchStatusBadge } from "@/components/research/research-status-badge";
import { useResearchLibrary, useResearchSearch } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export default function LibraryPage() {
  const [query, setQuery] = useState("");
  const trimmed = query.trim();

  const library = useResearchLibrary(200);
  const search = useResearchSearch(trimmed);
  const searching = trimmed.length > 0;

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Research Library</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Every past research thread and its cached sources on B2. Search across
          questions, reports, and extracted source text.
        </p>
      </div>

      <div className="animate-fade-in-up stagger-1 relative max-w-lg">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search past research…"
          className="pl-9"
        />
      </div>

      <div className="animate-fade-in-up stagger-2">
        {searching ? (
          <SearchResults
            query={trimmed}
            loading={search.isLoading}
            error={search.error}
            hits={search.data ?? []}
          />
        ) : library.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : library.error ? (
          <ErrorState error={library.error} onRetry={() => library.refetch()} />
        ) : (library.data ?? []).length === 0 ? (
          <EmptyState
            icon={LibraryIcon}
            title="Your research library is empty"
            description="Run a research from the Research page and it will show up here."
          />
        ) : (
          <ResearchGrid items={library.data ?? []} />
        )}
      </div>
    </div>
  );
}

function SearchResults({
  query,
  loading,
  error,
  hits,
}: {
  query: string;
  loading: boolean;
  error: unknown;
  hits: import("@deep-research-agent-app/shared").ResearchSearchHit[];
}) {
  if (loading) return <Skeleton className="h-40 w-full" />;
  if (error) return <ErrorState error={error} />;
  if (hits.length === 0) {
    return (
      <EmptyState
        icon={Search}
        title="No matches"
        description={`Nothing in your library matches "${query}".`}
      />
    );
  }
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {hits.length} match{hits.length === 1 ? "" : "es"} for &ldquo;{query}
        &rdquo;
      </p>
      {hits.map((hit) => (
        <Link
          key={`${hit.research_id}-${hit.matched_in}`}
          href={`/research/${hit.research_id}`}
          className="block rounded-lg border border-border p-4 card-hover"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="font-medium text-sm">{hit.question}</p>
            <ResearchStatusBadge status={hit.status} />
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            matched in {hit.matched_in} · {formatDate(hit.created_at)}
          </p>
          <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
            {hit.snippet}
          </p>
        </Link>
      ))}
    </div>
  );
}
