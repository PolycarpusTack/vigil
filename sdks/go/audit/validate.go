package audit

import (
	"fmt"
	"strings"
)

// Valid action types matching the Python ActionType enum.
var validActionTypes = map[string]bool{
	"READ":    true,
	"WRITE":   true,
	"UPDATE":  true,
	"DELETE":  true,
	"EXECUTE": true,
	"CREATE":  true,
	"LOGIN":   true,
	"LOGOUT":  true,
	"ACCESS":  true,
	"MODIFY":  true,
	"GRANT":   true,
	"REVOKE":  true,
	"APPROVE": true,
	"REJECT":  true,
}

// Valid action categories matching the Python ActionCategory enum.
var validCategories = map[string]bool{
	"DATABASE":   true,
	"API":        true,
	"AUTH":       true,
	"FILE":       true,
	"SYSTEM":     true,
	"NETWORK":    true,
	"SECURITY":   true,
	"COMPLIANCE": true,
	"USER":       true,
	"ADMIN":      true,
}

// ValidateEvent checks that the event has valid action type, category,
// and a non-empty operation. Returns nil if valid.
func ValidateEvent(e *AuditEvent) error {
	actionType := strings.ToUpper(e.Action.Type)
	if !validActionTypes[actionType] {
		return fmt.Errorf("invalid action type %q: must be one of READ, WRITE, UPDATE, DELETE, EXECUTE, CREATE, LOGIN, LOGOUT, ACCESS, MODIFY, GRANT, REVOKE, APPROVE, REJECT", e.Action.Type)
	}

	category := strings.ToUpper(e.Action.Category)
	if !validCategories[category] {
		return fmt.Errorf("invalid category %q: must be one of DATABASE, API, AUTH, FILE, SYSTEM, NETWORK, SECURITY, COMPLIANCE, USER, ADMIN", e.Action.Category)
	}

	if strings.TrimSpace(e.Action.Operation) == "" {
		return fmt.Errorf("action operation must not be empty")
	}

	return nil
}
