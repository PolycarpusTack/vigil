/**
 * TypeScript types matching schema/audit_event.schema.json
 */

export interface SessionContext {
  session_id?: string;
  request_id?: string;
  correlation_id?: string;
}

export interface ActorContext {
  type?: "user" | "system" | "service" | "anonymous";
  id?: string;
  username?: string;
  email?: string;
  roles?: string[];
  ip_address?: string;
  user_agent?: string;
}

export interface ResourceInfo {
  type?: "table" | "file" | "endpoint" | "function";
  id?: string;
  name?: string;
  path?: string;
}

export interface ActionResult {
  status?: "SUCCESS" | "FAILURE" | "PARTIAL";
  code?: string;
  message?: string;
  rows_affected?: number;
  data_size_bytes?: number;
}

export interface ActionContext {
  type:
    | "READ"
    | "WRITE"
    | "UPDATE"
    | "DELETE"
    | "EXECUTE"
    | "CREATE"
    | "LOGIN"
    | "LOGOUT"
    | "ACCESS"
    | "MODIFY"
    | "GRANT"
    | "REVOKE"
    | "APPROVE"
    | "REJECT";
  category:
    | "DATABASE"
    | "API"
    | "AUTH"
    | "FILE"
    | "SYSTEM"
    | "NETWORK"
    | "SECURITY"
    | "COMPLIANCE"
    | "USER"
    | "ADMIN";
  operation?: string;
  description?: string;
  resource?: ResourceInfo;
  parameters?: Record<string, unknown>;
  result?: ActionResult;
}

export interface PerformanceMetrics {
  duration_ms?: number;
  cpu_time_ms?: number;
  memory_mb?: number;
  slow_query?: boolean;
  threshold_exceeded?: boolean;
}

export interface ErrorInfo {
  occurred?: boolean;
  type?: string;
  message?: string;
  stack_trace?: string;
  handled?: boolean;
}

export interface AuditEvent {
  event_id: string;
  timestamp: string;
  version: string;
  session?: SessionContext;
  actor?: ActorContext;
  action: ActionContext;
  performance?: PerformanceMetrics;
  error?: ErrorInfo;
  system?: Record<string, unknown>;
  custom?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface BatchRequest {
  events: AuditEvent[];
}

export interface IngestResponse {
  status: string;
  event_id: string;
}

export interface BatchResponse {
  status: string;
  accepted: number;
  errors: Array<{ index: number; error: string }>;
  event_ids: string[];
}

export interface AuditClientOptions {
  collectorUrl: string;
  apiKey?: string;
  application?: string;
  environment?: string;
  timeout?: number;
}
