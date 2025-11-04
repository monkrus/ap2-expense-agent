import React, { useState, useEffect } from 'react';
import {
  Building2, Users, Settings, UserPlus, Mail, Edit, Trash2, Check, X, Plus,
  Search, RefreshCw, AlertCircle, Globe, Clock, Shield, Crown, ChevronDown, Copy, ArrowLeft
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import organizationAPI from '../services/organizationAPI';

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

  // Forms
  const [createOrgForm, setCreateOrgForm] = useState({
    name: '', slug: '', description: '', currency: 'USD', timezone: 'UTC'
  });
  const [editOrgForm, setEditOrgForm] = useState({});
  const [inviteForm, setInviteForm] = useState({ email: '', role: 'member' });
  const [bulkEmails, setBulkEmails] = useState('');
  const [showBulk, setShowBulk] = useState(false);

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (currentOrg) {
      fetchOrgMembers();
      fetchOrgInvitations();
    }
  }, [currentOrg]);

  const fetchOrganizations = async () => {
    try {
      setLoading(true);
      const data = await organizationAPI.listOrganizations();
      setOrganizations(data);
      if (data.length > 0 && !currentOrg) setCurrentOrg(data[0]);
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
      showError(err.message);
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
          <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-4" />
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
              <p className="text-gray-600 mt-1">Manage organizations, members, and team settings</p>
            </div>
            {/* Only show Create button in header if organizations exist */}
            {organizations.length > 0 && (
              <button
                onClick={() => setShowCreateOrgModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                <Plus className="w-5 h-5" />
                Create Organization
              </button>
            )}
          </div>

          {/* Org Selector */}
          {organizations.length > 0 && (
            <div className="mt-6">
              <select
                value={currentOrg?.id || ''}
                onChange={(e) => setCurrentOrg(organizations.find(o => o.id === e.target.value))}
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
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-semibold">Team Members ({members.length})</h3>
                    <button
                      onClick={() => setShowInviteModal(true)}
                      className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg"
                    >
                      <UserPlus className="w-4 h-4" />
                      Invite Member
                    </button>
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
                className="w-full px-3 py-2 border rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Organization ID*
              </label>
              <input
                type="text"
                value={createOrgForm.slug}
                onChange={(e) => setCreateOrgForm({ ...createOrgForm, slug: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                placeholder="acme-corp"
                pattern="[a-z0-9-]+"
                title="Use only lowercase letters, numbers, and hyphens"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                <strong>Auto-generated from name</strong> (you can customize it). Use only lowercase letters, numbers, and hyphens. Example: "Corex Inc" becomes "corex-inc"
              </p>
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
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="America/Los_Angeles">America/Los_Angeles</option>
                  <option value="Europe/London">Europe/London</option>
                </select>
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
                disabled={processing}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg disabled:opacity-50"
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
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="America/Los_Angeles">America/Los_Angeles</option>
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
