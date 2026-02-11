// Package audit provides a Go SDK for the Vigil collector service.
package audit

// AuditEvent matches schema/audit_event.schema.json.
type AuditEvent struct {
	EventID     string                 `json:"event_id"`
	Timestamp   string                 `json:"timestamp"`
	Version     string                 `json:"version"`
	Session     *SessionContext        `json:"session,omitempty"`
	Actor       *ActorContext          `json:"actor,omitempty"`
	Action      ActionContext          `json:"action"`
	Performance *PerformanceMetrics    `json:"performance,omitempty"`
	Error       *ErrorInfo             `json:"error,omitempty"`
	System      map[string]interface{} `json:"system,omitempty"`
	Custom      map[string]interface{} `json:"custom,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// SessionContext holds session identifiers.
type SessionContext struct {
	SessionID     string `json:"session_id,omitempty"`
	RequestID     string `json:"request_id,omitempty"`
	CorrelationID string `json:"correlation_id,omitempty"`
}

// ActorContext identifies who performed the action.
type ActorContext struct {
	Type      string   `json:"type,omitempty"`
	ID        string   `json:"id,omitempty"`
	Username  string   `json:"username,omitempty"`
	Email     string   `json:"email,omitempty"`
	Roles     []string `json:"roles,omitempty"`
	IPAddress string   `json:"ip_address,omitempty"`
	UserAgent string   `json:"user_agent,omitempty"`
}

// ResourceInfo describes the target resource.
type ResourceInfo struct {
	Type string `json:"type,omitempty"`
	ID   string `json:"id,omitempty"`
	Name string `json:"name,omitempty"`
	Path string `json:"path,omitempty"`
}

// ActionResult holds the outcome of the action.
type ActionResult struct {
	Status        string `json:"status,omitempty"`
	Code          string `json:"code,omitempty"`
	Message       string `json:"message,omitempty"`
	RowsAffected  *int   `json:"rows_affected,omitempty"`
	DataSizeBytes *int   `json:"data_size_bytes,omitempty"`
}

// ActionContext describes what was done.
type ActionContext struct {
	Type        string                 `json:"type"`
	Category    string                 `json:"category"`
	Operation   string                 `json:"operation,omitempty"`
	Description string                 `json:"description,omitempty"`
	Resource    *ResourceInfo          `json:"resource,omitempty"`
	Parameters  map[string]interface{} `json:"parameters,omitempty"`
	Result      *ActionResult          `json:"result,omitempty"`
}

// PerformanceMetrics holds timing and resource usage data.
type PerformanceMetrics struct {
	DurationMS        *float64 `json:"duration_ms,omitempty"`
	CPUTimeMS         *float64 `json:"cpu_time_ms,omitempty"`
	MemoryMB          *float64 `json:"memory_mb,omitempty"`
	SlowQuery         bool     `json:"slow_query,omitempty"`
	ThresholdExceeded bool     `json:"threshold_exceeded,omitempty"`
}

// ErrorInfo holds error details.
type ErrorInfo struct {
	Occurred   bool   `json:"occurred,omitempty"`
	Type       string `json:"type,omitempty"`
	Message    string `json:"message,omitempty"`
	StackTrace string `json:"stack_trace,omitempty"`
	Handled    bool   `json:"handled,omitempty"`
}

// BatchRequest wraps multiple events for the batch endpoint.
type BatchRequest struct {
	Events []AuditEvent `json:"events"`
}

// IngestResponse is returned by the single-event endpoint.
type IngestResponse struct {
	Status  string `json:"status"`
	EventID string `json:"event_id"`
}

// BatchResponse is returned by the batch endpoint.
type BatchResponse struct {
	Status   string        `json:"status"`
	Accepted int           `json:"accepted"`
	Errors   []BatchError  `json:"errors"`
	EventIDs []string      `json:"event_ids"`
}

// BatchError reports a failed event in a batch.
type BatchError struct {
	Index int    `json:"index"`
	Error string `json:"error"`
}
