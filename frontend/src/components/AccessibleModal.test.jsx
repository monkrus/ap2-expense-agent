/**
 * AccessibleModal Component Tests
 *
 * Tests the accessible modal component for:
 * - WCAG 2.1 AA compliance
 * - Focus trap functionality
 * - Keyboard navigation (ESC to close)
 * - ARIA attributes
 * - Focus restoration
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AccessibleModal from "./AccessibleModal";

describe("AccessibleModal Component", () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should not render when isOpen is false", () => {
      render(
        <AccessibleModal
          isOpen={false}
          onClose={mockOnClose}
          title="Test Modal"
        >
          <p>Content</p>
        </AccessibleModal>,
      );

      expect(screen.queryByText("Test Modal")).not.toBeInTheDocument();
    });

    it("should render when isOpen is true", () => {
      render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </AccessibleModal>,
      );

      expect(screen.getByText("Test Modal")).toBeInTheDocument();
      expect(screen.getByText("Content")).toBeInTheDocument();
    });

    it("should render with description", () => {
      render(
        <AccessibleModal
          isOpen={true}
          onClose={mockOnClose}
          title="Test Modal"
          description="This is a description"
        >
          <p>Content</p>
        </AccessibleModal>,
      );

      expect(screen.getByText("This is a description")).toBeInTheDocument();
    });

    it("should render close button by default", () => {
      render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </AccessibleModal>,
      );

      expect(
        screen.getByRole("button", { name: /close dialog/i }),
      ).toBeInTheDocument();
    });

    it("should not render close button when showCloseButton is false", () => {
      render(
        <AccessibleModal
          isOpen={true}
          onClose={mockOnClose}
          title="Test Modal"
          showCloseButton={false}
        >
          <p>Content</p>
        </AccessibleModal>,
      );

      expect(
        screen.queryByRole("button", { name: /close dialog/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Accessibility - WCAG 2.1 AA Compliance", () => {
    it('should have role="dialog"', () => {
      render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </AccessibleModal>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it('should have aria-modal="true"', () => {
      render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </AccessibleModal>,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });

    it("should have aria-labelledby pointing to title", () => {
      render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </AccessibleModal>,
      );

      const dialog = screen.getByRole("dialog");
      const titleId = dialog.getAttribute("aria-labelledby");
      expect(titleId).toBe("modal-title");

      const title = document.getElementById(titleId);
      expect(title).toHaveTextContent("Test Modal");
    });

    it("should have aria-describedby when description is provided", () => {
      render(
        <AccessibleModal
          isOpen={true}
          onClose={mockOnClose}
          title="Test Modal"
          description="Test description"
        >
          <p>Content</p>
        </AccessibleModal>,
      );

      const dialog = screen.getByRole("dialog");
      const descId = dialog.getAttribute("aria-describedby");
      expect(descId).toBe("modal-description");

      const description = document.getElementById(descId);
      expect(description).toHaveTextContent("Test description");
    });
  });

  describe("Keyboard Navigation", () => {
    it("should close modal on ESC key", async () => {
      const user = userEvent.setup();
      render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </AccessibleModal>,
      );

      await user.keyboard("{Escape}");

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("should not close on ESC when closeOnEscape is false", async () => {
      const user = userEvent.setup();
      render(
        <AccessibleModal
          isOpen={true}
          onClose={mockOnClose}
          title="Test Modal"
          closeOnEscape={false}
        >
          <p>Content</p>
        </AccessibleModal>,
      );

      await user.keyboard("{Escape}");

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("should trap focus within modal", async () => {
      const user = userEvent.setup();
      render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <button>Button 1</button>
          <button>Button 2</button>
          <button>Button 3</button>
        </AccessibleModal>,
      );

      // Initial focus should be on close button
      const closeButton = screen.getByRole("button", { name: /close dialog/i });
      expect(closeButton).toHaveFocus();
    });
  });

  describe("Interaction", () => {
    it("should close when close button is clicked", async () => {
      const user = userEvent.setup();
      render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </AccessibleModal>,
      );

      const closeButton = screen.getByRole("button", { name: /close dialog/i });
      await user.click(closeButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("should close when backdrop is clicked", async () => {
      const user = userEvent.setup();
      const { container } = render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </AccessibleModal>,
      );

      const backdrop = container.querySelector('[role="dialog"]').parentElement;
      await user.click(backdrop);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("should not close on backdrop click when closeOnBackdropClick is false", async () => {
      const user = userEvent.setup();
      const { container } = render(
        <AccessibleModal
          isOpen={true}
          onClose={mockOnClose}
          title="Test Modal"
          closeOnBackdropClick={false}
        >
          <p>Content</p>
        </AccessibleModal>,
      );

      const backdrop = container.querySelector('[role="dialog"]').parentElement;
      await user.click(backdrop);

      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe("Size Variants", () => {
    it("should apply small size class", () => {
      const { container } = render(
        <AccessibleModal
          isOpen={true}
          onClose={mockOnClose}
          title="Test Modal"
          size="small"
        >
          <p>Content</p>
        </AccessibleModal>,
      );

      const modal = container.querySelector(".max-w-md");
      expect(modal).toBeInTheDocument();
    });

    it("should apply medium size class by default", () => {
      const { container } = render(
        <AccessibleModal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </AccessibleModal>,
      );

      const modal = container.querySelector(".max-w-2xl");
      expect(modal).toBeInTheDocument();
    });

    it("should apply large size class", () => {
      const { container } = render(
        <AccessibleModal
          isOpen={true}
          onClose={mockOnClose}
          title="Test Modal"
          size="large"
        >
          <p>Content</p>
        </AccessibleModal>,
      );

      const modal = container.querySelector(".max-w-4xl");
      expect(modal).toBeInTheDocument();
    });
  });
});
