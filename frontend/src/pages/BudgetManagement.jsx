import React, { useState, useEffect } from "react";
import {
  DollarSign,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Plus,
  Edit2,
  Trash2,
  Eye,
  Filter,
} from "lucide-react";
import { useToast } from "../hooks/useToast";
import { useAuth } from "../contexts/AuthContext";
import BudgetForm from "../components/BudgetForm";

const BudgetManagement = () => {
  const { user } = useAuth();
  const { success: showSuccess, error: showError } = useToast();

  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showBudgetForm, setShowBudgetForm] = useState(false);
  const [selectedBudget, setSelectedBudget] = useState(null);
  const [filter, setFilter] = useState("all"); // all, on_track, warning, critical, exceeded
  const [showActiveOnly, setShowActiveOnly] = useState(true);

  // Fetch budgets
  useEffect(() => {
    fetchBudgets();
  }, [showActiveOnly]);

  const fetchBudgets = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("access_token");
      const response = await fetch(
        `/api/budgets?active_only=${showActiveOnly}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (!response.ok) {
        throw new Error("Failed to load budgets");
      }

      const data = await response.json();
      setBudgets(data);
    } catch (err) {
      showError(err.message || "Failed to load budgets");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBudget = () => {
    setSelectedBudget(null);
    setShowBudgetForm(true);
  };

  const handleEditBudget = (budget) => {
    setSelectedBudget(budget);
    setShowBudgetForm(true);
  };

  const handleDeleteBudget = async (budgetId) => {
    if (
      !confirm(
        "Are you sure you want to delete this budget? This action cannot be undone.",
      )
    ) {
      return;
    }

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`/api/budgets/${budgetId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to delete budget");
      }

      showSuccess("Budget deleted successfully");
      fetchBudgets();
    } catch (err) {
      showError(err.message || "Failed to delete budget");
      console.error(err);
    }
  };

  const handleBudgetFormSuccess = () => {
    setShowBudgetForm(false);
    setSelectedBudget(null);
    fetchBudgets();
  };

  // Calculate stats
  const stats = budgets.reduce(
    (acc, budget) => {
      acc.total++;
      if (budget.status === "on_track") acc.on_track++;
      if (budget.status === "warning") acc.warning++;
      if (budget.status === "critical") acc.critical++;
      if (budget.status === "exceeded") acc.exceeded++;
      acc.totalBudget += budget.amount;
      acc.totalSpent += budget.current_spending;
      return acc;
    },
    {
      total: 0,
      on_track: 0,
      warning: 0,
      critical: 0,
      exceeded: 0,
      totalBudget: 0,
      totalSpent: 0,
    },
  );

  // Filter budgets
  const filteredBudgets =
    filter === "all" ? budgets : budgets.filter((b) => b.status === filter);

  const getStatusColor = (status) => {
    switch (status) {
      case "on_track":
        return "bg-green-100 text-green-800";
      case "warning":
        return "bg-yellow-100 text-yellow-800";
      case "critical":
        return "bg-orange-100 text-orange-800";
      case "exceeded":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "on_track":
        return <CheckCircle className="w-4 h-4" />;
      case "warning":
        return <AlertTriangle className="w-4 h-4" />;
      case "critical":
        return <AlertTriangle className="w-4 h-4" />;
      case "exceeded":
        return <AlertTriangle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getProgressBarColor = (status) => {
    switch (status) {
      case "on_track":
        return "bg-green-500";
      case "warning":
        return "bg-yellow-500";
      case "critical":
        return "bg-orange-500";
      case "exceeded":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const isAdmin = user?.role === "admin";
  const isManager = user?.role === "manager";
  const canManageBudgets = isAdmin || isManager;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-3xl font-bold text-gray-900">
              Budget Management
            </h1>
            {canManageBudgets && (
              <button
                onClick={handleCreateBudget}
                className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
              >
                <Plus className="w-5 h-5" />
                Create Budget
              </button>
            )}
          </div>
          <p className="text-gray-600">
            Monitor and manage organizational budgets
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-gray-600 text-sm">Total Budgets</p>
              <DollarSign className="w-8 h-8 text-indigo-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            <p className="text-sm text-gray-500 mt-1">Active budgets</p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-gray-600 text-sm">Total Budget Amount</p>
              <TrendingUp className="w-8 h-8 text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              ${formatCurrency(stats.totalBudget)}
            </p>
            <p className="text-sm text-gray-500 mt-1">Combined budget</p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-gray-600 text-sm">Total Spent</p>
              <DollarSign className="w-8 h-8 text-purple-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              ${formatCurrency(stats.totalSpent)}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {stats.totalBudget > 0
                ? Math.round((stats.totalSpent / stats.totalBudget) * 100)
                : 0}
              % utilized
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-gray-600 text-sm">Budget Status</p>
              <AlertTriangle className="w-8 h-8 text-yellow-600" />
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-green-600">
                  {stats.on_track} On Track
                </span>
                <span className="text-yellow-600">{stats.warning} Warning</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-orange-600">
                  {stats.critical} Critical
                </span>
                <span className="text-red-600">{stats.exceeded} Exceeded</span>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Filter:</span>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setFilter("all")}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  filter === "all"
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                All ({budgets.length})
              </button>
              <button
                onClick={() => setFilter("on_track")}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  filter === "on_track"
                    ? "bg-green-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                On Track ({stats.on_track})
              </button>
              <button
                onClick={() => setFilter("warning")}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  filter === "warning"
                    ? "bg-yellow-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                Warning ({stats.warning})
              </button>
              <button
                onClick={() => setFilter("critical")}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  filter === "critical"
                    ? "bg-orange-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                Critical ({stats.critical})
              </button>
              <button
                onClick={() => setFilter("exceeded")}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  filter === "exceeded"
                    ? "bg-red-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                Exceeded ({stats.exceeded})
              </button>
            </div>

            <div className="ml-auto flex items-center gap-2">
              <input
                type="checkbox"
                id="activeOnly"
                checked={showActiveOnly}
                onChange={(e) => setShowActiveOnly(e.target.checked)}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="activeOnly" className="text-sm text-gray-700">
                Active only
              </label>
            </div>
          </div>
        </div>

        {/* Budget List */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b">
            <h2 className="text-xl font-semibold text-gray-900">
              Budgets ({filteredBudgets.length})
            </h2>
          </div>

          {loading ? (
            <div className="p-12 text-center">
              <div className="inline-block w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-4 text-gray-600">Loading budgets...</p>
            </div>
          ) : filteredBudgets.length === 0 ? (
            <div className="p-12 text-center">
              <DollarSign className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 mb-2">No budgets found</p>
              {canManageBudgets && (
                <button
                  onClick={handleCreateBudget}
                  className="text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  Create your first budget
                </button>
              )}
            </div>
          ) : (
            <div className="divide-y">
              {filteredBudgets.map((budget) => (
                <div
                  key={budget.id}
                  className="p-6 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">
                          {budget.name}
                        </h3>
                        <span
                          className={`px-2 py-1 text-xs font-medium rounded-full flex items-center gap-1 ${getStatusColor(budget.status)}`}
                        >
                          {getStatusIcon(budget.status)}
                          {budget.status.replace("_", " ").toUpperCase()}
                        </span>
                        {!budget.is_active && (
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
                            INACTIVE
                          </span>
                        )}
                      </div>

                      {budget.description && (
                        <p className="text-sm text-gray-600 mb-2">
                          {budget.description}
                        </p>
                      )}

                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span className="capitalize">{budget.period}</span>
                        {budget.category && <span>• {budget.category}</span>}
                        {budget.user_id && <span>• User-specific</span>}
                        <span>
                          • Started{" "}
                          {new Date(budget.start_date).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    {canManageBudgets && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleEditBudget(budget)}
                          className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                          title="Edit budget"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        {isAdmin && (
                          <button
                            onClick={() => handleDeleteBudget(budget.id)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Delete budget"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="font-medium text-gray-700">
                        ${formatCurrency(budget.current_spending)} / $
                        {formatCurrency(budget.amount)}
                      </span>
                      <span className="font-medium text-gray-700">
                        {budget.percentage_used.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${getProgressBarColor(budget.status)}`}
                        style={{
                          width: `${Math.min(budget.percentage_used, 100)}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Thresholds */}
                  <div className="flex items-center gap-6 text-xs text-gray-600">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
                      <span>Warning at {budget.warning_threshold}%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                      <span>Critical at {budget.critical_threshold}%</span>
                    </div>
                    <div className="ml-auto font-medium">
                      Remaining: ${formatCurrency(budget.remaining)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Budget Form Modal */}
      {showBudgetForm && (
        <BudgetForm
          budget={selectedBudget}
          onSuccess={handleBudgetFormSuccess}
          onCancel={() => {
            setShowBudgetForm(false);
            setSelectedBudget(null);
          }}
        />
      )}
    </div>
  );
};

export default BudgetManagement;
