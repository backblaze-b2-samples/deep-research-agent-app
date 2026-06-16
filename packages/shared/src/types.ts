export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Research agent ---
// These mirror services/api/app/types/research.py. Keep the two in sync.

export type ResearchStatus = "pending" | "running" | "complete" | "failed";

export interface Source {
  source_id: string;
  url: string;
  title: string;
  fetched_at: string;
  sha256: string;
  html_bytes: number;
  text_bytes: number;
  has_screenshot: boolean;
}

export interface ResearchTurn {
  question: string;
  report_id: string;
  source_ids: string[];
  created_at: string;
}

export interface ReportMeta {
  research_id: string;
  question: string;
  model: string;
  status: ResearchStatus;
  created_at: string;
  updated_at: string;
  sources: Source[];
  turns: ResearchTurn[];
  error: string | null;
}

export interface ResearchSummary {
  research_id: string;
  question: string;
  status: ResearchStatus;
  model: string;
  created_at: string;
  updated_at: string;
  source_count: number;
  turn_count: number;
}

export interface ResearchTurnView {
  question: string;
  report_id: string;
  report_markdown: string | null;
  source_ids: string[];
  created_at: string;
}

export interface ResearchDetail {
  meta: ReportMeta;
  report_markdown: string | null;
  // The full conversation: every completed turn with its own report, oldest
  // first. The detail page renders this so prior questions and answers stay
  // visible across follow-ups.
  turns: ResearchTurnView[];
}

export interface StartResearchResponse {
  research_id: string;
  status: ResearchStatus;
}

export interface ResearchSearchHit {
  research_id: string;
  question: string;
  status: ResearchStatus;
  created_at: string;
  matched_in: string;
  snippet: string;
}

export interface ResearchStats {
  total_research: number;
  total_sources: number;
  total_screenshots: number;
  total_storage_bytes: number;
  total_storage_human: string;
  research_today: number;
}
