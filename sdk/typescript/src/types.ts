export interface Episode {
  id: string;
  module_id: string;
  action: string;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  avg_score?: number | null;
}

export interface Rule {
  id: string;
  module_id: string;
  scope: string;
  rule_text: string;
  rule_structured: Record<string, unknown> | null;
  confidence: number;
  evidence_count: number;
  tags: string[];
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Context {
  episodes: Episode[];
  rules: Rule[];
}

export type FeedbackType = 'auto_metric' | 'human' | 'ab_test' | 'downstream';

export interface MemoryClientConfig {
  apiUrl: string;
  project: string;
  module: string;
  timeout?: number;
}

export interface LogParams {
  action: string;
  inputData: Record<string, unknown>;
  outputData: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface FeedbackParams {
  episodeId: string;
  score: number;
  feedbackType?: FeedbackType;
  source?: string;
  details?: Record<string, unknown>;
}

export interface ContextParams {
  query: string;
  topK?: number;
  minScore?: number;
  minConfidence?: number;
  tags?: string[];
}

export interface RulesParams {
  tags?: string[];
  minConfidence?: number;
}
