/**
 * Tests for API Error Handler
 * Ensures all errors have status and data properties
 */

import {
  createAPIError,
  isTierLimitError,
  extractTierLimitInfo,
} from "../apiErrorHandler";

describe("API Error Handler", () => {
  describe("createAPIError", () => {
    it("should create error with status and data properties", () => {
      const mockResponse = { status: 402 };
      const mockErrorData = {
        detail: {
          message: "Limit exceeded",
          limit: 1,
          current: 1,
        },
      };

      const error = createAPIError(mockResponse, mockErrorData);

      expect(error).toBeInstanceOf(Error);
      expect(error.status).toBe(402);
      expect(error.data).toEqual(mockErrorData);
      expect(error.message).toBe("Limit exceeded");
    });

    it("should extract message from structured detail object", () => {
      const mockResponse = { status: 402 };
      const mockErrorData = {
        detail: {
          message: "Users limit exceeded",
          upgrade_message: "Upgrade to Starter",
        },
      };

      const error = createAPIError(mockResponse, mockErrorData);

      expect(error.message).toBe("Users limit exceeded");
    });

    it("should extract message from string detail", () => {
      const mockResponse = { status: 400 };
      const mockErrorData = {
        detail: "Validation failed",
      };

      const error = createAPIError(mockResponse, mockErrorData);

      expect(error.message).toBe("Validation failed");
    });

    it("should provide helper methods", () => {
      const mockResponse = { status: 402 };
      const mockErrorData = { detail: { message: "Limit exceeded" } };

      const error = createAPIError(mockResponse, mockErrorData);

      expect(error.is402PaymentRequired()).toBe(true);
      expect(error.is401Unauthorized()).toBe(false);
      expect(error.is403Forbidden()).toBe(false);
    });

    it("should parse new error format with error object (422 validation)", () => {
      const mockResponse = { status: 422 };
      const mockErrorData = {
        error: {
          message: "Request validation failed",
          code: "VALIDATION_ERROR",
          status: 422,
          details: {
            errors: [
              {
                field: "body.slug",
                message: "String should have at least 3 characters",
                type: "string_too_short",
              },
            ],
          },
        },
      };

      const error = createAPIError(mockResponse, mockErrorData);

      expect(error).toBeInstanceOf(Error);
      expect(error.status).toBe(422);
      expect(error.data).toEqual(mockErrorData);
      expect(error.message).toBe("slug: must be at least 3 characters long");
      expect(error.is422ValidationError()).toBe(true);
    });

    it("should parse multiple validation errors", () => {
      const mockResponse = { status: 422 };
      const mockErrorData = {
        error: {
          message: "Request validation failed",
          code: "VALIDATION_ERROR",
          status: 422,
          details: {
            errors: [
              {
                field: "body.slug",
                message: "String should have at least 3 characters",
                type: "string_too_short",
              },
              {
                field: "body.name",
                message: "Field required",
                type: "missing",
              },
            ],
          },
        },
      };

      const error = createAPIError(mockResponse, mockErrorData);

      expect(error.message).toContain("slug:");
      expect(error.message).toContain("name:");
      expect(error.message).toContain(",");
    });

    it("should handle new error format without validation errors", () => {
      const mockResponse = { status: 400 };
      const mockErrorData = {
        error: {
          message: "Invalid request",
          code: "BAD_REQUEST",
          status: 400,
        },
      };

      const error = createAPIError(mockResponse, mockErrorData);

      expect(error.message).toBe("Invalid request");
      expect(error.status).toBe(400);
    });
  });

  describe("isTierLimitError", () => {
    it("should return true for 402 errors", () => {
      const error = new Error("Limit exceeded");
      error.status = 402;

      expect(isTierLimitError(error)).toBe(true);
    });

    it("should return false for non-402 errors", () => {
      const error = new Error("Not found");
      error.status = 404;

      expect(isTierLimitError(error)).toBe(false);
    });

    it("should return false for errors without status", () => {
      const error = new Error("Some error");

      expect(isTierLimitError(error)).toBe(false);
    });
  });

  describe("extractTierLimitInfo", () => {
    it("should extract tier info from 402 error", () => {
      const error = new Error("Limit exceeded");
      error.status = 402;
      error.data = {
        detail: {
          message: "Users limit exceeded: 1/1",
          current_tier: "free",
          limit: 1,
          current: 1,
          upgrade_options: { next_tier: "Starter" },
        },
      };

      const tierInfo = extractTierLimitInfo(error);

      expect(tierInfo).toEqual({
        currentTier: "free",
        currentLimit: 1,
        currentCount: 1,
        message: "Users limit exceeded: 1/1",
        upgradeOptions: { next_tier: "Starter" },
      });
    });

    it("should return null for non-402 errors", () => {
      const error = new Error("Not found");
      error.status = 404;

      expect(extractTierLimitInfo(error)).toBeNull();
    });

    it("should use defaults when data is missing", () => {
      const error = new Error("Limit exceeded");
      error.status = 402;
      error.data = {};

      const tierInfo = extractTierLimitInfo(error);

      expect(tierInfo.currentTier).toBe("Free");
      expect(tierInfo.currentLimit).toBe(1);
      expect(tierInfo.upgradeOptions).toEqual({ next_tier: "Starter" });
    });
  });
});
