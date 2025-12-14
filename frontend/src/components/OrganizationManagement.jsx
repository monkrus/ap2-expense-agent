import React, { useState, useEffect } from 'react';
import {
  Building2, Users, Settings, UserPlus, Mail, Edit, Trash2, Check, X, Plus,
  Search, RefreshCw, AlertCircle, Globe, Clock, Shield, Crown, ChevronDown, Copy, ArrowLeft
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import organizationAPI from '../services/organizationAPI';
import UpgradePrompt from './upsell/UpgradePrompt';

const OrganizationManagement = () => {
  const { user } = useAuth();
  const { success, error: showError } = useToast();

  const [activeTab, setActiveTab] = useState('overview');
  const [organizations, setOrganizations] = useState([]);
  const [currentOrg, setCurrentOrg] = useState(null);
  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  // Modals
  const [showCreateOrgModal, setShowCreateOrgModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showEditOrgModal, setShowEditOrgModal] = useState(false);
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);
  const [upgradeTierInfo, setUpgradeTierInfo] = useState(null);

  // Forms
  const [createOrgForm, setCreateOrgForm] = useState({
    name: '', slug: '', description: '', currency: 'USD', timezone: 'UTC'
  });
  const [editOrgForm, setEditOrgForm] = useState({});
  const [inviteForm, setInviteForm] = useState({ email: '', role: 'member' });
  const [bulkEmails, setBulkEmails] = useState('');
  const [showBulk, setShowBulk] = useState(false);

  // Real-time validation state
  const [nameValidation, setNameValidation] = useState({ checking: false, result: null });
  const [slugValidation, setSlugValidation] = useState({ checking: false, result: null });

  // Debounced name validation
  useEffect(() => {
    if (!createOrgForm.name || createOrgForm.name.trim().length === 0) {
      setNameValidation({ checking: false, result: null });
      return;
    }

    setNameValidation({ checking: true, result: null });

    const timer = setTimeout(async () => {
      try {
        const result = await organizationAPI.checkNameAvailability(createOrgForm.name);
        setNameValidation({ checking: false, result });
      } catch (err) {
        console.error('Name validation error:', err);
        setNameValidation({ checking: false, result: null });
      }
    }, 500); // 500ms debounce

    return () => clearTimeout(timer);
  }, [createOrgForm.name]);

  // Debounced slug validation
  useEffect(() => {
    if (!createOrgForm.slug || createOrgForm.slug.trim().length === 0) {
      setSlugValidation({ checking: false, result: null });
      return;
    }

    setSlugValidation({ checking: true, result: null });

    const timer = setTimeout(async () => {
      try {
        const result = await organizationAPI.checkSlugAvailability(createOrgForm.slug);
        setSlugValidation({ checking: false, result });
      } catch (err) {
        console.error('Slug validation error:', err);
        setSlugValidation({ checking: false, result: null });
      }
    }, 500); // 500ms debounce

    return () => clearTimeout(timer);
  }, [createOrgForm.slug]);

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (currentOrg) {
      // Save to localStorage and dispatch event for other components (like Billing)
      organizationAPI.setCurrentOrganizationId(currentOrg.id);
      window.dispatchEvent(new CustomEvent('organizationChanged', { detail: { orgId: currentOrg.id } }));

      fetchOrgMembers();
      fetchOrgInvitations();
    }
  }, [currentOrg]);

  const fetchOrganizations = async () => {
    try {
      setLoading(true);
      const data = await organizationAPI.listOrganizations();
      setOrganizations(data);

      if (data.length > 0 && !currentOrg) {
        // Check if there's a saved organization in localStorage
        const savedOrgId = organizationAPI.getCurrentOrganizationId();
        const savedOrg = savedOrgId ? data.find(org => org.id === savedOrgId) : null;

        // Use saved org if found, otherwise use first org
        setCurrentOrg(savedOrg || data[0]);
      }
    } catch (err) {
      showError('Failed to load organizations');
    } finally {
      setLoading(false);
    }
  };

  const fetchOrgMembers = async () => {
    if (!currentOrg) return;
    try {
      const data = await organizationAPI.listMembers(currentOrg.id);
      setMembers(data);
    } catch (err) {
      showError('Failed to load members');
    }
  };

  const fetchOrgInvitations = async () => {
    if (!currentOrg) return;
    try {
      const data = await organizationAPI.listInvitations(currentOrg.id);
      setInvitations(data);
    } catch (err) {
      console.error('Failed to load invitations:', err);
    }
  };

  const handleCreateOrg = async (e) => {
    e.preventDefault();
    setProcessing(true);
    try {
      const newOrg = await organizationAPI.createOrganization(createOrgForm);
      success(`Organization "${newOrg.name}" created!`);
      setOrganizations([...organizations, newOrg]);
      setCurrentOrg(newOrg);
      setShowCreateOrgModal(false);
      setCreateOrgForm({ name: '', slug: '', description: '', currency: 'USD', timezone: 'UTC' });
    } catch (err) {
      // Handle Free tier limit (402 Payment Required)
      if (err.status === 402) {
        const errorData = err.data || {};
        const friendlyMessage =
          err.friendlyMessage ||
          errorData.user_friendly_message ||
          errorData.message ||
          'Free plan allows 1 organization. Upgrade to create another.';

        // Store tier info for upgrade prompt
        setUpgradeTierInfo({
          currentTier: errorData.current_tier || 'free',
          currentLimit: errorData.current_limit || 1,
          currentCount: errorData.current_count || 1,
          message: friendlyMessage
        });

        // Close create modal
        setShowCreateOrgModal(false);

        // Show upgrade prompt modal
        setShowUpgradePrompt(true);
        showError(friendlyMessage);
      }
      // Handle validation errors with suggestions (400 Bad Request)
      else if (err.status === 400 && err.data) {
        const errorData = err.data;
        let errorMessage = errorData.message || err.message;

        // Add suggestions if available
        if (errorData.suggestions && errorData.suggestions.length > 0) {
          errorMessage += '\n\nSuggestions:\n' + errorData.suggestions.map(s => `  • ${s}`).join('\n');
        }

        // Add hint if available
        if (errorData.hint) {
          errorMessage += '\n\n' + errorData.hint;
        }

        showError(errorMessage);
      }
      else {
        showError(err.message);
      }
    } finally {
      setProcessing(false);
    }
  };

  const handleUpdateOrg = async (e) => {
    e.preventDefault();
    if (!currentOrg) return;
    setProcessing(true);
    try {
      const updated = await organizationAPI.updateOrganization(currentOrg.id, editOrgForm);
      success('Organization updated!');
      setOrganizations(organizations.map(o => o.id === updated.id ? updated : o));
      setCurrentOrg(updated);
      setShowEditOrgModal(false);
    } catch (err) {
      showError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!currentOrg) return;
    setProcessing(true);
    try {
      await organizationAPI.createInvitation(currentOrg.id, inviteForm.email, inviteForm.role);
      success(`Invitation sent to ${inviteForm.email}!`);
      setShowInviteModal(false);
      setInviteForm({ email: '', role: 'member' });
      fetchOrgInvitations();
    } catch (err) {
      showError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleBulkInvite = async () => {
    if (!currentOrg || !bulkEmails.trim()) return;
    setProcessing(true);
    const emails = bulkEmails.split('\n').map(e => e.trim()).filter(e => e);
    const results = await organizationAPI.bulkInviteMembers(currentOrg.id, emails, 'member');
    success(`Sent: ${results.successful.length} successful, ${results.failed.length} failed`);
    setBulkEmails('');
    setShowBulk(false);
    fetchOrgInvitations();
    setProcessing(false);
  };

  const handleUpdateRole = async (memberId, newRole) => {
    if (!currentOrg) return;
    setProcessing(true);
    try {
      await organizationAPI.updateMemberRole(currentOrg.id, memberId, newRole);
      success('Role updated!');
      fetchOrgMembers();
    } catch (err) {
      showError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (!currentOrg || !confirm('Remove this member?')) return;
    setProcessing(true);
    try {
      await organizationAPI.removeMember(currentOrg.id, memberId);
      success('Member removed');
      fetchOrgMembers();
    } catch (err) {
      showError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleDeleteOrg = async () => {
    if (!currentOrg) return;

    // Use organization slug for confirmation to avoid apostrophe/quote issues
    const confirmText = currentOrg.slug.toLowerCase();

    const userInput = prompt(
      `⚠️ WARNING: This will permanently delete "${currentOrg.name}" and all associated data.\n\n` +
      `This action CANNOT be undone.\n\n` +
      `To confirm, type the organization ID: ${confirmText}`
    );

    // Case-insensitive comparison and trim whitespace
    if (userInput?.toLowerCase().trim() !== confirmText) {
      if (userInput !== null) {
        showError('Deletion cancelled - confirmation text did not match');
      }
      return;
    }

    setProcessing(true);
    const orgName = currentOrg.name; // Store name before deletion
    const deletedOrgId = currentOrg.id; // Store ID before deletion
    try {
      await organizationAPI.deleteOrganization(currentOrg.id);

      // Clear current org immediately
      setCurrentOrg(null);

      // Refetch organizations to ensure we get updated list from server
      const data = await organizationAPI.listOrganizations();
      setOrganizations(data);

      // Select first available organization or null if none left
      if (data.length > 0) {
        // Select a different org (not the deleted one)
        const nextOrg = data.find(org => org.id !== deletedOrgId) || data[0];
        setCurrentOrg(nextOrg);
      } else {
        setCurrentOrg(null);
      }

      // Show success confirmation
      success(`✓ Organization "${orgName}" has been permanently deleted`);

      // Additional confirmation alert
      setTimeout(() => {
        alert(`✓ Deletion Confirmed\n\nOrganization "${orgName}" and all associated data have been permanently removed.`);
      }, 500);
    } catch (err) {
      showError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleRevokeInvite = async (inviteId) => {
    if (!currentOrg) return;
    setProcessing(true);
    try {
      await organizationAPI.revokeInvitation(currentOrg.id, inviteId);
      success('Invitation revoked');
      fetchOrgInvitations();
    } catch (err) {
      showError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const getRoleColor = (role) => {
    const colors = {
      owner: 'bg-purple-100 text-purple-800',
      admin: 'bg-blue-100 text-blue-800',
      manager: 'bg-green-100 text-green-800',
      member: 'bg-gray-100 text-gray-800'
    };
    return colors[role] || colors.member;
  };

  const getRoleIcon = (role) => {
    switch(role) {
      case 'owner': return <Crown className="w-4 h-4" />;
      case 'admin': return <Shield className="w-4 h-4" />;
      default: return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-100 rounded-full mb-4">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
          </div>
          <p className="text-gray-600">Loading organizations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          {/* Back to Dashboard Button */}
          {user?.role === 'admin' && (
            <button
              onClick={() => window.location.href = '/'}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Dashboard
            </button>
          )}

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <Building2 className="w-8 h-8 text-indigo-600" />
                Organization Management
              </h1>
              <p className="text-gray-600 mt-1">
                Manage organizations, members, and team settings
                {organizations.length > 0 && (
                  <span className="ml-2 text-indigo-600 font-medium">
                    • {organizations.length} {organizations.length === 1 ? 'organization' : 'organizations'}
                  </span>
                )}
              </p>
            </div>
            {/* Only show Create button in header if organizations exist */}
            {organizations.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setShowCreateOrgModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  <Plus className="w-5 h-5" />
                  Create Organization
                </button>
              </div>
            )}
          </div>

          {/* Org Selector */}
          {organizations.length > 0 && (
            <div className="mt-6">
              <select
                value={currentOrg?.id || ''}
                onChange={(e) => {
                  const newOrg = organizations.find(o => o.id === e.target.value);
                  setCurrentOrg(newOrg);

                  // Save to localStorage and notify other components
                  if (newOrg) {
                    organizationAPI.setCurrentOrganizationId(newOrg.id);
                    window.dispatchEvent(new CustomEvent('organizationChanged', { detail: { organizationId: newOrg.id } }));
                  }
                }}
                className="block w-full max-w-md pl-4 pr-10 py-3 border-gray-300 rounded-lg"
              >
                {organizations.map(org => (
                  <option key={org.id} value={org.id}>{org.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      {organizations.length === 0 ? (
        <div className="max-w-7xl mx-auto px-4 py-12">
          <div className="text-center bg-white rounded-lg shadow p-12">
            <Building2 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">No Organizations Yet</h3>
            <p className="text-gray-600 mb-6">Create your first organization to get started</p>
            <button
              onClick={() => setShowCreateOrgModal(true)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg"
            >
              <Plus className="w-5 h-5" />
              Create Your First Organization
            </button>
          </div>
        </div>
      ) : currentOrg && (
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="bg-white rounded-lg shadow">
            {/* Tabs */}
            <div className="border-b">
              <nav className="-mb-px flex space-x-8 px-6">
                {[
                  { id: 'overview', label: 'Overview', icon: Building2 },
                  { id: 'members', label: 'Members', icon: Users },
                  { id: 'invitations', label: 'Invitations', icon: Mail },
                  { id: 'settings', label: 'Settings', icon: Settings }
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`${
                      activeTab === tab.id
                        ? 'border-indigo-500 text-indigo-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    } flex items-center gap-2 py-4 border-b-2 font-medium text-sm`}
                  >
                    <tab.icon className="w-5 h-5" />
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            {/* Tab Content */}
            <div className="p-6">
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-blue-50 rounded-lg p-6">
                      <Users className="w-8 h-8 text-blue-600 mb-2" />
                      <p className="text-2xl font-bold text-blue-900">{members.length}</p>
                      <p className="text-blue-700 text-sm">Team Members</p>
                    </div>
                    <div className="bg-yellow-50 rounded-lg p-6">
                      <Mail className="w-8 h-8 text-yellow-600 mb-2" />
                      <p className="text-2xl font-bold text-yellow-900">{invitations.length}</p>
                      <p className="text-yellow-700 text-sm">Pending Invitations</p>
                    </div>
                    <div className="bg-green-50 rounded-lg p-6">
                      <Globe className="w-8 h-8 text-green-600 mb-2" />
                      <p className="text-2xl font-bold text-green-900">{currentOrg.currency}</p>
                      <p className="text-green-700 text-sm">Currency</p>
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-6">
                    <h3 className="text-lg font-semibold mb-4">Organization Details</h3>
                    <dl className="grid grid-cols-2 gap-4">
                      <div>
                        <dt className="text-sm text-gray-500">Name</dt>
                        <dd className="text-base font-medium">{currentOrg.name}</dd>
                      </div>
                      <div>
                        <dt className="text-sm text-gray-500">Organization ID</dt>
                        <dd className="text-base font-medium font-mono">{currentOrg.slug}</dd>
                      </div>
                      <div>
                        <dt className="text-sm text-gray-500">Timezone</dt>
                        <dd className="text-base font-medium">{currentOrg.timezone}</dd>
                      </div>
                      <div>
                        <dt className="text-sm text-gray-500">Max Members</dt>
                        <dd className="text-base font-medium">{currentOrg.max_members}</dd>
                      </div>
                    </dl>
                  </div>
                </div>
              )}

              {activeTab === 'members' && (
                <div>
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold">Team Members ({members.length})</h3>
                  </div>
                  <div className="space-y-3">
                    {members.map(member => (
                      <div key={member.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium">{member.full_name || member.email}</p>
                          <p className="text-sm text-gray-600">{member.email}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${getRoleColor(member.role)}`}>
                            {getRoleIcon(member.role)}
                            {member.role}
                          </span>
                          {member.role !== 'owner' && (
                            <>
                              <select
                                value={member.role}
                                onChange={(e) => handleUpdateRole(member.id, e.target.value)}
                                className="text-sm border rounded px-2 py-1"
                                disabled={processing}
                              >
                                <option value="member">Member</option>
                                <option value="manager">Manager</option>
                                <option value="admin">Admin</option>
                              </select>
                              <button
                                onClick={() => handleRemoveMember(member.id)}
                                className="text-red-600 hover:text-red-700"
                                disabled={processing}
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'invitations' && (
                <div>
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-semibold">Pending Invitations ({invitations.length})</h3>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setShowBulk(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg"
                      >
                        <UserPlus className="w-4 h-4" />
                        Bulk Invite
                      </button>
                      <button
                        onClick={() => setShowInviteModal(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg"
                      >
                        <UserPlus className="w-4 h-4" />
                        Invite Member
                      </button>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {invitations.length === 0 ? (
                      <p className="text-gray-500 text-center py-8">No pending invitations</p>
                    ) : (
                      invitations.map(inv => (
                        <div key={inv.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                          <div>
                            <p className="font-medium">{inv.email}</p>
                            <p className="text-sm text-gray-600">
                              Invited {new Date(inv.created_at).toLocaleDateString()} • Expires {new Date(inv.expires_at).toLocaleDateString()}
                            </p>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getRoleColor(inv.role)}`}>
                              {inv.role}
                            </span>
                            <span className="text-xs text-yellow-600 bg-yellow-100 px-2 py-1 rounded">
                              {inv.status}
                            </span>
                            <button
                              onClick={() => handleRevokeInvite(inv.id)}
                              className="text-red-600 hover:text-red-700"
                              disabled={processing}
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'settings' && (
                <div className="space-y-6">
                  <div className="bg-gray-50 rounded-lg p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-semibold mb-2">Organization Settings</h3>
                        <p className="text-sm text-gray-600">Update your organization details</p>
                      </div>
                      <button
                        onClick={() => {
                          setEditOrgForm({
                            name: currentOrg.name,
                            description: currentOrg.description || '',
                            currency: currentOrg.currency,
                            timezone: currentOrg.timezone
                          });
                          setShowEditOrgModal(true);
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg"
                      >
                        <Edit className="w-4 h-4" />
                        Edit
                      </button>
                    </div>
                    <dl className="grid grid-cols-2 gap-4">
                      <div>
                        <dt className="text-sm text-gray-500 mb-1">Organization Name</dt>
                        <dd className="text-base font-medium">{currentOrg.name}</dd>
                      </div>
                      <div>
                        <dt className="text-sm text-gray-500 mb-1">Organization ID</dt>
                        <dd className="text-base font-mono text-gray-700">{currentOrg.slug}</dd>
                      </div>
                      <div>
                        <dt className="text-sm text-gray-500 mb-1">Currency</dt>
                        <dd className="text-base font-medium">{currentOrg.currency}</dd>
                      </div>
                      <div>
                        <dt className="text-sm text-gray-500 mb-1">Timezone</dt>
                        <dd className="text-base font-medium">{currentOrg.timezone}</dd>
                      </div>
                      {currentOrg.description && (
                        <div className="col-span-2">
                          <dt className="text-sm text-gray-500 mb-1">Description</dt>
                          <dd className="text-base text-gray-700">{currentOrg.description}</dd>
                        </div>
                      )}
                    </dl>
                  </div>

                  {/* Danger Zone */}
                  <div className="border-2 border-red-200 rounded-lg p-6 bg-red-50">
                    <div className="flex items-start gap-3 mb-4">
                      <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                      <div>
                        <h3 className="text-lg font-semibold text-red-900 mb-1">Danger Zone</h3>
                        <p className="text-sm text-red-700">
                          Once you delete an organization, there is no going back. This action will permanently delete
                          the organization, all members, expenses, and associated data.
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={handleDeleteOrg}
                      disabled={processing}
                      className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete Organization
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {showCreateOrgModal && (
        <Modal title="Create Organization" onClose={() => setShowCreateOrgModal(false)}>
          <form onSubmit={handleCreateOrg} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Organization Name*</label>
              <input
                type="text"
                value={createOrgForm.name}
                onChange={(e) => setCreateOrgForm({
                  ...createOrgForm,
                  name: e.target.value,
                  slug: e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
                })}
                className={`w-full px-3 py-2 border rounded-lg ${
                  nameValidation.result && !nameValidation.result.available
                    ? 'border-yellow-400 focus:ring-yellow-400'
                    : nameValidation.result?.available
                      ? 'border-green-400 focus:ring-green-400'
                      : ''
                }`}
                required
              />
              {/* Real-time validation feedback */}
              {nameValidation.checking && (
                <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Checking availability...
                </p>
              )}
              {nameValidation.result && !nameValidation.result.available && (
                <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-xs text-yellow-800 font-medium flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {nameValidation.result.message}
                  </p>
                  {nameValidation.result.suggestions && nameValidation.result.suggestions.length > 0 && (
                    <div className="mt-1">
                      <p className="text-xs text-yellow-700 mb-1">Try these instead:</p>
                      <div className="flex flex-wrap gap-1">
                        {nameValidation.result.suggestions.map((suggestion, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => setCreateOrgForm({
                              ...createOrgForm,
                              name: suggestion,
                              slug: suggestion.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
                            })}
                            className="text-xs px-2 py-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 rounded border border-yellow-300 transition-colors"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {nameValidation.result.hint && (
                    <p className="text-xs text-yellow-600 mt-1 italic">{nameValidation.result.hint}</p>
                  )}
                </div>
              )}
              {nameValidation.result?.available && (
                <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                  <Check className="w-3 h-3" />
                  Name is available
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Organization ID*
              </label>
              <input
                type="text"
                value={createOrgForm.slug}
                onChange={(e) => setCreateOrgForm({ ...createOrgForm, slug: e.target.value })}
                className={`w-full px-3 py-2 border rounded-lg font-mono text-sm ${
                  slugValidation.result && !slugValidation.result.available
                    ? 'border-yellow-400 focus:ring-yellow-400'
                    : slugValidation.result?.available
                      ? 'border-green-400 focus:ring-green-400'
                      : ''
                }`}
                placeholder="acme-corp"
                pattern="[a-z0-9\-]+"
                title="Use only lowercase letters, numbers, and hyphens"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                <strong>Auto-generated from name</strong> (you can customize it). Use only lowercase letters, numbers, and hyphens. Example: "Corex Inc" becomes "corex-inc"
              </p>
              {/* Real-time slug validation feedback */}
              {slugValidation.checking && (
                <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Checking slug availability...
                </p>
              )}
              {slugValidation.result && !slugValidation.result.available && (
                <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-xs text-yellow-800 font-medium flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {slugValidation.result.message}
                  </p>
                  {slugValidation.result.suggestions && slugValidation.result.suggestions.length > 0 && (
                    <div className="mt-1">
                      <p className="text-xs text-yellow-700 mb-1">Try these instead:</p>
                      <div className="flex flex-wrap gap-1">
                        {slugValidation.result.suggestions.map((suggestion, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => setCreateOrgForm({ ...createOrgForm, slug: suggestion })}
                            className="text-xs px-2 py-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 rounded border border-yellow-300 font-mono transition-colors"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              {slugValidation.result?.available && (
                <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                  <Check className="w-3 h-3" />
                  Slug is available
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea
                value={createOrgForm.description}
                onChange={(e) => setCreateOrgForm({ ...createOrgForm, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                rows="2"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Currency</label>
                <select
                  value={createOrgForm.currency}
                  onChange={(e) => setCreateOrgForm({ ...createOrgForm, currency: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="USD">USD - US Dollar</option>
                  <option value="EUR">EUR - Euro</option>
                  <option value="GBP">GBP - British Pound</option>
                  <option value="JPY">JPY - Japanese Yen</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Timezone</label>
                <select
                  value={createOrgForm.timezone}
                  onChange={(e) => setCreateOrgForm({ ...createOrgForm, timezone: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <optgroup label="Universal">
                    <option value="UTC">UTC (Coordinated Universal Time)</option>
                  </optgroup>
                  <optgroup label="North America">
                    <option value="America/New_York">Eastern Time (New York)</option>
                    <option value="America/Chicago">Central Time (Chicago)</option>
                    <option value="America/Denver">Mountain Time (Denver)</option>
                    <option value="America/Los_Angeles">Pacific Time (Los Angeles)</option>
                    <option value="America/Phoenix">Arizona (Phoenix)</option>
                    <option value="America/Anchorage">Alaska (Anchorage)</option>
                    <option value="Pacific/Honolulu">Hawaii (Honolulu)</option>
                    <option value="America/Toronto">Canada Eastern (Toronto)</option>
                    <option value="America/Vancouver">Canada Pacific (Vancouver)</option>
                  </optgroup>
                  <optgroup label="Europe">
                    <option value="Europe/London">UK (London)</option>
                    <option value="Europe/Paris">France (Paris)</option>
                    <option value="Europe/Berlin">Germany (Berlin)</option>
                    <option value="Europe/Rome">Italy (Rome)</option>
                    <option value="Europe/Madrid">Spain (Madrid)</option>
                    <option value="Europe/Amsterdam">Netherlands (Amsterdam)</option>
                    <option value="Europe/Brussels">Belgium (Brussels)</option>
                    <option value="Europe/Zurich">Switzerland (Zurich)</option>
                    <option value="Europe/Stockholm">Sweden (Stockholm)</option>
                    <option value="Europe/Oslo">Norway (Oslo)</option>
                    <option value="Europe/Moscow">Russia (Moscow)</option>
                  </optgroup>
                  <optgroup label="Asia">
                    <option value="Asia/Dubai">UAE (Dubai)</option>
                    <option value="Asia/Kolkata">India (Kolkata)</option>
                    <option value="Asia/Singapore">Singapore</option>
                    <option value="Asia/Hong_Kong">Hong Kong</option>
                    <option value="Asia/Shanghai">China (Shanghai)</option>
                    <option value="Asia/Tokyo">Japan (Tokyo)</option>
                    <option value="Asia/Seoul">South Korea (Seoul)</option>
                    <option value="Asia/Bangkok">Thailand (Bangkok)</option>
                    <option value="Asia/Jakarta">Indonesia (Jakarta)</option>
                  </optgroup>
                  <optgroup label="Australia & Pacific">
                    <option value="Australia/Sydney">Australia East (Sydney)</option>
                    <option value="Australia/Melbourne">Australia (Melbourne)</option>
                    <option value="Australia/Brisbane">Australia (Brisbane)</option>
                    <option value="Australia/Perth">Australia West (Perth)</option>
                    <option value="Pacific/Auckland">New Zealand (Auckland)</option>
                  </optgroup>
                  <optgroup label="Africa">
                    <option value="Africa/Cairo">Egypt (Cairo)</option>
                    <option value="Africa/Johannesburg">South Africa (Johannesburg)</option>
                    <option value="Africa/Lagos">Nigeria (Lagos)</option>
                    <option value="Africa/Nairobi">Kenya (Nairobi)</option>
                  </optgroup>
                  <optgroup label="South America">
                    <option value="America/Sao_Paulo">Brazil (São Paulo)</option>
                    <option value="America/Argentina/Buenos_Aires">Argentina (Buenos Aires)</option>
                    <option value="America/Santiago">Chile (Santiago)</option>
                    <option value="America/Bogota">Colombia (Bogota)</option>
                    <option value="America/Lima">Peru (Lima)</option>
                  </optgroup>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  <strong>Why UTC?</strong> UTC ensures consistent timestamps across global teams and prevents daylight saving confusion. Recommended for international organizations.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => setShowCreateOrgModal(false)}
                className="px-4 py-2 border rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={
                  processing ||
                  nameValidation.checking ||
                  slugValidation.checking ||
                  (nameValidation.result && !nameValidation.result.available) ||
                  (slugValidation.result && !slugValidation.result.available)
                }
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {processing ? 'Creating...' : 'Create Organization'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showEditOrgModal && (
        <Modal title="Edit Organization" onClose={() => setShowEditOrgModal(false)}>
          <form onSubmit={handleUpdateOrg} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Organization Name*</label>
              <input
                type="text"
                value={editOrgForm.name}
                onChange={(e) => setEditOrgForm({ ...editOrgForm, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea
                value={editOrgForm.description}
                onChange={(e) => setEditOrgForm({ ...editOrgForm, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                rows="2"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Currency</label>
                <select
                  value={editOrgForm.currency}
                  onChange={(e) => setEditOrgForm({ ...editOrgForm, currency: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Timezone</label>
                <select
                  value={editOrgForm.timezone}
                  onChange={(e) => setEditOrgForm({ ...editOrgForm, timezone: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <optgroup label="Universal">
                    <option value="UTC">UTC (Coordinated Universal Time)</option>
                  </optgroup>
                  <optgroup label="North America">
                    <option value="America/New_York">Eastern Time (New York)</option>
                    <option value="America/Chicago">Central Time (Chicago)</option>
                    <option value="America/Denver">Mountain Time (Denver)</option>
                    <option value="America/Los_Angeles">Pacific Time (Los Angeles)</option>
                    <option value="America/Phoenix">Arizona (Phoenix)</option>
                    <option value="America/Anchorage">Alaska (Anchorage)</option>
                    <option value="Pacific/Honolulu">Hawaii (Honolulu)</option>
                    <option value="America/Toronto">Canada Eastern (Toronto)</option>
                    <option value="America/Vancouver">Canada Pacific (Vancouver)</option>
                  </optgroup>
                  <optgroup label="Europe">
                    <option value="Europe/London">UK (London)</option>
                    <option value="Europe/Paris">France (Paris)</option>
                    <option value="Europe/Berlin">Germany (Berlin)</option>
                    <option value="Europe/Rome">Italy (Rome)</option>
                    <option value="Europe/Madrid">Spain (Madrid)</option>
                    <option value="Europe/Amsterdam">Netherlands (Amsterdam)</option>
                    <option value="Europe/Brussels">Belgium (Brussels)</option>
                    <option value="Europe/Zurich">Switzerland (Zurich)</option>
                    <option value="Europe/Stockholm">Sweden (Stockholm)</option>
                    <option value="Europe/Oslo">Norway (Oslo)</option>
                    <option value="Europe/Moscow">Russia (Moscow)</option>
                  </optgroup>
                  <optgroup label="Asia">
                    <option value="Asia/Dubai">UAE (Dubai)</option>
                    <option value="Asia/Kolkata">India (Kolkata)</option>
                    <option value="Asia/Singapore">Singapore</option>
                    <option value="Asia/Hong_Kong">Hong Kong</option>
                    <option value="Asia/Shanghai">China (Shanghai)</option>
                    <option value="Asia/Tokyo">Japan (Tokyo)</option>
                    <option value="Asia/Seoul">South Korea (Seoul)</option>
                    <option value="Asia/Bangkok">Thailand (Bangkok)</option>
                    <option value="Asia/Jakarta">Indonesia (Jakarta)</option>
                  </optgroup>
                  <optgroup label="Australia & Pacific">
                    <option value="Australia/Sydney">Australia East (Sydney)</option>
                    <option value="Australia/Melbourne">Australia (Melbourne)</option>
                    <option value="Australia/Brisbane">Australia (Brisbane)</option>
                    <option value="Australia/Perth">Australia West (Perth)</option>
                    <option value="Pacific/Auckland">New Zealand (Auckland)</option>
                  </optgroup>
                  <optgroup label="Africa">
                    <option value="Africa/Cairo">Egypt (Cairo)</option>
                    <option value="Africa/Johannesburg">South Africa (Johannesburg)</option>
                    <option value="Africa/Lagos">Nigeria (Lagos)</option>
                    <option value="Africa/Nairobi">Kenya (Nairobi)</option>
                  </optgroup>
                  <optgroup label="South America">
                    <option value="America/Sao_Paulo">Brazil (São Paulo)</option>
                    <option value="America/Argentina/Buenos_Aires">Argentina (Buenos Aires)</option>
                    <option value="America/Santiago">Chile (Santiago)</option>
                    <option value="America/Bogota">Colombia (Bogota)</option>
                    <option value="America/Lima">Peru (Lima)</option>
                  </optgroup>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button type="button" onClick={() => setShowEditOrgModal(false)} className="px-4 py-2 border rounded-lg">
                Cancel
              </button>
              <button type="submit" disabled={processing} className="px-4 py-2 bg-indigo-600 text-white rounded-lg">
                {processing ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showInviteModal && (
        <Modal title="Invite Team Member" onClose={() => setShowInviteModal(false)}>
          <form onSubmit={handleInvite} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email Address*</label>
              <input
                type="email"
                value={inviteForm.email}
                onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="colleague@company.com"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Role</label>
              <select
                value={inviteForm.role}
                onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="member">Member - Can submit expenses</option>
                <option value="manager">Manager - Can approve expenses</option>
                <option value="admin">Admin - Full access</option>
              </select>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button type="button" onClick={() => setShowInviteModal(false)} className="px-4 py-2 border rounded-lg">
                Cancel
              </button>
              <button type="submit" disabled={processing} className="px-4 py-2 bg-indigo-600 text-white rounded-lg">
                {processing ? 'Sending...' : 'Send Invitation'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showBulk && (
        <Modal title="Bulk Invite Members" onClose={() => setShowBulk(false)}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email Addresses (one per line)</label>
              <textarea
                value={bulkEmails}
                onChange={(e) => setBulkEmails(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                rows="10"
                placeholder="user1@company.com&#10;user2@company.com&#10;user3@company.com"
              />
              <p className="text-xs text-gray-500 mt-1">
                {bulkEmails.split('\n').filter(e => e.trim()).length} emails
              </p>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowBulk(false)} className="px-4 py-2 border rounded-lg">
                Cancel
              </button>
              <button
                onClick={handleBulkInvite}
                disabled={processing || !bulkEmails.trim()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg disabled:opacity-50"
              >
                {processing ? 'Sending...' : 'Send Invitations'}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Upgrade Prompt for Organization Limit */}
      <UpgradePrompt
        isOpen={showUpgradePrompt}
        onClose={() => setShowUpgradePrompt(false)}
        feature="Multiple Organizations"
        currentUsage={upgradeTierInfo?.currentCount}
        limit={upgradeTierInfo?.currentLimit}
        title="Organization Limit Reached"
        description={upgradeTierInfo?.message || "Upgrade to create more organizations and unlock additional features."}
        recommendedPlan="Starter"
      />
    </div>
  );
};

// Simple Modal Component
const Modal = ({ title, children, onClose }) => (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
    <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      <div className="p-6 border-b">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>
      </div>
      <div className="p-6">
        {children}
      </div>
    </div>
  </div>
);

export default OrganizationManagement;
