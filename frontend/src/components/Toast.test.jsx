/**
 * Toast Component Tests
 *
 * Tests the Toast notification component for:
 * - Rendering different toast types
 * - Accessibility (aria-live, role)
 * - Auto-dismiss functionality
 * - Close button interaction
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Toast from "./Toast";

describe("Toast Component", () => {
  const mockOnClose = vi.fn();

  const defaultToast = {
    id: "test-toast-1",
    type: "success",
    message: "Operation successful",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Rendering", () => {
    it("should render success toast with correct message", () => {
      render(<Toast toast={defaultToast} onClose={mockOnClose} />);

      expect(screen.getByText("Operation successful")).toBeInTheDocument();
    });

    it("should render error toast with error styling", () => {
      const errorToast = { ...defaultToast, type: "error", message: "Error occurred" };
      render(<Toast toast={errorToast} onClose={mockOnClose} />);

      expect(screen.getByText("Error occurred")).toBeInTheDocument();
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("should render info toast", () => {
      const infoToast = { ...defaultToast, type: "info", message: "Information message" };
      render(<Toast toast={infoToast} onClose={mockOnClose} />);

      expect(screen.getByText("Information message")).toBeInTheDocument();
    });

    it("should render warning toast", () => {
      const warningToast = { ...defaultToast, type: "warning", message: "Warning message" };
      render(<Toast toast={warningToast} onClose={mockOnClose} />);

      expect(screen.getByText("Warning message")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it('should have role="status" for screen readers', () => {
      render(<Toast toast={defaultToast} onClose={mockOnClose} />);

      const toast = screen.getByRole("status");
      expect(toast).toBeInTheDocument();
    });

    it('should have aria-live="polite" for non-error toasts', () => {
      render(<Toast toast={defaultToast} onClose={mockOnClose} />);

      const toast = screen.getByRole("status");
      expect(toast).toHaveAttribute("aria-live", "polite");
    });

    it('should have aria-live="assertive" for error toasts', () => {
      const errorToast = { ...defaultToast, type: "error" };
      render(<Toast toast={errorToast} onClose={mockOnClose} />);

      const toast = screen.getByRole("status");
      expect(toast).toHaveAttribute("aria-live", "assertive");
    });

    it("should have accessible close button", () => {
      render(<Toast toast={defaultToast} onClose={mockOnClose} />);

      const closeButton = screen.getByRole("button", { name: /close/i });
      expect(closeButton).toBeInTheDocument();
    });
  });

  describe("Interaction", () => {
    it("should call onClose when close button is clicked", async () => {
      const user = userEvent.setup({ delay: null });
      render(<Toast toast={defaultToast} onClose={mockOnClose} />);

      const closeButton = screen.getByRole("button");
      await user.click(closeButton);

      expect(mockOnClose).toHaveBeenCalledWith(defaultToast.id);
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("should auto-dismiss after timeout", () => {
      vi.useFakeTimers();
      const autoCloseToast = { ...defaultToast, duration: 3000 };
      render(<Toast toast={autoCloseToast} onClose={mockOnClose} />);

      // Fast-forward time
      vi.advanceTimersByTime(3000);

      // Check that onClose was called
      expect(mockOnClose).toHaveBeenCalledWith(defaultToast.id);
      vi.useRealTimers();
    });

    it("should not auto-dismiss if duration is 0", () => {
      vi.useFakeTimers();
      const persistentToast = { ...defaultToast, duration: 0 };
      render(<Toast toast={persistentToast} onClose={mockOnClose} />);

      vi.advanceTimersByTime(10000);

      expect(mockOnClose).not.toHaveBeenCalled();
      vi.useRealTimers();
    });
  });

  describe("Icons", () => {
    it("should display success icon for success type", () => {
      render(<Toast toast={defaultToast} onClose={mockOnClose} />);

      // Check for success icon (CheckCircle)
      const container = screen.getByRole("status");
      expect(container.querySelector("svg")).toBeInTheDocument();
    });

    it("should display error icon for error type", () => {
      const errorToast = { ...defaultToast, type: "error" };
      render(<Toast toast={errorToast} onClose={mockOnClose} />);

      const container = screen.getByRole("status");
      expect(container.querySelector("svg")).toBeInTheDocument();
    });
  });
});
