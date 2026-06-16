"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders a research report's Markdown. The agent writes GitHub-flavored
 * Markdown with inline [n] citations and a "## Sources" list; we render it with
 * prose styling that picks up the app's design tokens.
 */
export function ReportView({ markdown }: { markdown: string }) {
  return (
    <article
      className="prose prose-sm dark:prose-invert max-w-none
        prose-headings:font-display prose-headings:tracking-tight
        prose-a:text-[var(--primary)] prose-a:no-underline hover:prose-a:underline
        prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5
        prose-pre:bg-muted prose-pre:border prose-pre:border-border"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </article>
  );
}
