import React, { useState, useEffect } from 'react';
import {
  Calendar,
  DollarSign,
  Repeat,
  Plus,
  Pause,
  Play,
  Trash2,
  Edit2,
  Clock,
  CheckCircle,
  AlertCircle,
  Info
} from 'lucide-react';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../contexts/AuthContext';
import RecurringExpenseForm from '../components/RecurringExpenseForm';

const RecurringExpenses = () => {
  const { user } = useAuth();
  const { success, error: showError } = useToast();

  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [filter, setFilter] = useState('all'); // all, active, paused, inactive

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch('/api/recurring-expenses?active_only=false', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to fetch recurring expenses');

      const data = await response.json();
      setTemplates(data);
    } catch (err) {
      showError('Failed to load recurring expenses');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setSelectedTemplate(null);
    setShowForm(true);
  };

  const handleEdit = (template) => {
    setSelectedTemplate(template);
    setShowForm(true);
  };

  const handleFormSuccess = () => {
    setShowForm(false);
    setSelectedTemplate(null);
    fetchTemplates();
    success(selectedTemplate ? 'Recurring expense updated!' : 'Recurring expense created!');
  };

  const handlePause = async (templateId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/recurring-expenses/${templateId}/pause`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to pause recurring expense');

      success('Recurring expense paused');
      fetchTemplates();
    } catch (err) {
      showError('Failed to pause recurring expense');
    }
  };

  const handleResume = async (templateId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/recurring-expenses/${templateId}/resume`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to resume recurring expense');

      success('Recurring expense resumed');
      fetchTemplates();
    } catch (err) {
      showError('Failed to resume recurring expense');
    }
  };

  const handleDelete = async (templateId, vendor) => {
    if (!window.confirm(`Delete recurring expense for ${vendor}?`)) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/recurring-expenses/${templateId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to delete recurring expense');

      success('Recurring expense deleted');
      fetchTemplates();
    } catch (err) {
      showError('Failed to delete recurring expense');
    }
  };

  const getFrequencyLabel = (frequency) => {
    const labels = {
      weekly: 'Weekly',
      biweekly: 'Bi-weekly',
      monthly: 'Monthly',
      quarterly: 'Quarterly',
      yearly: 'Yearly'
    };
    return labels[frequency] || frequency;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getStatusBadge = (template) => {
    if (!template.is_active) {
      return <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded">Inactive</span>;
    }
    if (template.is_paused) {
      return <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">Paused</span>;
    }
    return <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">Active</span>;
  };

  const filteredTemplates = templates.filter(template => {
    if (filter === 'all') return true;
    if (filter === 'active') return template.is_active && !template.is_paused;
    if (filter === 'paused') return template.is_paused;
    if (filter === 'inactive') return !template.is_active;
    return true;
  });

  const stats = {
    total: templates.length,
    active: templates.filter(t => t.is_active && !t.is_paused).length,
    paused: templates.filter(t => t.is_paused).length,
    totalSubmitted: templates.reduce((sum, t) => sum + t.total_submitted, 0)
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
                <Repeat className="w-8 h-8 text-indigo-600" />
                Recurring Expenses
              </h1>
              <p className="text-gray-600 mt-2">Automate your regular expense submissions</p>
            </div>
            <button
              onClick={handleCreate}
              className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
            >
              <Plus className="w-5 h-5" />
              New Recurring Expense
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Total Templates</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
              </div>
              <Repeat className="w-10 h-10 text-blue-500 opacity-50" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Active</p>
                <p className="text-2xl font-bold text-green-600">{stats.active}</p>
              </div>
              <CheckCircle className="w-10 h-10 text-green-500 opacity-50" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Paused</p>
                <p className="text-2xl font-bold text-yellow-600">{stats.paused}</p>
              </div>
              <Pause className="w-10 h-10 text-yellow-500 opacity-50" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Total Submitted</p>
                <p className="text-2xl font-bold text-indigo-600">{stats.totalSubmitted}</p>
              </div>
              <DollarSign className="w-10 h-10 text-indigo-500 opacity-50" />
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Filter:</span>
            {['all', 'active', 'paused', 'inactive'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filter === f
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Templates List */}
        <div className="bg-white rounded-lg shadow p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div className="text-center py-12">
              <Repeat className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg font-medium">No recurring expenses found</p>
              <p className="text-gray-400 text-sm mt-2">
                {filter !== 'all' ? 'Try changing the filter' : 'Create your first recurring expense to get started'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredTemplates.map(template => (
                <div
                  key={template.id}
                  className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{template.vendor}</h3>
                        {getStatusBadge(template)}
                        {template.auto_submit && (
                          <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Auto-submit
                          </span>
                        )}
                      </div>

                      <p className="text-gray-600 text-sm mb-3">{template.description}</p>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">Amount</p>
                          <p className="font-semibold text-gray-900">${Number(template.amount).toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Frequency</p>
                          <p className="font-semibold text-gray-900">{getFrequencyLabel(template.frequency)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Next Run</p>
                          <p className="font-semibold text-gray-900">{formatDate(template.next_run_date)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Submitted</p>
                          <p className="font-semibold text-gray-900">{template.total_submitted} times</p>
                        </div>
                      </div>

                      {template.end_date && (
                        <div className="mt-2 text-sm text-gray-600">
                          <Info className="w-4 h-4 inline mr-1" />
                          Ends on {formatDate(template.end_date)}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={() => handleEdit(template)}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Edit"
                      >
                        <Edit2 className="w-5 h-5" />
                      </button>

                      {template.is_active && (
                        template.is_paused ? (
                          <button
                            onClick={() => handleResume(template.id)}
                            className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                            title="Resume"
                          >
                            <Play className="w-5 h-5" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handlePause(template.id)}
                            className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
                            title="Pause"
                          >
                            <Pause className="w-5 h-5" />
                          </button>
                        )
                      )}

                      <button
                        onClick={() => handleDelete(template.id, template.vendor)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Form Modal */}
      {showForm && (
        <RecurringExpenseForm
          template={selectedTemplate}
          onSuccess={handleFormSuccess}
          onCancel={() => {
            setShowForm(false);
            setSelectedTemplate(null);
          }}
        />
      )}
    </div>
  );
};

export default RecurringExpenses;
