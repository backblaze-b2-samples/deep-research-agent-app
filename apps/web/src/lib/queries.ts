"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  deleteFile,
  deleteResearch,
  followUpResearch,
  getFiles,
  getFileStats,
  getPreviewUrl,
  getResearch,
  getResearchLibrary,
  getResearchSources,
  getResearchStats,
  getUploadActivity,
  searchResearch,
  startResearch,
} from "@/lib/api-client";
import type {
  FileMetadata,
  ResearchDetail,
  ResearchSummary,
} from "@deep-research-agent-app/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  // Research
  research: ["research"] as const,
  researchLibrary: (limit?: number) =>
    [...qk.research, "library", limit ?? 100] as const,
  researchDetail: (id: string) => [...qk.research, "detail", id] as const,
  researchSources: (id: string) => [...qk.research, "sources", id] as const,
  researchStats: () => [...qk.research, "stats"] as const,
  researchSearch: (q: string) => [...qk.research, "search", q] as const,
};

// Poll while a run is in flight; stop once it's done. Returns the
// refetchInterval value TanStack Query expects (ms, or false to stop).
function researchPollInterval(detail: ResearchDetail | undefined): number | false {
  const status = detail?.meta.status;
  return status === "pending" || status === "running" ? 2000 : false;
}

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Research agent ---

export function useResearchLibrary(limit = 100) {
  return useQuery<ResearchSummary[], ApiError>({
    queryKey: qk.researchLibrary(limit),
    queryFn: () => getResearchLibrary(limit),
  });
}

/** Polls every 2s while the run is pending/running, then stops. */
export function useResearch(id: string | undefined) {
  return useQuery<ResearchDetail, ApiError>({
    queryKey: qk.researchDetail(id ?? ""),
    queryFn: () => getResearch(id as string),
    enabled: !!id,
    refetchInterval: (query) => researchPollInterval(query.state.data),
  });
}

export function useResearchSources(id: string | undefined) {
  return useQuery({
    queryKey: qk.researchSources(id ?? ""),
    queryFn: () => getResearchSources(id as string),
    enabled: !!id,
  });
}

export function useResearchStats() {
  return useQuery({
    queryKey: qk.researchStats(),
    queryFn: getResearchStats,
  });
}

export function useResearchSearch(query: string) {
  return useQuery({
    queryKey: qk.researchSearch(query),
    queryFn: () => searchResearch(query),
    enabled: query.trim().length > 0,
  });
}

export function useStartResearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (question: string) => startResearch(question),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.research });
    },
  });
}

export function useFollowUp(researchId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (question: string) => followUpResearch(researchId, question),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.researchDetail(researchId) });
    },
  });
}

export function useDeleteResearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (researchId: string) => deleteResearch(researchId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.research });
    },
  });
}
