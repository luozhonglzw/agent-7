/**
 * Shared TypeScript types for the RAG Knowledge Base frontend.
 *
 * These types mirror the backend Pydantic schemas for type-safe
 * API communication.
 */

// ── API Response ─────────────────────────────────────────────

/** Standard API response wrapper. */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T | null;
}

/** Paginated list response. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// ── Authentication ────────────────────────────────────────────

/** User login request. */
export interface LoginRequest {
  email: string;
  password: string;
}

/** User registration request. */
export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

/** JWT token response. */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/** User profile. */
export interface UserProfile {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: "admin" | "editor" | "viewer";
  is_active: boolean;
  avatar_url: string | null;
  created_at: string;
  last_login_at: string | null;
}

// ── Documents ─────────────────────────────────────────────────

/** Document details. */
export interface Document {
  id: string;
  title: string;
  filename: string;
  file_size: number;
  file_type: string;
  status: DocumentStatus;
  error_message: string | null;
  page_count: number | null;
  chunk_count: number | null;
  token_count: number | null;
  is_public: boolean;
  created_at: string;
  processed_at: string | null;
}

/** Document processing status. */
export type DocumentStatus =
  | "pending"
  | "parsing"
  | "chunking"
  | "embedding"
  | "indexing"
  | "ready"
  | "failed";

// ── Search & Q&A ──────────────────────────────────────────────

/** Search request. */
export interface SearchRequest {
  query: string;
  top_k?: number;
  document_ids?: string[];
  file_types?: string[];
  use_reranker?: boolean;
  score_threshold?: number;
}

/** Retrieved source chunk. */
export interface SourceChunk {
  chunk_id: string;
  document_id: string;
  document_title: string;
  content: string;
  score: number;
  page_number: number | null;
  heading: string | null;
}

/** Search results response. */
export interface SearchResponse {
  query: string;
  results: SourceChunk[];
  total: number;
  search_time_ms: number;
}

/** Q&A request. */
export interface QARequest {
  question: string;
  top_k?: number;
  document_ids?: string[];
  stream?: boolean;
  max_tokens?: number;
}

/** Q&A response with citations. */
export interface QAResponse {
  question: string;
  answer: string;
  sources: SourceChunk[];
  model: string;
  tokens_used: number;
  response_time_ms: number;
}

// ── Admin ─────────────────────────────────────────────────────

/** System statistics. */
export interface SystemStats {
  total_users: number;
  active_users: number;
  total_documents: number;
  ready_documents: number;
  total_chunks: number;
  total_embeddings: number;
  storage_used_mb: number;
}

// ── Audit ─────────────────────────────────────────────────────

/** Audit log entry. */
export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

// ── UI State ──────────────────────────────────────────────────

/** Chat message in Q&A interface. */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
  timestamp: Date;
  isStreaming?: boolean;
}
