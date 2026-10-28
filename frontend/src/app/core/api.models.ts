// Mirrors the FastAPI response models in src/log_intel (answer.py, api.py, history.py).

export type AnswerStatus = 'answered' | 'insufficient_evidence' | 'degraded';
export type Confidence = 'low' | 'medium' | 'high';
export type RetrievalMode = 'hybrid' | 'bm25' | 'embed';

export interface Health {
  status: 'ok';
  files: number;
  chunks: number;
  embeddings: boolean;
  llm: string | null;
  provider: string;
  embed_model: string;
  max_upload_mb: number;
  default_top_k: number;
}

export interface UploadResponse {
  filename: string;
  files_indexed: number;
  chunks: number;
  embeddings: boolean;
}

export interface Citation {
  chunk_id: string;
  file: string;
  start_line: number;
  end_line: number;
}

export interface Hypothesis {
  cause: string;
  explanation: string;
  confidence: Confidence;
  next_steps: string[];
  citations: Citation[];
}

export interface Evidence {
  chunk_id: string;
  file: string;
  start_line: number;
  end_line: number;
  score: number;
  text: string;
}

export interface Answer {
  id: string | null;
  status: AnswerStatus;
  question: string;
  hypotheses: Hypothesis[];
  evidence: Evidence[];
  model: string | null;
  notes: string[];
}

export interface AskRequest {
  question: string;
  top_k?: number;
  mode?: RetrievalMode;
}

export interface HistoryItem {
  id: string;
  created_at: string;
  question: string;
  status: AnswerStatus;
  model: string | null;
  top_cause: string | null;
}

export interface Investigation extends HistoryItem {
  answer: Answer;
}
