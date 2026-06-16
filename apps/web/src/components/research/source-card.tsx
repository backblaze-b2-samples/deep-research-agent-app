"use client";

import { ExternalLink, Camera, FileText, ImageOff } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { getSourceArtifactUrl } from "@/lib/api-client";
import { humanizeBytes, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import type { Source } from "@deep-research-agent-app/shared";

export function SourceCard({
  researchId,
  source,
}: {
  researchId: string;
  source: Source;
}) {
  async function openArtifact(
    artifact: "page.html" | "page.md" | "screenshot.png",
  ) {
    try {
      const { url } = await getSourceArtifactUrl(
        researchId,
        source.source_id,
        artifact,
      );
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      toast.error("Could not open cached artifact");
    }
  }

  return (
    <Card className="card-hover">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-medium text-sm leading-snug line-clamp-2">
            {source.title}
          </h3>
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground shrink-0"
            title="Open original"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
        <p className="text-xs text-muted-foreground truncate">{source.url}</p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
          <span>{formatDate(source.fetched_at)}</span>
          <span>HTML {humanizeBytes(source.html_bytes)}</span>
          <span>Text {humanizeBytes(source.text_bytes)}</span>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {source.has_screenshot ? (
            <button
              type="button"
              onClick={() => openArtifact("screenshot.png")}
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <Camera className="h-3.5 w-3.5" /> Screenshot
            </button>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground/60">
              <ImageOff className="h-3.5 w-3.5" /> No screenshot
            </span>
          )}
          <button
            type="button"
            onClick={() => openArtifact("page.md")}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <FileText className="h-3.5 w-3.5" /> Cached text
          </button>
          <button
            type="button"
            onClick={() => openArtifact("page.html")}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <FileText className="h-3.5 w-3.5" /> Cached HTML
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
