package audit

import (
	"strings"
	"testing"
)

func TestValidateEvent_Valid(t *testing.T) {
	e := &AuditEvent{
		Action: ActionContext{
			Type:      "READ",
			Category:  "DATABASE",
			Operation: "query_users",
		},
	}
	if err := ValidateEvent(e); err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
}

func TestValidateEvent_ValidLowerCase(t *testing.T) {
	e := &AuditEvent{
		Action: ActionContext{
			Type:      "read",
			Category:  "database",
			Operation: "query_users",
		},
	}
	if err := ValidateEvent(e); err != nil {
		t.Fatalf("expected no error for lowercase input, got: %v", err)
	}
}

func TestValidateEvent_InvalidActionType(t *testing.T) {
	e := &AuditEvent{
		Action: ActionContext{
			Type:      "INVALID_TYPE",
			Category:  "DATABASE",
			Operation: "test",
		},
	}
	err := ValidateEvent(e)
	if err == nil {
		t.Fatal("expected error for invalid action type")
	}
	if !strings.Contains(err.Error(), "invalid action type") {
		t.Fatalf("expected 'invalid action type' in error, got: %v", err)
	}
}

func TestValidateEvent_InvalidCategory(t *testing.T) {
	e := &AuditEvent{
		Action: ActionContext{
			Type:      "READ",
			Category:  "INVALID_CATEGORY",
			Operation: "test",
		},
	}
	err := ValidateEvent(e)
	if err == nil {
		t.Fatal("expected error for invalid category")
	}
	if !strings.Contains(err.Error(), "invalid category") {
		t.Fatalf("expected 'invalid category' in error, got: %v", err)
	}
}

func TestValidateEvent_EmptyOperation(t *testing.T) {
	e := &AuditEvent{
		Action: ActionContext{
			Type:     "READ",
			Category: "DATABASE",
		},
	}
	err := ValidateEvent(e)
	if err == nil {
		t.Fatal("expected error for empty operation")
	}
	if !strings.Contains(err.Error(), "operation must not be empty") {
		t.Fatalf("expected 'operation must not be empty' in error, got: %v", err)
	}
}

func TestValidateEvent_WhitespaceOperation(t *testing.T) {
	e := &AuditEvent{
		Action: ActionContext{
			Type:      "READ",
			Category:  "DATABASE",
			Operation: "   ",
		},
	}
	err := ValidateEvent(e)
	if err == nil {
		t.Fatal("expected error for whitespace-only operation")
	}
}

func TestValidateEvent_AllActionTypes(t *testing.T) {
	types := []string{
		"READ", "WRITE", "UPDATE", "DELETE", "EXECUTE", "CREATE",
		"LOGIN", "LOGOUT", "ACCESS", "MODIFY", "GRANT", "REVOKE",
		"APPROVE", "REJECT",
	}
	for _, at := range types {
		e := &AuditEvent{
			Action: ActionContext{
				Type:      at,
				Category:  "SYSTEM",
				Operation: "test",
			},
		}
		if err := ValidateEvent(e); err != nil {
			t.Errorf("expected %q to be valid, got: %v", at, err)
		}
	}
}

func TestValidateEvent_AllCategories(t *testing.T) {
	categories := []string{
		"DATABASE", "API", "AUTH", "FILE", "SYSTEM",
		"NETWORK", "SECURITY", "COMPLIANCE", "USER", "ADMIN",
	}
	for _, cat := range categories {
		e := &AuditEvent{
			Action: ActionContext{
				Type:      "EXECUTE",
				Category:  cat,
				Operation: "test",
			},
		}
		if err := ValidateEvent(e); err != nil {
			t.Errorf("expected %q to be valid, got: %v", cat, err)
		}
	}
}
