"use client";

import Link from "next/link";
import { Telescope, FileText, Trash2, MessagesSquare } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { ResearchStatusBadge } from "@/components/research/research-status-badge";
import { useDeleteResearch } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import { toast } from "sonner";
import type { ResearchSummary } from "@deep-research-agent-app/shared";

export function ResearchGrid({ items }: { items: ResearchSummary[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <ResearchCard key={item.research_id} item={item} />
      ))}
    </div>
  );
}

function ResearchCard({ item }: { item: ResearchSummary }) {
  const del = useDeleteResearch();

  function handleDelete() {
    del.mutate(item.research_id, {
      onSuccess: (res) =>
        toast.success(`Deleted research (${res.objects} objects removed from B2)`),
      onError: (err) => toast.error(err.message),
    });
  }

  return (
    <Card className="card-hover relative flex flex-col">
      <CardContent className="p-4 flex flex-col gap-3 flex-1">
        <Link
          href={`/research/${item.research_id}`}
          className="flex items-start gap-2 group flex-1"
        >
          <Telescope className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
          <span className="font-medium text-sm leading-snug line-clamp-3 group-hover:text-[var(--primary)]">
            {item.question}
          </span>
        </Link>
        <div className="flex items-center justify-between">
          <ResearchStatusBadge status={item.status} />
          <span className="text-[11px] text-muted-foreground">
            {formatDate(item.created_at)}
          </span>
        </div>
        <div className="flex items-center justify-between border-t border-border pt-2">
          <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <FileText className="h-3 w-3" /> {item.source_count} sources
            </span>
            <span className="inline-flex items-center gap-1">
              <MessagesSquare className="h-3 w-3" /> {item.turn_count} turns
            </span>
          </div>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this research?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently removes the report and every cached page,
                  screenshot, and metadata file for this thread from B2. This
                  cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleDelete}>
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
