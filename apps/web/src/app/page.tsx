import Link from "next/link";
import { Telescope } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentResearch } from "@/components/dashboard/recent-research";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your research library on Backblaze B2 — threads, cached sources,
            screenshots, and storage.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/research">
            <Telescope className="h-3.5 w-3.5" />
            New research
          </Link>
        </Button>
      </div>
      <StatsCards />
      <div className="animate-fade-in-up stagger-3">
        <RecentResearch />
      </div>
    </div>
  );
}
