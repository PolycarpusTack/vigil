/**
 * Vigil TypeScript SDK client.
 */

import { v4 as uuidv4 } from "uuid";
import type {
  AuditEvent,
  AuditClientOptions,
  ActorContext,
  ActionContext,
  PerformanceMetrics,
  ErrorInfo,
  IngestResponse,
  BatchResponse,
} from "./types";

export class AuditClient {
  private baseUrl: string;
  private apiKey: string;
  private application: string;
  private environment: string;
  private timeout: number;

  constructor(options: AuditClientOptions) {
    this.baseUrl = options.collectorUrl.replace(/\/+$/, "");
    this.apiKey = options.apiKey ?? "";
    this.application = options.application ?? "";
    this.environment = options.environment ?? "";
    this.timeout = options.timeout ?? 10000;
  }

  /**
   * Send a single audit event to the collector.
   */
  async log(params: {
    actionType?: string;
    actionCategory?: string;
    operation?: string;
    actor?: ActorContext;
    action?: Partial<ActionContext>;
    performance?: PerformanceMetrics;
    error?: ErrorInfo;
    custom?: Record<string, unknown>;
    metadata?: Record<string, unknown>;
  }): Promise<IngestResponse> {
    const event = this.buildEvent(params);
    const resp = await this.post<IngestResponse>("/api/v1/events", event);
    return resp;
  }

  /**
   * Send a batch of audit events to the collector.
   */
  async logBatch(events: AuditEvent[]): Promise<BatchResponse> {
    // Ensure defaults
    for (const e of events) {
      if (!e.event_id) e.event_id = uuidv4();
      if (!e.timestamp) e.timestamp = new Date().toISOString();
    }
    const resp = await this.post<BatchResponse>("/api/v1/events/batch", {
      events,
    });
    return resp;
  }

  private buildEvent(params: Record<string, unknown>): AuditEvent {
    const action: ActionContext = {
      type: (params.actionType as string) ?? "EXECUTE",
      category: (params.actionCategory as string) ?? "SYSTEM",
      ...(params.action as object),
    } as ActionContext;

    if (params.operation) {
      action.operation = params.operation as string;
    }

    const meta: Record<string, unknown> =
      (params.metadata as Record<string, unknown>) ?? {};
    if (this.application) meta.application ??= this.application;
    if (this.environment) meta.environment ??= this.environment;

    const event: AuditEvent = {
      event_id: uuidv4(),
      timestamp: new Date().toISOString(),
      version: "1.0.0",
      action,
    };

    if (params.actor) event.actor = params.actor as ActorContext;
    if (params.performance)
      event.performance = params.performance as PerformanceMetrics;
    if (params.error) event.error = params.error as ErrorInfo;
    if (params.custom) event.custom = params.custom as Record<string, unknown>;
    if (Object.keys(meta).length > 0) event.metadata = meta;

    return event;
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), this.timeout);

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    try {
      const resp = await fetch(`${this.baseUrl}${path}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!resp.ok) {
        throw new Error(`Collector returned ${resp.status}: ${await resp.text()}`);
      }

      return (await resp.json()) as T;
    } finally {
      clearTimeout(id);
    }
  }
}
