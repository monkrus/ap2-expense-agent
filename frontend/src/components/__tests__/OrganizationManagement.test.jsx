/**
 * Comprehensive Organization Management Frontend Tests
 *
 * Tests:
 * - Organization creation with validation
 * - Error message display
 * - Free tier limit handling
 * - Delete and edit flows
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import OrganizationManagement from '../OrganizationManagement';
import { AuthContext } from '../../contexts/AuthContext';
import organizationAPI from '../../services/organizationAPI';

// Mock the API
vi.mock('../../services/organizationAPI');

// Mock toast hook
const mockSuccess = vi.fn();
const mockError = vi.fn();
vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({
    success: mockSuccess,
    error: mockError,
    toasts: [],
    removeToast: vi.fn()
  })
}));

describe('OrganizationManagement', () => {
  const mockUser = {
    id: '1',
    username: 'testuser',
    role: 'admin',
    email: 'test@example.com'
  };

  const mockAuthContext = {
    user: mockUser,
    accessToken: 'fake-token',
    logout: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    organizationAPI.listOrganizations.mockResolvedValue([]);
  });

  describe('Organization Creation', () => {
    test('shows validation error for short slug', async () => {
      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      // Wait for component to load
      await waitFor(() => {
        expect(organizationAPI.listOrganizations).toHaveBeenCalled();
      });

      // Click "Create Organization" button
      const createButton = screen.getByText(/create organization/i);
      fireEvent.click(createButton);

      // Fill in form with short slug
      const nameInput = screen.getByLabelText(/organization name/i);
      const slugInput = screen.getByLabelText(/organization id/i);

      await userEvent.type(nameInput, 'Test Org');
      await userEvent.type(slugInput, 'ab'); // Too short

      // Mock API error for validation
      const validationError = new Error('slug: must be at least 3 characters long');
      validationError.status = 422;
      validationError.data = {
        error: {
          message: 'Request validation failed',
          details: {
            errors: [{
              field: 'body.slug',
              message: 'String should have at least 3 characters'
            }]
          }
        }
      };
      organizationAPI.createOrganization.mockRejectedValue(validationError);

      // Submit form
      const submitButton = screen.getByText(/create organization/i, { selector: 'button' });
      fireEvent.click(submitButton);

      // Verify error is shown
      await waitFor(() => {
        expect(mockError).toHaveBeenCalledWith(
          expect.stringContaining('slug')
        );
      });
    });

    test('shows free tier limit error with upgrade prompt', async () => {
      // Mock organization already exists
      organizationAPI.listOrganizations.mockResolvedValue([
        { id: '1', name: 'Existing Org', slug: 'existing' }
      ]);

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(organizationAPI.listOrganizations).toHaveBeenCalled();
      });

      // Click "Create Organization"
      const createButton = screen.getByText(/create organization/i);
      fireEvent.click(createButton);

      // Fill form
      const nameInput = screen.getByLabelText(/organization name/i);
      const slugInput = screen.getByLabelText(/organization id/i);

      await userEvent.type(nameInput, 'Second Org');
      await userEvent.type(slugInput, 'second-org');

      // Mock 402 error (tier limit)
      const limitError = new Error("You've reached your Free plan's limit of 1 organization");
      limitError.status = 402;
      limitError.data = {
        error: 'limit_exceeded',
        feature: 'Organizations',
        current_tier: 'Free',
        current_limit: 1,
        current_count: 1,
        message: "You've reached your Free plan's limit of 1 organization",
        upgrade_message: "Upgrade to Starter ($29/month) to create up to 3 organizations",
        upgrade_options: [
          { tier: 'Starter', price: '$29/month', organizations: 3 }
        ]
      };
      organizationAPI.createOrganization.mockRejectedValue(limitError);

      // Submit
      const submitButton = screen.getByText(/create organization/i, { selector: 'button' });
      fireEvent.click(submitButton);

      // Verify upgrade prompt is shown
      await waitFor(() => {
        expect(screen.getByText(/upgrade/i)).toBeInTheDocument();
      });
    });

    test('creates organization successfully', async () => {
      organizationAPI.createOrganization.mockResolvedValue({
        id: '123',
        name: 'New Org',
        slug: 'new-org',
        is_active: true
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
      const createButton = screen.getByText(/create organization/i);
      fireEvent.click(createButton);

      // Fill form
      const nameInput = screen.getByLabelText(/organization name/i);
      const slugInput = screen.getByLabelText(/organization id/i);

      await userEvent.type(nameInput, 'New Org');
      await userEvent.clear(slugInput);
      await userEvent.type(slugInput, 'new-org');

      // Submit
      const submitButton = screen.getByText(/create organization/i, { selector: 'button' });
      fireEvent.click(submitButton);

      // Verify success
      await waitFor(() => {
        expect(organizationAPI.createOrganization).toHaveBeenCalledWith({
          name: 'New Org',
          slug: 'new-org',
          description: '',
          currency: 'USD',
          timezone: 'UTC'
        });
        expect(mockSuccess).toHaveBeenCalledWith(
          expect.stringContaining('New Org')
        );
      });
    });
  });

  describe('Organization Deletion', () => {
    test('deletes organization successfully', async () => {
      const mockOrg = {
        id: '123',
        name: 'Test Org',
        slug: 'test-org',
        is_active: true
      };

      organizationAPI.listOrganizations.mockResolvedValue([mockOrg]);
      organizationAPI.deleteOrganization.mockResolvedValue();

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Org')).toBeInTheDocument();
      });

      // Click delete button
      const deleteButton = screen.getByTestId('delete-org-123');
      fireEvent.click(deleteButton);

      // Confirm deletion
      const confirmButton = await screen.findByText(/confirm/i);
      fireEvent.click(confirmButton);

      // Verify deletion
      await waitFor(() => {
        expect(organizationAPI.deleteOrganization).toHaveBeenCalledWith('123');
        expect(mockSuccess).toHaveBeenCalled();
      });
    });
  });

  describe('Organization Editing', () => {
    test('updates organization successfully', async () => {
      const mockOrg = {
        id: '123',
        name: 'Original Name',
        slug: 'original',
        description: 'Original description',
        is_active: true
      };

      organizationAPI.listOrganizations.mockResolvedValue([mockOrg]);
      organizationAPI.updateOrganization.mockResolvedValue({
        ...mockOrg,
        name: 'Updated Name',
        description: 'Updated description'
      });

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(screen.getByText('Original Name')).toBeInTheDocument();
      });

      // Click edit button
      const editButton = screen.getByTestId('edit-org-123');
      fireEvent.click(editButton);

      // Update name
      const nameInput = screen.getByLabelText(/organization name/i);
      await userEvent.clear(nameInput);
      await userEvent.type(nameInput, 'Updated Name');

      // Submit
      const saveButton = screen.getByText(/save/i);
      fireEvent.click(saveButton);

      // Verify update
      await waitFor(() => {
        expect(organizationAPI.updateOrganization).toHaveBeenCalledWith(
          '123',
          expect.objectContaining({
            name: 'Updated Name'
          })
        );
        expect(mockSuccess).toHaveBeenCalled();
      });
    });
  });

  describe('Real-time Validation', () => {
    test('checks slug availability in real-time', async () => {
      organizationAPI.checkSlugAvailability.mockResolvedValue({
        available: true,
        message: 'Slug is available'
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
      const createButton = screen.getByText(/create organization/i);
      fireEvent.click(createButton);

      // Type slug
      const slugInput = screen.getByLabelText(/organization id/i);
      await userEvent.type(slugInput, 'test-slug');

      // Wait for debounced validation
      await waitFor(() => {
        expect(organizationAPI.checkSlugAvailability).toHaveBeenCalledWith('test-slug');
      }, { timeout: 1000 });

      // Verify availability indicator
      expect(screen.getByText(/slug is available/i)).toBeInTheDocument();
    });

    test('shows slug unavailable message', async () => {
      organizationAPI.checkSlugAvailability.mockResolvedValue({
        available: false,
        message: 'Slug is already taken',
        suggestions: ['test-slug-1', 'test-slug-2']
      });

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <OrganizationManagement />
        </AuthContext.Provider>
      );

      await waitFor(() => {
        expect(organizationAPI.listOrganizations).toHaveBeenCalled();
      });

      const createButton = screen.getByText(/create organization/i);
      fireEvent.click(createButton);

      const slugInput = screen.getByLabelText(/organization id/i);
      await userEvent.type(slugInput, 'taken-slug');

      await waitFor(() => {
        expect(screen.getByText(/already taken/i)).toBeInTheDocument();
      }, { timeout: 1000 });

      // Verify suggestions are shown
      expect(screen.getByText(/test-slug-1/)).toBeInTheDocument();
    });
  });
});
