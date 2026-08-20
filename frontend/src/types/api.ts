/**
 * API Type Definitions
 *
 * TypeScript interfaces that match backend Pydantic models.
 * These ensure type safety and prevent frontend-backend contract mismatches.
 *
 * IMPORTANT: Keep these in sync with backend/src/schemas/responses.py
 */

// ============================================================================
// Base Response Types
// ============================================================================

export interface SuccessResponse<T = any> {
  success: true;
  message: string;
  data?: T;
}

export interface ErrorResponse {
  success: false;
  error: string;
  message: string;
  detail?: string;
  field?: string;
}

export interface PaginatedResponse<T> {
  success: true;
  data: T[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// ============================================================================
// User Types
// ============================================================================

export interface UserData {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at?: string;
  last_login?: string;
}

/**
 * Response from POST /api/v1/admin/users/create
 * IMPORTANT: User data is nested under 'user' key
 */
export interface UserCreatedResponse {
  success: true;
  message: string;
  user: UserData; // ← Nested structure!
}

export interface UserDeletedResponse {
  success: true;
  message: string;
  user_id: string;
}

export interface UserUpdatedResponse {
  success: true;
  message: string;
  user: UserData;
}

// ============================================================================
// Expense Types
// ============================================================================

export interface ExpenseData {
  id: string;
  amount: number;
  vendor: string;
  category: string;
  description: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  date: string;
  created_at: string;
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
  user?: {
    id: string;
    username: string;
    email: string;
  };
}

export interface ExpenseCreatedResponse {
  success: true;
  message: string;
  expense?: ExpenseData; // May be at root or nested
  // Actual response structure varies - check backend!
  id?: string;
  amount?: number;
  status?: string;
}

export interface ExpenseApprovedResponse {
  success: true;
  message?: string;
  // Response data at root level (inconsistent with other endpoints)
  id: string;
  amount: number;
  vendor: string;
  status: string;
  approved_by?: string;
  approved_at?: string;
}

// ============================================================================
// Organization Types
// ============================================================================

export interface OrganizationData {
  id: string;
  name: string;
  slug: string;
  description?: string;
  currency: string;
  timezone: string;
  is_active: boolean;
  created_at: string;
}

export interface OrganizationCreatedResponse {
  success: true;
  message: string;
  organization: OrganizationData;
}

// ============================================================================
// Error Types
// ============================================================================

export interface ValidationErrorDetail {
  field: string;
  message: string;
  value?: any;
}

export interface ValidationErrorResponse extends ErrorResponse {
  errors: ValidationErrorDetail[];
}

export interface MissingHeaderError extends ErrorResponse {
  error: "MISSING_REQUIRED_HEADER";
  required_header: string;
}

export interface UnauthorizedResponse extends ErrorResponse {
  error: "UNAUTHORIZED";
}

export interface ForbiddenResponse extends ErrorResponse {
  error: "FORBIDDEN";
}

export interface NotFoundResponse extends ErrorResponse {
  error: "NOT_FOUND";
}

export interface ConflictResponse extends ErrorResponse {
  error: "CONFLICT";
}

export interface PaymentRequiredResponse extends ErrorResponse {
  error: "PAYMENT_REQUIRED";
  upgrade_message?: string;
}

// ============================================================================
// Request Types
// ============================================================================

export interface CreateUserRequest {
  email: string;
  username: string;
  full_name?: string;
  password: string;
  role: "employee" | "admin" | "manager";
  department_id?: string;
}

export interface CreateExpenseRequest {
  amount: number;
  vendor: string;
  category: string;
  description: string;
  date: string;
  payment_method?: string;
  currency?: string;
}

export interface CreateOrganizationRequest {
  name: string;
  slug: string;
  description?: string;
  currency?: string;
  timezone?: string;
}

// ============================================================================
// Type Guards
// ============================================================================

export function isSuccessResponse(response: any): response is SuccessResponse {
  return response && response.success === true;
}

export function isErrorResponse(response: any): response is ErrorResponse {
  return response && response.success === false;
}

export function isUserCreatedResponse(
  response: any,
): response is UserCreatedResponse {
  return (
    isSuccessResponse(response) &&
    "user" in response &&
    typeof response.user === "object"
  );
}

export function isMissingHeaderError(error: any): error is MissingHeaderError {
  return isErrorResponse(error) && error.error === "MISSING_REQUIRED_HEADER";
}

// ============================================================================
// API Response Helpers
// ============================================================================

/**
 * Type-safe wrapper for extracting user data from API response
 * Handles both nested (correct) and root-level (legacy) structures
 */
export function extractUserData(response: UserCreatedResponse | any): UserData {
  if (response.user) {
    return response.user; // Correct nested structure
  }
  // Fallback for legacy flat structure
  return {
    id: response.id,
    username: response.username,
    email: response.email,
    full_name: response.full_name,
    role: response.role,
    is_active: response.is_active,
    is_verified: response.is_verified,
    created_at: response.created_at,
    updated_at: response.updated_at,
    last_login: response.last_login,
  };
}

/**
 * Extract error message from API error response
 */
export function extractErrorMessage(error: any): string {
  if (isErrorResponse(error)) {
    return error.detail || error.message;
  }
  if (error.detail) {
    return typeof error.detail === "string"
      ? error.detail
      : error.detail.message || "An error occurred";
  }
  return error.message || "An unknown error occurred";
}
