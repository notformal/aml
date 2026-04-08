import type {
  Context,
  ContextParams,
  Episode,
  FeedbackParams,
  LogParams,
  MemoryClientConfig,
  Rule,
  RulesParams,
} from './types';

export class MemoryClient {
  private readonly baseUrl: string;
  private readonly project: string;
  private readonly module: string;
  private readonly timeout: number;

  constructor(config: MemoryClientConfig) {
    this.baseUrl = config.apiUrl.replace(/\/$/, '') + '/api/v1';
    this.project = config.project;
    this.module = config.module;
    this.timeout = config.timeout ?? 30000;
  }

  private get moduleId(): string {
    return `${this.project}.${this.module}`;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    params?: Record<string, string>,
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(url.toString(), {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`AML API ${resp.status}: ${text}`);
      }

      return (await resp.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }

  // ── Episode logging ──

  async log(params: LogParams): Promise<string> {
    const data = await this.request<{ id: string }>('POST', '/episodes', {
      module_id: this.moduleId,
      action: params.action,
      input_data: params.inputData,
      output_data: params.outputData,
      metadata: params.metadata ?? {},
    });
    return data.id;
  }

  // ── Feedback ──

  async feedback(params: FeedbackParams): Promise<string> {
    const data = await this.request<{ id: string }>(
      'POST',
      `/episodes/${params.episodeId}/feedback`,
      {
        score: params.score,
        feedback_type: params.feedbackType ?? 'auto_metric',
        source: params.source ?? null,
        details: params.details ?? {},
      },
    );
    return data.id;
  }

  // ── Context (episodes + rules) ──

  async getContext(params: ContextParams): Promise<Context> {
    return this.request<Context>('POST', '/context', {
      module_id: this.moduleId,
      query: params.query,
      top_k: params.topK ?? 10,
      min_score: params.minScore ?? 0,
      min_confidence: params.minConfidence ?? 0.3,
      tags: params.tags ?? null,
    });
  }

  // ── Rules ──

  async getRules(params?: RulesParams): Promise<Rule[]> {
    const queryParams: Record<string, string> = {
      module_id: this.moduleId,
      min_confidence: String(params?.minConfidence ?? 0.3),
      active_only: 'true',
    };
    if (params?.tags?.length) {
      queryParams.tags = params.tags.join(',');
    }
    return this.request<Rule[]>('GET', '/rules', undefined, queryParams);
  }

  // ── Setup helpers ──

  async ensureProject(name?: string): Promise<void> {
    try {
      await this.request('POST', '/projects', {
        id: this.project,
        name: name ?? this.project,
      });
    } catch (e: any) {
      if (!e.message?.includes('409')) throw e;
    }
  }

  async ensureModule(
    moduleType: string = 'generation',
    name?: string,
  ): Promise<void> {
    try {
      await this.request('POST', '/modules', {
        id: this.moduleId,
        project_id: this.project,
        name: name ?? this.module,
        module_type: moduleType,
      });
    } catch (e: any) {
      if (!e.message?.includes('409')) throw e;
    }
  }
}
