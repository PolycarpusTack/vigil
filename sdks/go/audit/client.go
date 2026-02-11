package audit

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
)

// Client sends audit events to the collector service.
type Client struct {
	baseURL     string
	apiKey      string
	application string
	environment string
	httpClient  *http.Client
}

// ClientOption configures a Client.
type ClientOption func(*Client)

// WithAPIKey sets the Bearer token for authentication.
func WithAPIKey(key string) ClientOption {
	return func(c *Client) { c.apiKey = key }
}

// WithApplication sets the default application name in event metadata.
func WithApplication(app string) ClientOption {
	return func(c *Client) { c.application = app }
}

// WithEnvironment sets the default environment in event metadata.
func WithEnvironment(env string) ClientOption {
	return func(c *Client) { c.environment = env }
}

// WithTimeout sets the HTTP client timeout.
func WithTimeout(d time.Duration) ClientOption {
	return func(c *Client) { c.httpClient.Timeout = d }
}

// NewClient creates a new audit SDK client.
func NewClient(collectorURL string, opts ...ClientOption) *Client {
	c := &Client{
		baseURL:    strings.TrimRight(collectorURL, "/"),
		httpClient: &http.Client{Timeout: 10 * time.Second},
	}
	for _, opt := range opts {
		opt(c)
	}
	return c
}

// Log sends a single audit event. Fields are populated with defaults if empty.
// The event is validated before sending; invalid events return an error without
// making an HTTP call.
func (c *Client) Log(event AuditEvent) (*IngestResponse, error) {
	c.fillDefaults(&event)

	if err := ValidateEvent(&event); err != nil {
		return nil, fmt.Errorf("validate event: %w", err)
	}

	body, err := json.Marshal(event)
	if err != nil {
		return nil, fmt.Errorf("marshal event: %w", err)
	}

	resp, err := c.doPost("/api/v1/events", body)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result IngestResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	return &result, nil
}

// LogBatch sends multiple audit events in a single request (up to 100).
// All events are validated before sending.
func (c *Client) LogBatch(events []AuditEvent) (*BatchResponse, error) {
	for i := range events {
		c.fillDefaults(&events[i])
		if err := ValidateEvent(&events[i]); err != nil {
			return nil, fmt.Errorf("validate event[%d]: %w", i, err)
		}
	}

	batch := BatchRequest{Events: events}
	body, err := json.Marshal(batch)
	if err != nil {
		return nil, fmt.Errorf("marshal batch: %w", err)
	}

	resp, err := c.doPost("/api/v1/events/batch", body)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result BatchResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	return &result, nil
}

func (c *Client) fillDefaults(e *AuditEvent) {
	if e.EventID == "" {
		e.EventID = uuid.New().String()
	}
	if e.Timestamp == "" {
		e.Timestamp = time.Now().UTC().Format(time.RFC3339Nano)
	}
	if e.Version == "" {
		e.Version = "1.0.0"
	}
	if e.Metadata == nil {
		e.Metadata = make(map[string]interface{})
	}
	if c.application != "" {
		if _, ok := e.Metadata["application"]; !ok {
			e.Metadata["application"] = c.application
		}
	}
	if c.environment != "" {
		if _, ok := e.Metadata["environment"]; !ok {
			e.Metadata["environment"] = c.environment
		}
	}
}

func (c *Client) doPost(path string, body []byte) (*http.Response, error) {
	url := c.baseURL + path
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if c.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.apiKey)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("send request to %s: %w", url, err)
	}

	if resp.StatusCode >= 400 {
		defer resp.Body.Close()
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("collector returned %d: %s", resp.StatusCode, string(respBody))
	}

	return resp, nil
}
