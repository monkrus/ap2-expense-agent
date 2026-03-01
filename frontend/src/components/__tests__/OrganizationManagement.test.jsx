/**
 * Comprehensive Organization Management Frontend Tests
 *
 * Tests:
 * - Organization creation with validation
 * - Error message display
 * - Free tier limit handling
 * - Delete and edit flows
 */

import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import OrganizationManagement from "../OrganizationManagement";
import { AuthContext } from "../../contexts/AuthContext";
import organizationAPI from "../../services/organizationAPI";

// Mock the API
vi.mock("../../services/organizationAPI");

// Mock toast hook
const mockSuccess = vi.fn();
const mockError = vi.fn();
vi.mock("../../hooks/useToast", () => ({
  useToast: () => ({
    success: mockSuccess,
    error: mockError,
    toasts: [],
    removeToast: vi.fn()
  })
}));

describe("OrganizationManagement", () => {
  const mockUser = {
    id: "1",
    username: "testuser",
    role: "admin",
    email: "test@example.com"
  };

  const mockAuthContext = {
    user: mockUser,
    accessToken: "fake-token",
    logout: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    organizationAPI.listOrganizations.mockResolvedValue([]);
    organizationAPI.listMembers.mockResolvedValue([]);
    organizationAPI.listInvitations.mockResolvedValue([]);
    organizationAPI.getCurrentOrganizationId.mockReturnValue(null);
    organizationAPI.setCurrentOrganizationId.mockImplementation(() => {});
    organizationAPI.checkNameAvailability.mockResolvedValue({ available: true, message: "Name is available" });
    organizationAPI.checkSlugAvailability.mockResolvedValue({ available: true, message: "Slug is available" });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Organization Creation", () => {
    test("shows validation error for short slug", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      // Wait for component to load
      await waitFor(() => {
        expect(organizationAPI.listOrganizations).toHaveBeenCalled();
      });

      // Click "Create Your First Organization" button
      const createButton = screen.getByRole("button", { name: /create.*organization/i });
      await user.click(createButton);

      // Fill in form
      const nameInput = screen.getByLabelText(/organization name/i);
      const slugInput = screen.getByLabelText(/organization id/i);

      await user.type(nameInput, "Test Org");
      await user.clear(slugInput);
      await user.type(slugInput, "ab");

      // Advance timers to complete debounced validation
      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      // Wait for validation to resolve (button becomes enabled)
      await waitFor(() => {
        const submitBtn = screen.getByRole("button", { name: /^create organization$/i });
        expect(submitBtn).not.toBeDisabled();
      });

      // Mock API error for validation
      const validationError = new Error("slug: must be at least 3 characters long");
      validationError.status = 422;
      validationError.data = {
        detail: [{
          loc: ["body", "slug"],
          msg: "String should have at least 3 characters",
          type: "string_too_short"
        }]
      };
      organizationAPI.createOrganization.mockRejectedValue(validationError);

      // Submit form
      const submitButton = screen.getByRole("button", { name: /^create organization$/i });
      await user.click(submitButton);

      // Verify error is shown
      await waitFor(() => {
        expect(mockError).toHaveBeenCalledWith(
          expect.stringContaining("slug")
        );
      });
    });

    test("shows free tier limit error with upgrade prompt", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      // Mock organization already exists
      organizationAPI.listOrganizations.mockResolvedValue([
        { id: "1", name: "Existing Org", slug: "existing", currency: "USD", timezone: "UTC", max_members: 5 }
      ]);

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(organizationAPI.listOrganizations).toHaveBeenCalled();
      });

      // When orgs exist, the header shows "Create Organization" button
      const createButton = await screen.findByRole("button", { name: /create organization/i });
      await user.click(createButton);

      // Fill form
      const nameInput = screen.getByLabelText(/organization name/i);
      const slugInput = screen.getByLabelText(/organization id/i);

      await user.type(nameInput, "Second Org");
      await user.clear(slugInput);
      await user.type(slugInput, "second-org");

      // Advance timers for debounced validation
      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      await waitFor(() => {
        const btns = screen.getAllByRole("button", { name: /^create organization$/i });
        // The last one is the modal submit button
        expect(btns[btns.length - 1]).not.toBeDisabled();
      });

      // Mock 402 error (tier limit)
      const limitError = new Error("You've reached your Free plan's limit of 1 organization");
      limitError.status = 402;
      limitError.data = {
        error: "limit_exceeded",
        feature: "Organizations",
        current_tier: "Free",
        current_limit: 1,
        current_count: 1,
        message: "You've reached your Free plan's limit of 1 organization",
        upgrade_message: "Upgrade to Starter ($29/month) to create up to 3 organizations",
        upgrade_options: [
          { tier: "Starter", price: "$29/month", organizations: 3 }
        ]
      };
      organizationAPI.createOrganization.mockRejectedValue(limitError);

      // Submit - use the modal's submit button (last matching button)
      const submitButtons = screen.getAllByRole("button", { name: /^create organization$/i });
      await user.click(submitButtons[submitButtons.length - 1]);

      // Verify upgrade prompt is shown
      await waitFor(() => {
        expect(screen.getByText(/upgrade/i)).toBeInTheDocument();
      });
    });

    test("creates organization successfully", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      organizationAPI.createOrganization.mockResolvedValue({
        id: "123",
        name: "New Org",
        slug: "new-org",
        is_active: true,
        currency: "USD",
        timezone: "UTC",
        max_members: 5
      });

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(organizationAPI.listOrganizations).toHaveBeenCalled();
      });

      // Click create button
      const createButton = screen.getByRole("button", { name: /create.*organization/i });
      await user.click(createButton);

      // Fill form
      const nameInput = screen.getByLabelText(/organization name/i);
      const slugInput = screen.getByLabelText(/organization id/i);

      await user.type(nameInput, "New Org");
      await user.clear(slugInput);
      await user.type(slugInput, "new-org");

      // Advance timers for debounced validation
      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      await waitFor(() => {
        const submitBtn = screen.getByRole("button", { name: /^create organization$/i });
        expect(submitBtn).not.toBeDisabled();
      });

      // Submit
      const submitButton = screen.getByRole("button", { name: /^create organization$/i });
      await user.click(submitButton);

      // Verify success
      await waitFor(() => {
        expect(organizationAPI.createOrganization).toHaveBeenCalledWith({
          name: "New Org",
          slug: "new-org",
          description: "",
          currency: "USD",
          timezone: "UTC"
        });
        expect(mockSuccess).toHaveBeenCalledWith(
          expect.stringContaining("New Org")
        );
      });
    });
  });

  describe("Organization Deletion", () => {
    test("deletes organization successfully", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      const mockOrg = {
        id: "123",
        name: "Test Org",
        slug: "test-org",
        is_active: true,
        currency: "USD",
        timezone: "UTC",
        max_members: 5
      };

      organizationAPI.listOrganizations
        .mockResolvedValueOnce([mockOrg])  // Initial load
        .mockResolvedValueOnce([]);        // After deletion

      organizationAPI.deleteOrganization.mockResolvedValue();

      // Mock window.prompt to return the slug for confirmation
      const promptSpy = vi.spyOn(window, "prompt").mockReturnValue("test-org");
      // Mock window.alert to prevent errors from the post-delete alert
      const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(screen.getAllByText("Test Org").length).toBeGreaterThanOrEqual(1);
      });

      // Navigate to Settings tab where the delete button is
      const settingsTab = screen.getByText("Settings");
      await user.click(settingsTab);

      // Click delete button
      const deleteButton = screen.getByTestId("delete-org-123");
      await user.click(deleteButton);

      // Advance timers for the setTimeout in handleDeleteOrg
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      // Verify deletion (prompt is auto-answered by the mock)
      await waitFor(() => {
        expect(organizationAPI.deleteOrganization).toHaveBeenCalledWith("123");
        expect(mockSuccess).toHaveBeenCalled();
      });

      // Cleanup
      promptSpy.mockRestore();
      alertSpy.mockRestore();
    });
  });

  describe("Organization Editing", () => {
    test("updates organization successfully", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      const mockOrg = {
        id: "123",
        name: "Original Name",
        slug: "original",
        description: "Original description",
        is_active: true,
        currency: "USD",
        timezone: "UTC",
        max_members: 5
      };

      organizationAPI.listOrganizations.mockResolvedValue([mockOrg]);
      organizationAPI.updateOrganization.mockResolvedValue({
        ...mockOrg,
        name: "Updated Name",
        description: "Updated description"
      });

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(screen.getAllByText("Original Name").length).toBeGreaterThanOrEqual(1);
      });

      // Navigate to Settings tab where the Edit button lives
      const settingsTab = screen.getByText("Settings");
      await user.click(settingsTab);

      // Click edit button
      const editButton = screen.getByTestId("edit-org-123");
      await user.click(editButton);

      // Update name - the edit modal has its own labeled input
      const nameInput = screen.getByLabelText(/organization name/i);
      await user.clear(nameInput);
      await user.type(nameInput, "Updated Name");

      // Submit
      const saveButton = screen.getByText(/save/i);
      await user.click(saveButton);

      // Verify update
      await waitFor(() => {
        expect(organizationAPI.updateOrganization).toHaveBeenCalledWith(
          "123",
          expect.objectContaining({
            name: "Updated Name"
          })
        );
        expect(mockSuccess).toHaveBeenCalled();
      });
    });
  });

  describe("Real-time Validation", () => {
    test("checks slug availability in real-time", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      organizationAPI.checkSlugAvailability.mockResolvedValue({
        available: true,
        message: "Slug is available"
      });

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(organizationAPI.listOrganizations).toHaveBeenCalled();
      });

      // Click create
      const createButton = screen.getByRole("button", { name: /create.*organization/i });
      await user.click(createButton);

      // Type slug
      const slugInput = screen.getByLabelText(/organization id/i);
      await user.clear(slugInput);
      await user.type(slugInput, "test-slug");

      // Advance timers for debounced validation
      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      // Wait for validation to resolve
      await waitFor(() => {
        expect(organizationAPI.checkSlugAvailability).toHaveBeenCalledWith("test-slug");
      });

      // Verify availability indicator
      expect(screen.getByText(/slug is available/i)).toBeInTheDocument();
    });

    test("shows slug unavailable message", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      organizationAPI.checkSlugAvailability.mockResolvedValue({
        available: false,
        message: "Slug is already taken",
        suggestions: ["test-slug-1", "test-slug-2"]
      });

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(organizationAPI.listOrganizations).toHaveBeenCalled();
      });

      const createButton = screen.getByRole("button", { name: /create.*organization/i });
      await user.click(createButton);

      const slugInput = screen.getByLabelText(/organization id/i);
      await user.clear(slugInput);
      await user.type(slugInput, "taken-slug");

      // Advance timers for debounced validation
      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      await waitFor(() => {
        expect(screen.getByText(/already taken/i)).toBeInTheDocument();
      });

      // Verify suggestions are shown
      expect(screen.getByText(/test-slug-1/)).toBeInTheDocument();
    });
  });
});
