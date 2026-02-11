/**
 * Vigil TypeScript SDK
 *
 * Usage:
 *   import { AuditClient } from "audit-sdk";
 *
 *   const client = new AuditClient({
 *     collectorUrl: "http://localhost:8080",
 *     apiKey: "my-secret-key",
 *   });
 *
 *   await client.log({
 *     actionType: "READ",
 *     actionCategory: "DATABASE",
 *     operation: "query_users",
 *     actor: { type: "user", username: "admin" },
 *   });
 */

export { AuditClient } from "./client";
export type {
  AuditEvent,
  AuditClientOptions,
  ActorContext,
  ActionContext,
  SessionContext,
  ResourceInfo,
  ActionResult,
  PerformanceMetrics,
  ErrorInfo,
  IngestResponse,
  BatchResponse,
  BatchRequest,
} from "./types";
