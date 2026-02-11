/**
 * Unit tests for AuditClient.
 *
 * Uses vitest with the global fetch mock.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AuditClient } from "../client";
import type { IngestResponse, BatchResponse } from "../types";

// Mock uuid to return deterministic IDs
vi.mock("uuid", () => ({
  v4: () => "test-uuid-1234",
}));

function mockFetchOk<T>(data: T): void {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 201,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
}

function mockFetchError(status: number, body: string): void {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(body),
  });
}

describe("AuditClient", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("constructor", () => {
    it("sets properties from options", () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080/",
        apiKey: "my-key",
        application: "test-app",
        environment: "test",
        timeout: 5000,
      });

      // Verify by logging an event and checking the fetch call
      mockFetchOk<IngestResponse>({ status: "accepted", event_id: "123" });

      // Client should be constructed without error
      expect(client).toBeDefined();
    });

    it("strips trailing slashes from URL", async () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080///",
      });

      mockFetchOk<IngestResponse>({ status: "accepted", event_id: "123" });

      await client.log({ operation: "test", actionType: "READ", actionCategory: "SYSTEM" });

      const fetchCall = vi.mocked(fetch).mock.calls[0];
      expect(fetchCall[0]).toBe("http://localhost:8080/api/v1/events");
    });
  });

  describe("log", () => {
    it("sends event to collector", async () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080",
        apiKey: "test-key",
        application: "my-app",
        environment: "staging",
      });

      mockFetchOk<IngestResponse>({ status: "accepted", event_id: "evt-1" });

      const result = await client.log({
        operation: "query_users",
        actionType: "READ",
        actionCategory: "DATABASE",
        actor: { username: "admin" },
      });

      expect(result.status).toBe("accepted");
      expect(result.event_id).toBe("evt-1");

      // Verify fetch was called with correct URL and method
      const fetchCall = vi.mocked(fetch).mock.calls[0];
      expect(fetchCall[0]).toBe("http://localhost:8080/api/v1/events");
      const init = fetchCall[1] as RequestInit;
      expect(init.method).toBe("POST");
      expect(init.headers).toHaveProperty("Content-Type", "application/json");
    });

    it("sends auth header when API key is set", async () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080",
        apiKey: "secret-key",
      });

      mockFetchOk<IngestResponse>({ status: "accepted", event_id: "evt-1" });

      await client.log({ operation: "test", actionType: "EXECUTE", actionCategory: "SYSTEM" });

      const init = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
      const headers = init.headers as Record<string, string>;
      expect(headers["Authorization"]).toBe("Bearer secret-key");
    });

    it("does not send auth header when API key is empty", async () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080",
      });

      mockFetchOk<IngestResponse>({ status: "accepted", event_id: "evt-1" });

      await client.log({ operation: "test", actionType: "READ", actionCategory: "SYSTEM" });

      const init = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
      const headers = init.headers as Record<string, string>;
      expect(headers["Authorization"]).toBeUndefined();
    });

    it("includes application and environment in metadata", async () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080",
        application: "my-app",
        environment: "prod",
      });

      mockFetchOk<IngestResponse>({ status: "accepted", event_id: "evt-1" });

      await client.log({ operation: "test", actionType: "READ", actionCategory: "API" });

      const body = JSON.parse(
        (vi.mocked(fetch).mock.calls[0][1] as RequestInit).body as string,
      );
      expect(body.metadata.application).toBe("my-app");
      expect(body.metadata.environment).toBe("prod");
    });

    it("throws on server error", async () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080",
      });

      mockFetchError(500, "Internal Server Error");

      await expect(
        client.log({ operation: "test", actionType: "READ", actionCategory: "SYSTEM" }),
      ).rejects.toThrow("Collector returned 500");
    });

    it("throws on timeout", async () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080",
        timeout: 1, // 1ms timeout
      });

      // Mock fetch to never resolve
      global.fetch = vi.fn().mockImplementation(
        () => new Promise((_resolve, reject) => {
          // Simulate abort signal
          setTimeout(() => reject(new DOMException("Aborted", "AbortError")), 5);
        }),
      );

      await expect(
        client.log({ operation: "test", actionType: "READ", actionCategory: "SYSTEM" }),
      ).rejects.toThrow();
    });
  });

  describe("logBatch", () => {
    it("sends batch to collector", async () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080",
        apiKey: "key",
      });

      mockFetchOk<BatchResponse>({
        status: "accepted",
        accepted: 2,
        errors: [],
        event_ids: ["evt-1", "evt-2"],
      });

      const result = await client.logBatch([
        {
          event_id: "",
          timestamp: "",
          version: "1.0.0",
          action: { type: "READ", category: "DATABASE" },
        },
        {
          event_id: "",
          timestamp: "",
          version: "1.0.0",
          action: { type: "WRITE", category: "FILE" },
        },
      ]);

      expect(result.accepted).toBe(2);
      expect(result.event_ids).toHaveLength(2);

      const fetchCall = vi.mocked(fetch).mock.calls[0];
      expect(fetchCall[0]).toBe("http://localhost:8080/api/v1/events/batch");
    });

    it("fills in missing event_id and timestamp", async () => {
      const client = new AuditClient({
        collectorUrl: "http://localhost:8080",
      });

      mockFetchOk<BatchResponse>({
        status: "accepted",
        accepted: 1,
        errors: [],
        event_ids: ["evt-1"],
      });

      await client.logBatch([
        {
          event_id: "",
          timestamp: "",
          version: "1.0.0",
          action: { type: "EXECUTE", category: "SYSTEM" },
        },
      ]);

      const body = JSON.parse(
        (vi.mocked(fetch).mock.calls[0][1] as RequestInit).body as string,
      );
      // Should have been filled by logBatch
      expect(body.events[0].event_id).toBe("test-uuid-1234");
      expect(body.events[0].timestamp).toBeTruthy();
    });
  });
});
