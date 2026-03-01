import React, { useState, useEffect } from "react";
import {
  Plus,
  Edit2,
  Trash2,
  Power,
  CheckCircle,
  XCircle,
  AlertCircle,
  AlertTriangle,
  DollarSign,
  Users,
  Calendar,
  Clock,
  Tag,
  Building,
  TrendingUp,
  TestTube,
  Save,
  X,
} from "lucide-react";
import { useToast } from "../hooks/useToast";

const EXPENSE_CATEGORIES = [
  "MEALS",
  "TRAVEL",
  "OFFICE_SUPPLIES",
  "EQUIPMENT",
  "SOFTWARE",
  "MARKETING",
  "ENTERTAINMENT",
  "PARKING",
  "FUEL",
  "SHIPPING",
  "OTHER",
];

const ApprovalPolicies = () => {
  const { success, error: showError } = useToast();
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState(null);
  const [testingPolicy, setTestingPolicy] = useState(null);

  // Priority mapping
  const PRIORITY_LEVELS = {
    low: 100,
    medium: 500,
    high: 900,
  };

  const getPriorityLabel = (numericPriority) => {
    if (numericPriority >= 700) return "high";
    if (numericPriority >= 300) return "medium";
    return "low";
  };

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    priority: "medium",
    auto_approve: true,
    require_receipt: false,
    notify_on_auto_approve: true,
    max_amount_per_expense: "",
    daily_limit_per_user: "",
    monthly_limit_per_user: "",
    yearly_limit_per_user: "",
    conditions: {
      categories: [],
      vendors: [],
      exclude_vendors: [],
      min_amount: "",
    },
  });

  // Test form state
  const [testData, setTestData] = useState({
    amount: "",
    category: "", // Empty = All Categories
    vendor: "",
    has_receipt: true,
    test_limit_type: "", // "", "daily", "monthly", "yearly"
  });
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    loadPolicies();
  }, []);

  const loadPolicies = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("access_token");
      const response = await fetch("/api/v1/approval-policies", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error("Failed to load rules");

      const data = await response.json();
      setPolicies(data);
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const token = localStorage.getItem("access_token");

      // Parse numeric values for validation
      const maxPerExpense = formData.max_amount_per_expense
        ? parseFloat(formData.max_amount_per_expense)
        : null;
      const dailyLimit = formData.daily_limit_per_user
        ? parseFloat(formData.daily_limit_per_user)
        : null;
      const monthlyLimit = formData.monthly_limit_per_user
        ? parseFloat(formData.monthly_limit_per_user)
        : null;
      const yearlyLimit = formData.yearly_limit_per_user
        ? parseFloat(formData.yearly_limit_per_user)
        : null;

      // Validate limit logic
      if (maxPerExpense && dailyLimit && dailyLimit < maxPerExpense) {
        showError(
          `Daily limit ($${dailyLimit}) must be at least $${maxPerExpense} (max per expense) to allow any expenses up to the maximum amount.`
        );
        return;
      }

      if (dailyLimit && monthlyLimit && monthlyLimit < dailyLimit) {
        showError(
          `Monthly limit ($${monthlyLimit}) must be at least $${dailyLimit} (daily limit).`
        );
        return;
      }

      if (monthlyLimit && yearlyLimit && yearlyLimit < monthlyLimit) {
        showError(
          `Yearly limit ($${yearlyLimit}) must be at least $${monthlyLimit} (monthly limit).`
        );
        return;
      }

      const payload = {
        ...formData,
        priority: PRIORITY_LEVELS[formData.priority], // Convert text to numeric
        max_amount_per_expense: maxPerExpense,
        daily_limit_per_user: dailyLimit,
        monthly_limit_per_user: monthlyLimit,
        yearly_limit_per_user: yearlyLimit,
        conditions: {
          ...formData.conditions,
          min_amount: formData.conditions.min_amount
            ? parseFloat(formData.conditions.min_amount)
            : undefined,
        },
      };

      const url = editingPolicy
        ? `/api/v1/approval-policies/${editingPolicy.id}`
        : "/api/v1/approval-policies";

      const response = await fetch(url, {
        method: editingPolicy ? "PATCH" : "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to save rule");

      success(editingPolicy ? "Rule updated!" : "Rule created!");
      setShowCreateForm(false);
      setEditingPolicy(null);
      resetForm();
      loadPolicies();
    } catch (err) {
      showError(err.message);
    }
  };

  const handleDelete = async (policyId) => {
    if (!confirm("Are you sure you want to delete this rule?")) return;

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`/api/v1/approval-policies/${policyId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error("Failed to delete rule");

      success("Rule deleted!");
      loadPolicies();
    } catch (err) {
      showError(err.message);
    }
  };

  const handleToggleActive = async (policy) => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`/api/v1/approval-policies/${policy.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          is_active: !policy.is_active,
        }),
      });

      if (!response.ok) throw new Error("Failed to update rule");

      success(
        policy.is_active ? "Rule deactivated!" : "Rule activated!"
      );
      loadPolicies();
    } catch (err) {
      showError(err.message);
    }
  };

  const handleTest = async (e) => {
    e.preventDefault();

    // Validate amount before sending
    const amount = parseFloat(testData.amount);
    if (isNaN(amount) || amount <= 0) {
      showError("Please enter a valid amount greater than 0");
      return;
    }

    try {
      const token = localStorage.getItem("access_token");

      // Build payload with parsed numeric values
      const payload = {
        amount: amount,
        category: testData.category,
        vendor: testData.vendor,
        has_receipt: testData.has_receipt,
        test_limit_type: testData.test_limit_type || null,
      };

      const response = await fetch("/api/v1/approval-policies/test", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const errorMsg = errorData?.detail || "Failed to test rules";
        throw new Error(errorMsg);
      }

      const result = await response.json();
      setTestResult(result);
    } catch (err) {
      showError(err.message);
      setTestResult(null);
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      priority: "medium",
      auto_approve: true,
      require_receipt: false,
      notify_on_auto_approve: true,
      max_amount_per_expense: "",
      daily_limit_per_user: "",
      monthly_limit_per_user: "",
      yearly_limit_per_user: "",
      conditions: {
        categories: [],
        vendors: [],
        exclude_vendors: [],
        min_amount: "",
      },
    });
  };

  const startEdit = (policy) => {
    setEditingPolicy(policy);
    setFormData({
      name: policy.name,
      description: policy.description || "",
      priority: getPriorityLabel(policy.priority), // Convert numeric to text
      auto_approve: policy.auto_approve,
      require_receipt: policy.require_receipt,
      notify_on_auto_approve: policy.notify_on_auto_approve,
      max_amount_per_expense: policy.limits?.max_amount_per_expense || "",
      daily_limit_per_user: policy.limits?.daily_limit_per_user || "",
      monthly_limit_per_user: policy.limits?.monthly_limit_per_user || "",
      yearly_limit_per_user: policy.limits?.yearly_limit_per_user || "",
      conditions: policy.conditions || {
        categories: [],
        vendors: [],
        exclude_vendors: [],
        min_amount: "",
      },
    });
    setShowCreateForm(true);
  };

  const toggleCategory = (category) => {
    setFormData((prev) => ({
      ...prev,
      conditions: {
        ...prev.conditions,
        categories: prev.conditions.categories.includes(category)
          ? prev.conditions.categories.filter((c) => c !== category)
          : [...prev.conditions.categories, category],
      },
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading approval rules...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Approval Rules
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Reduce your approval workload with automatic rule-based approvals
          </p>
        </div>
        <button
          onClick={() => {
            setShowCreateForm(true);
            setEditingPolicy(null);
            resetForm();
          }}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="h-5 w-5 mr-2" />
          Create Rule
        </button>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <CheckCircle className="h-5 w-5 text-blue-600 mt-0.5" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              How Approval Rules Work
            </h3>
            <p className="mt-1 text-sm text-blue-700">
              <strong>Save time on routine approvals.</strong> Rules automatically approve expenses that match your conditions (amount, category, etc.).
              Rules are checked in priority order - if an expense matches a rule and stays within limits, it's instantly approved without manual review.
              All other expenses still require your approval.
            </p>
            <p className="mt-2 text-xs text-blue-600">
              💡 Example: "Auto-approve meals under $50 with receipt" - instantly approves qualifying lunch expenses
            </p>
          </div>
        </div>
      </div>

      {/* Create/Edit Form */}
      {showCreateForm && (
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">
              {editingPolicy ? "Edit Rule" : "Create New Approval Rule"}
            </h3>
            <button
              onClick={() => {
                setShowCreateForm(false);
                setEditingPolicy(null);
                resetForm();
              }}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Rule Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g., Small Meal Expenses"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Priority
                </label>
                <select
                  value={formData.priority}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      priority: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  High priority rules are checked first
                </p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                rows="2"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., Auto-approve small team meals to save time"
              />
            </div>

            {/* Amount Limits */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                <DollarSign className="h-4 w-4 mr-2 text-green-600" />
                Amount Limits
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-700 mb-2">
                    Max per expense ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.max_amount_per_expense}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        max_amount_per_expense: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="e.g., 100.00"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-700 mb-2">
                    Min amount ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.conditions.min_amount}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        conditions: {
                          ...formData.conditions,
                          min_amount: e.target.value,
                        },
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="Optional"
                  />
                </div>
              </div>
            </div>

            {/* User Spending Limits */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                <Users className="h-4 w-4 mr-2 text-blue-600" />
                Per-User Spending Limits
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm text-gray-700 mb-2">
                    Daily limit ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.daily_limit_per_user}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        daily_limit_per_user: e.target.value,
                      })
                    }
                    className={`w-full px-3 py-2 border rounded-md ${
                      formData.max_amount_per_expense &&
                      formData.daily_limit_per_user &&
                      parseFloat(formData.daily_limit_per_user) <
                        parseFloat(formData.max_amount_per_expense)
                        ? "border-red-300 bg-red-50"
                        : "border-gray-300"
                    }`}
                    placeholder="Optional"
                  />
                  {formData.max_amount_per_expense &&
                    formData.daily_limit_per_user &&
                    parseFloat(formData.daily_limit_per_user) <
                      parseFloat(formData.max_amount_per_expense) && (
                      <p className="mt-1 text-xs text-red-600 flex items-center">
                        <AlertTriangle className="h-3 w-3 mr-1" />
                        Must be ≥ ${formData.max_amount_per_expense} (max per
                        expense)
                      </p>
                    )}
                </div>

                <div>
                  <label className="block text-sm text-gray-700 mb-2">
                    Monthly limit ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.monthly_limit_per_user}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        monthly_limit_per_user: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="Optional"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-700 mb-2">
                    Yearly limit ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.yearly_limit_per_user}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        yearly_limit_per_user: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="Optional"
                  />
                </div>
              </div>
            </div>

            {/* Categories */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                <Tag className="h-4 w-4 mr-2 text-purple-600" />
                Allowed Categories
              </h4>
              <p className="text-xs text-gray-500 mb-3">
                Leave empty to allow all categories
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {EXPENSE_CATEGORIES.map((category) => (
                  <label
                    key={category}
                    className="flex items-center space-x-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={formData.conditions.categories.includes(
                        category
                      )}
                      onChange={() => toggleCategory(category)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">{category}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Options */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-3">
                Options
              </h4>
              <div className="space-y-2">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.auto_approve}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        auto_approve: e.target.checked,
                      })
                    }
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">
                    Auto-approve matching expenses
                  </span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.notify_on_auto_approve}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        notify_on_auto_approve: e.target.checked,
                      })
                    }
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">
                    Notify user on auto-approval
                  </span>
                </label>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end space-x-3 pt-4 border-t">
              <button
                type="button"
                onClick={() => {
                  setShowCreateForm(false);
                  setEditingPolicy(null);
                  resetForm();
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                <Save className="h-4 w-4 mr-2" />
                {editingPolicy ? "Update Rule" : "Create Rule"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Test Rules */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <TestTube className="h-5 w-5 mr-2 text-orange-600" />
          Test Your Rules
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Check if a sample expense would be automatically approved by your current rules
        </p>

        <form onSubmit={handleTest} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Amount ($)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                required
                value={testData.amount}
                onChange={(e) =>
                  setTestData({ ...testData, amount: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="50.00"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Test Limit
              </label>
              <select
                value={testData.test_limit_type}
                onChange={(e) =>
                  setTestData({ ...testData, test_limit_type: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">Per-expense only</option>
                <option value="daily">Daily limit</option>
                <option value="monthly">Monthly limit</option>
                <option value="yearly">Yearly limit</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <select
                value={testData.category}
                onChange={(e) =>
                  setTestData({ ...testData, category: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">All Categories</option>
                {EXPENSE_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Vendor
              </label>
              <input
                type="text"
                value={testData.vendor}
                onChange={(e) =>
                  setTestData({ ...testData, vendor: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="e.g., Amazon"
              />
            </div>
          </div>

          <div className="mt-4">
            <button
              type="submit"
              className="w-full px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-orange-600 hover:bg-orange-700"
            >
              Test
            </button>
          </div>
        </form>

        {testResult && (
          <div
            className={`mt-4 p-4 rounded-lg ${
              testResult.would_auto_approve
                ? "bg-green-50 border border-green-200"
                : "bg-yellow-50 border border-yellow-200"
            }`}
          >
            <div className="flex items-start">
              {testResult.would_auto_approve ? (
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
              ) : (
                <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
              )}
              <div className="ml-3">
                <h4
                  className={`text-sm font-medium ${
                    testResult.would_auto_approve
                      ? "text-green-800"
                      : "text-yellow-800"
                  }`}
                >
                  {testResult.would_auto_approve
                    ? "✓ Would Auto-Approve"
                    : `⚠ ${testResult.reason}`}
                </h4>
                {testResult.would_auto_approve && (
                  <p
                    className="mt-1 text-sm text-green-700"
                  >
                    {testResult.reason}
                  </p>
                )}
                {testResult.matching_policy && (
                  <p className="mt-2 text-xs text-gray-600">
                    Matched Rule: <strong>{testResult.matching_policy.name}</strong>
                  </p>
                )}
                {testResult.remaining_limits && (
                  <div className="mt-2 text-xs text-gray-600">
                    <strong>Remaining Limits:</strong>
                    {testResult.remaining_limits.daily_remaining && (
                      <span className="ml-2">
                        Daily: ${testResult.remaining_limits.daily_remaining}
                      </span>
                    )}
                    {testResult.remaining_limits.monthly_remaining && (
                      <span className="ml-2">
                        Monthly: ${testResult.remaining_limits.monthly_remaining}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Rules List */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Your Approval Rules ({policies.length})
          </h3>
        </div>

        {policies.length === 0 ? (
          <div className="p-12 text-center">
            <CheckCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No approval rules yet
            </h3>
            <p className="text-gray-500 mb-4">
              Create your first rule to automatically approve routine expenses and save time
            </p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="h-5 w-5 mr-2" />
              Create Rule
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {policies
              .sort((a, b) => b.priority - a.priority)
              .map((policy) => (
                <div
                  key={policy.id}
                  className={`p-6 ${
                    !policy.is_active ? "bg-gray-50" : ""
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <h4 className="text-lg font-medium text-gray-900">
                          {policy.name}
                        </h4>
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            policy.is_active
                              ? "bg-green-100 text-green-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {policy.is_active ? "Active" : "Inactive"}
                        </span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          getPriorityLabel(policy.priority) === "high"
                            ? "bg-red-100 text-red-800"
                            : getPriorityLabel(policy.priority) === "medium"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-gray-100 text-gray-800"
                        }`}>
                          {getPriorityLabel(policy.priority).charAt(0).toUpperCase() + getPriorityLabel(policy.priority).slice(1)} Priority
                        </span>
                      </div>

                      {policy.description && (
                        <p className="mt-1 text-sm text-gray-600">
                          {policy.description}
                        </p>
                      )}

                      <div className="mt-3 flex flex-wrap gap-2 text-sm text-gray-600">
                        {policy.limits?.max_amount_per_expense && (
                          <span className="inline-flex items-center px-2 py-1 rounded bg-gray-100">
                            <DollarSign className="h-3 w-3 mr-1" />
                            Max: ${policy.limits.max_amount_per_expense}
                          </span>
                        )}
                        {policy.limits?.daily_limit_per_user && (
                          <span className="inline-flex items-center px-2 py-1 rounded bg-gray-100">
                            <Calendar className="h-3 w-3 mr-1" />
                            Daily: ${policy.limits.daily_limit_per_user}
                          </span>
                        )}
                        {policy.limits?.monthly_limit_per_user && (
                          <span className="inline-flex items-center px-2 py-1 rounded bg-gray-100">
                            <TrendingUp className="h-3 w-3 mr-1" />
                            Monthly: ${policy.limits.monthly_limit_per_user}
                          </span>
                        )}
                        {policy.limits?.yearly_limit_per_user && (
                          <span className="inline-flex items-center px-2 py-1 rounded bg-gray-100">
                            <TrendingUp className="h-3 w-3 mr-1" />
                            Yearly: ${policy.limits.yearly_limit_per_user}
                          </span>
                        )}
                        <span className="inline-flex items-center px-2 py-1 rounded bg-purple-100 text-purple-700">
                          <Tag className="h-3 w-3 mr-1" />
                          {policy.conditions?.categories?.length > 0
                            ? policy.conditions.categories.length === 1
                              ? policy.conditions.categories[0]
                              : `${policy.conditions.categories.length} categories: ${policy.conditions.categories.join(", ")}`
                            : "All Categories"
                          }
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 ml-4">
                      <button
                        onClick={() => handleToggleActive(policy)}
                        className={`p-2 rounded-md ${
                          policy.is_active
                            ? "text-green-600 hover:bg-green-50"
                            : "text-gray-400 hover:bg-gray-100"
                        }`}
                        title={policy.is_active ? "Deactivate" : "Activate"}
                      >
                        <Power className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => startEdit(policy)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-md"
                        title="Edit"
                      >
                        <Edit2 className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleDelete(policy.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-md"
                        title="Delete"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ApprovalPolicies;
