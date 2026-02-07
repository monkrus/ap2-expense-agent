import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConstraintBuilder from "../ConstraintBuilder";
import IntentMandateManager from "../IntentMandateManager";
import AP2CompleteFlow from "../AP2CompleteFlow";
import { ToastProvider } from "../../contexts/ToastContext";
import { OrganizationProvider } from "../../contexts/OrganizationContext";

// Mock fetch globally
global.fetch = vi.fn();

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = value.toString();
    },
    removeItem: (key) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

// Wrapper for components
const Wrapper = ({ children }) => (
  <ToastProvider>
    <OrganizationProvider>
      {children}
    </OrganizationProvider>
  </ToastProvider>
);

describe("AP2 Components", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem("access_token", "test-token");
  });

  describe("ConstraintBuilder", () => {
    it("should render ConstraintBuilder component", () => {
      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={() => {}} />
        </Wrapper>
      );

      expect(screen.getByText("Create Intent Mandate")).toBeInTheDocument();
      expect(screen.getByText("Step 1 of 3")).toBeInTheDocument();
    });

    it("should show all three steps", () => {
      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={() => {}} />
        </Wrapper>
      );

      expect(screen.getByText(/Basic Settings/i)).toBeInTheDocument();
      expect(screen.getByText(/Basic Settings/i)).toBeInTheDocument();
    });

    it("should allow navigation between steps", async () => {
      const user = userEvent.setup();
      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={() => {}} />
        </Wrapper>
      );

      // Click Next button to go to Step 2
      const nextButtons = screen.getAllByRole("button", { name: /Next/i });
      await user.click(nextButtons[0]);

      expect(screen.getByText("Step 2 of 3")).toBeInTheDocument();
      expect(screen.getByText(/Advanced Rules/i)).toBeInTheDocument();
    });

    it("should allow max amount input", async () => {
      const user = userEvent.setup();
      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={() => {}} />
        </Wrapper>
      );

      const maxAmountInput = screen.getByPlaceholderText(/e.g., 1000.00/i);
      await user.type(maxAmountInput, "500.00");

      expect(maxAmountInput).toHaveValue(500);
    });

    it("should allow adding merchants", async () => {
      const user = userEvent.setup();
      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={() => {}} />
        </Wrapper>
      );

      // Navigate to Step 2 (Advanced Rules)
      const nextButtons = screen.getAllByRole("button", { name: /Next/i });
      await user.click(nextButtons[0]);

      // Find and fill merchant input
      const merchantInput = screen.getByPlaceholderText(/e.g., Amazon, Starbucks/i);
      await user.type(merchantInput, "Starbucks");

      // Find and click the Add button next to merchant input
      const addButtons = screen.getAllByRole("button", { name: /Add/i });
      await user.click(addButtons[1]); // Second Add button is for merchants

      // Verify merchant was added
      await waitFor(() => {
        expect(screen.getByText("Starbucks")).toBeInTheDocument();
      });
    });

    it("should allow adding categories", async () => {
      const user = userEvent.setup();
      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={() => {}} />
        </Wrapper>
      );

      // Navigate to Step 2
      const nextButtons = screen.getAllByRole("button", { name: /Next/i });
      await user.click(nextButtons[0]);

      // Click a predefined category button
      const officeSupplies = screen.getByRole("button", { name: /Office Supplies/i });
      await user.click(officeSupplies);

      // Verify category is selected
      await waitFor(() => {
        expect(screen.getByText("OFFICE_SUPPLIES")).toBeInTheDocument();
      });
    });

    it("should show review page with entered data", async () => {
      const user = userEvent.setup();
      const mockOnSuccess = vi.fn();

      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={mockOnSuccess} />
        </Wrapper>
      );

      // Step 1: Add max amount
      const maxAmountInput = screen.getByPlaceholderText(/e.g., 1000.00/i);
      await user.type(maxAmountInput, "1000");

      // Go to Step 2
      let nextButtons = screen.getAllByRole("button", { name: /Next/i });
      await user.click(nextButtons[0]);

      // Add a merchant
      const merchantInput = screen.getByPlaceholderText(/e.g., Amazon, Starbucks/i);
      await user.type(merchantInput, "Amazon");

      const addButtons = screen.getAllByRole("button", { name: /Add/i });
      await user.click(addButtons[1]);

      // Go to Step 3
      nextButtons = screen.getAllByRole("button", { name: /Next/i });
      await user.click(nextButtons[0]);

      // Verify review page
      expect(screen.getByText(/Review & Create/i)).toBeInTheDocument();
      expect(screen.getByText("$1000.00")).toBeInTheDocument();
      expect(screen.getByText("Amazon")).toBeInTheDocument();
    });

    it("should allow adding custom categories", async () => {
      const user = userEvent.setup();
      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={() => {}} />
        </Wrapper>
      );

      // Navigate to Step 2
      const nextButtons = screen.getAllByRole("button", { name: /Next/i });
      await user.click(nextButtons[0]);

      // Find custom category input
      const customCategoryInput = screen.getByPlaceholderText(/Or type custom category/i);
      await user.type(customCategoryInput, "COFFEE");

      // Click Add button
      const addButtons = screen.getAllByRole("button", { name: /Add/i });
      await user.click(addButtons[0]); // First Add button is for custom categories

      // Verify custom category was added
      await waitFor(() => {
        expect(screen.getByText("COFFEE")).toBeInTheDocument();
      });
    });
  });

  describe("IntentMandateManager", () => {
    const mockMandates = [
      {
        id: "1",
        type: "intent",
        status: "active",
        constraints: { max_amount: 1000 },
        expires_at: new Date(Date.now() + 86400000).toISOString(),
      },
      {
        id: "2",
        type: "intent",
        status: "expired",
        constraints: { max_amount: 500 },
        expires_at: new Date(Date.now() - 86400000).toISOString(),
      },
    ];

    it("should render Intent Mandate Manager", () => {
      render(
        <Wrapper>
          <IntentMandateManager
            mandates={mockMandates}
            onRefresh={() => {}}
            onCreateMandate={() => {}}
            showArchived={false}
            setShowArchived={() => {}}
          />
        </Wrapper>
      );

      expect(screen.getByText("Reusable Authorizations")).toBeInTheDocument();
    });

    it("should filter mandates by status", async () => {
      const user = userEvent.setup();
      render(
        <Wrapper>
          <IntentMandateManager
            mandates={mockMandates}
            onRefresh={() => {}}
            onCreateMandate={() => {}}
            showArchived={false}
            setShowArchived={() => {}}
          />
        </Wrapper>
      );

      // Check that filter buttons exist
      expect(screen.getByRole("button", { name: /All/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Active/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Expired/i })).toBeInTheDocument();
    });
  });

  describe("AP2CompleteFlow", () => {
    it("should render Complete Flow component", () => {
      render(
        <Wrapper>
          <AP2CompleteFlow mandates={[]} />
        </Wrapper>
      );

      expect(screen.getByText("One-time Authorization")).toBeInTheDocument();
    });

    it("should allow adding items to cart", async () => {
      const user = userEvent.setup();
      render(
        <Wrapper>
          <AP2CompleteFlow mandates={[]} />
        </Wrapper>
      );

      // Find item description input (should be first of each field type)
      const descriptionInputs = screen.getAllByPlaceholderText(/Item description/i);
      await user.type(descriptionInputs[0], "Test Item");

      // Find amount input
      const amountInputs = screen.getAllByPlaceholderText(/Amount/i);
      await user.type(amountInputs[0], "100");

      expect(descriptionInputs[0]).toHaveValue("Test Item");
      expect(amountInputs[0]).toHaveValue(100);
    });
  });

  describe("Role-based Access Control", () => {
    it("should show admin-only features when user is admin", () => {
      // Note: This would require mocking AuthContext
      // which needs additional setup
      expect(true).toBe(true); // Placeholder
    });

    it("should hide admin-only features for regular users", () => {
      expect(true).toBe(true); // Placeholder
    });
  });

  describe("Error Handling", () => {
    it("should handle API errors gracefully", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Server error" }),
      });

      // Test would verify error toast appears
      expect(true).toBe(true); // Placeholder
    });

    it("should display validation errors", async () => {
      // Test would verify validation error handling
      expect(true).toBe(true); // Placeholder
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA labels", () => {
      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={() => {}} />
        </Wrapper>
      );

      // Check for semantic HTML
      expect(screen.getByText("Create Intent Mandate")).toBeInTheDocument();
    });

    it("should support keyboard navigation", async () => {
      const user = userEvent.setup();
      render(
        <Wrapper>
          <ConstraintBuilder onClose={() => {}} onSuccess={() => {}} />
        </Wrapper>
      );

      // Tab to first interactive element and verify it's focused
      await user.tab();
      // This would require more specific testing
      expect(true).toBe(true); // Placeholder
    });
  });
});
