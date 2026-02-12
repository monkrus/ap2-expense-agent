import React, { useState } from "react";
import {
  Plus,
  Target,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Edit2,
  Trash2,
  Eye,
  DollarSign,
  Calendar,
  Tag,
  Store,
  Shield,
  Copy,
} from "lucide-react";
import { useToast } from "../hooks/useToast";
import { useOrganization } from "../contexts/OrganizationContext";

const IntentMandateManager = ({
  mandates,
  onRefresh,
  onCreateMandate,
  showArchived,
  setShowArchived
}) => {
  const { success, error: showError } = useToast();
  const [expandedMandate, setExpandedMandate] = useState(null);
  const [filter, setFilter] = useState("all"); // 'all', 'active', 'expired', 'revoked'

  // Filter mandates to show only intent type
  const intentMandates = mandates.filter((m) => m.type === "intent");

  // Apply status filter
  const filteredMandates = intentMandates.filter((mandate) => {
    if (filter === "all") return true;
    if (filter === "archived") return mandate.status === "deleted" || mandate.status === "revoked";
    return mandate.status === filter;
  });

  const handleDeleteMandate = async (mandateId) => {
    if (!confirm("Are you sure you want to delete this authorization?")) {
      return;
    }

    try {
      const response = await fetch(`/api/ap2/mandate/${mandateId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      if (response.ok) {
        success("Authorization deleted successfully");
        onRefresh();
      } else {
        throw new Error("Failed to delete");
      }
    } catch (err) {
      showError("Failed to delete authorization");
      console.error(err);
    }
  };

  const handleRevokeMandate = async (mandateId) => {
    const reason = prompt("Please provide a reason for revoking this authorization (required for audit):");
    if (!reason || !reason.trim()) {
      return;
    }

    try {
      const response = await fetch(`/api/ap2/intent-mandate/${mandateId}/revoke`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({
          reason: reason.trim(),
          revoke_dependents: true,
        }),
      });

      if (response.ok) {
        success("Authorization revoked successfully");
        onRefresh();
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to revoke");
      }
    } catch (err) {
      showError(err.message || "Failed to revoke authorization");
      console.error(err);
    }
  };

  const toggleExpanded = (mandateId) => {
    setExpandedMandate(expandedMandate === mandateId ? null : mandateId);
  };

  const getStatusBadge = (status) => {
    const badges = {
      active: { bg: "bg-green-100", text: "text-green-800", icon: CheckCircle },
      expired: { bg: "bg-gray-100", text: "text-gray-800", icon: Clock },
      revoked: { bg: "bg-orange-100", text: "text-orange-800", icon: XCircle },
      failed: { bg: "bg-red-100", text: "text-red-800", icon: XCircle },
      deleted: { bg: "bg-gray-100", text: "text-gray-600", icon: Trash2 },
    };

    const badge = badges[status] || { bg: "bg-gray-100", text: "text-gray-800", icon: AlertCircle };
    const Icon = badge.icon;

    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}
      >
        <Icon className="w-3 h-3 mr-1" />
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Reusable Authorizations</h2>
          <p className="text-gray-600 mt-1">
            Create standing authorizations for ongoing AI purchases. These can be used multiple times for automatic expense approvals.
          </p>
        </div>
        <button
          onClick={onCreateMandate}
          className="bg-purple-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-purple-700 transition-colors flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>New Authorization</span>
        </button>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <Shield className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
          <div className="text-sm text-blue-900">
            <p className="font-medium mb-1">Standing Authorizations for Ongoing Automation</p>
            <p>
              Create reusable authorizations that your AI agent can use multiple times.
              Perfect for recurring purchases like monthly software subscriptions, office supplies, or regular travel expenses.
            </p>
            <p className="mt-2 text-xs">
              <strong>Need a one-time purchase?</strong> Use the "One-time Authorization" tab for quick autonomous purchases without setting up ongoing authorization.
            </p>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-1 inline-flex space-x-1">
        {["all", "active", "expired", "revoked", "archived"].map((filterOption) => (
          <button
            key={filterOption}
            onClick={() => {
              setFilter(filterOption);
              if (filterOption === "archived") setShowArchived(true);
            }}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              filter === filterOption
                ? "bg-purple-100 text-purple-700"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
            <span className="ml-2 text-xs opacity-60">
              (
              {filterOption === "archived"
                ? intentMandates.filter((m) => m.status === "deleted" || m.status === "revoked").length
                : intentMandates.filter(
                    (m) => filterOption === "all" || m.status === filterOption,
                  ).length
              }
              )
            </span>
          </button>
        ))}
      </div>

      {/* Mandates List */}
      {filteredMandates.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <Target className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Reusable Authorizations Found
          </h3>
          <p className="text-gray-600 max-w-md mx-auto">
            {filter === "all"
              ? "Create your first reusable authorization using the button above."
              : `No authorizations with "${filter}" status.`}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredMandates.map((mandate) => (
            <MandateCard
              key={mandate.id}
              mandate={mandate}
              expanded={expandedMandate === mandate.id}
              onToggle={() => toggleExpanded(mandate.id)}
              onDelete={() => handleDeleteMandate(mandate.id)}
              onRevoke={() => handleRevokeMandate(mandate.id)}
              getStatusBadge={getStatusBadge}
            />
          ))}
        </div>
      )}

      {/* Show Archived Toggle - always visible */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <label className="flex items-center space-x-2 text-sm text-gray-600 cursor-pointer hover:text-gray-900 transition-colors">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
          />
          <span>Show archived items</span>
          {showArchived && (
            <span className="text-xs text-gray-500">
              (Including{" "}
              {intentMandates.filter(m => m.status === 'deleted' || m.status === 'revoked').length}{" "}
              deleted/revoked)
            </span>
          )}
        </label>
      </div>
    </div>
  );
};

// Mandate Card Component
const MandateCard = ({
  mandate,
  expanded,
  onToggle,
  onDelete,
  onRevoke,
  getStatusBadge,
}) => {
  const { formatDate, timezone } = useOrganization();

  // Parse constraints (they might be stored as JSON string)
  let constraints = {};
  try {
    constraints =
      typeof mandate.constraints === "string"
        ? JSON.parse(mandate.constraints)
        : mandate.constraints || {};
  } catch (e) {
    console.error("Error parsing constraints:", e);
  }

  const isArchived = mandate.status === "deleted" || mandate.status === "revoked";

  return (
    <div className={`rounded-xl shadow-sm border overflow-hidden hover:shadow-md transition-shadow ${isArchived ? "bg-gray-50 border-gray-300 opacity-75" : "bg-white border-gray-200"}`}>
      {/* Header */}
      <div className="px-6 py-4 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              {getStatusBadge(mandate.status)}
              {isArchived && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-600">
                  Archived
                </span>
              )}
              <span className="text-sm font-mono text-gray-500 inline-flex items-center">
                #{mandate.id.slice(-12)}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigator.clipboard.writeText(mandate.id);
                  }}
                  className="ml-1.5 p-0.5 text-gray-400 hover:text-purple-600 transition-colors"
                  title="Copy full ID"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </span>
            </div>
            <div className="space-y-2">
              {/* Quick Summary */}
              <div className="flex flex-wrap gap-3 text-sm">
                {constraints.max_amount && (
                  <span className="inline-flex items-center px-2 py-1 bg-green-50 text-green-700 rounded">
                    <DollarSign className="w-3 h-3 mr-1" />
                    ${parseFloat(constraints.max_amount).toFixed(0)} max
                  </span>
                )}
                {constraints.monthly_limit && (
                  <span className="inline-flex items-center px-2 py-1 bg-orange-50 text-orange-700 rounded">
                    <DollarSign className="w-3 h-3 mr-1" />
                    ${parseFloat(constraints.monthly_limit).toFixed(0)}/mo
                  </span>
                )}
                {(constraints.merchant || (constraints.merchants && constraints.merchants.length > 0)) && (
                  <span className="inline-flex items-center px-2 py-1 bg-purple-50 text-purple-700 rounded">
                    <Store className="w-3 h-3 mr-1" />
                    {constraints.merchant || constraints.merchants[0]}
                    {constraints.merchants && constraints.merchants.length > 1 && ` +${constraints.merchants.length - 1}`}
                  </span>
                )}
                {(constraints.category || (constraints.categories && constraints.categories.length > 0)) && (
                  <span className="inline-flex items-center px-2 py-1 bg-blue-50 text-blue-700 rounded">
                    <Tag className="w-3 h-3 mr-1" />
                    {constraints.category || constraints.categories[0]}
                    {constraints.categories && constraints.categories.length > 1 && ` +${constraints.categories.length - 1}`}
                  </span>
                )}
              </div>

              {/* Dates */}
              <div className="flex items-center space-x-6 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <Calendar className="w-4 h-4" />
                  <span>Created {formatDate(mandate.created_at)}</span>
                </div>
                {mandate.expiration && (
                  <div className="flex items-center space-x-1">
                    <Clock className="w-4 h-4" />
                    <span>Expires {formatDate(mandate.expiration)}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {mandate.status === "active" && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRevoke();
                }}
                className="px-3 py-1.5 text-orange-600 bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-lg transition-colors text-sm font-medium flex items-center space-x-1"
                title="Revoke authorization"
              >
                <XCircle className="w-4 h-4" />
                <span>Revoke</span>
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Delete"
            >
              <Trash2 className="w-5 h-5" />
            </button>
            {expanded ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <h4 className="font-semibold text-gray-900 mb-4 flex items-center space-x-2">
            <Shield className="w-5 h-5" />
            <span>Constraints & Rules</span>
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Max Amount */}
            {constraints.max_amount && (
              <ConstraintItem
                icon={<DollarSign className="w-5 h-5 text-green-600" />}
                label="Maximum per Transaction"
                value={`$${parseFloat(constraints.max_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              />
            )}

            {/* Monthly Limit */}
            {constraints.monthly_limit && (
              <ConstraintItem
                icon={<DollarSign className="w-5 h-5 text-orange-600" />}
                label="Monthly Spending Limit"
                value={`$${parseFloat(constraints.monthly_limit).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              />
            )}

            {/* Categories (array or single) */}
            {(constraints.categories && constraints.categories.length > 0) || constraints.category ? (
              <ConstraintItem
                icon={<Tag className="w-5 h-5 text-blue-600" />}
                label="Allowed Categories"
                value={
                  constraints.categories
                    ? constraints.categories.join(", ")
                    : constraints.category
                }
              />
            ) : null}

            {/* Merchants (array or single) */}
            {(constraints.merchants && constraints.merchants.length > 0) || constraints.merchant ? (
              <ConstraintItem
                icon={<Store className="w-5 h-5 text-purple-600" />}
                label="Allowed Merchants"
                value={
                  constraints.merchants
                    ? constraints.merchants.join(", ")
                    : constraints.merchant
                }
              />
            ) : null}

            {/* Usage Limit */}
            {constraints.usage_limit && (
              <ConstraintItem
                icon={<Target className="w-5 h-5 text-red-600" />}
                label="Usage Limit"
                value={`Can be used ${constraints.usage_limit} time${constraints.usage_limit > 1 ? 's' : ''}`}
              />
            )}

            {/* Approval Required */}
            {constraints.approval_required !== undefined && (
              <ConstraintItem
                icon={<CheckCircle className="w-5 h-5 text-yellow-600" />}
                label="Approval Mode"
                value={
                  constraints.approval_required ? "Manual Approval" : "Auto-approve"
                }
              />
            )}

            {/* Recurring */}
            {constraints.recurring && (
              <ConstraintItem
                icon={<Clock className="w-5 h-5 text-indigo-600" />}
                label="Recurring Pattern"
                value={constraints.recurring.charAt(0).toUpperCase() + constraints.recurring.slice(1)}
              />
            )}

            {/* Custom Constraints */}
            {Object.keys(constraints)
              .filter(
                (key) =>
                  ![
                    "max_amount",
                    "monthly_limit",
                    "categories",
                    "category",
                    "merchants",
                    "merchant",
                    "approval_required",
                    "recurring",
                    "usage_limit",
                  ].includes(key),
              )
              .map((key) => (
                <ConstraintItem
                  key={key}
                  icon={<AlertCircle className="w-5 h-5 text-gray-600" />}
                  label={key
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (c) => c.toUpperCase())}
                  value={String(constraints[key])}
                />
              ))}
          </div>

          {/* Signature Info */}
          {mandate.signature && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="flex items-start space-x-2">
                <Shield className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    Cryptographic Signature
                  </p>
                  <p className="text-xs text-gray-600 font-mono break-all mt-1">
                    {mandate.signature.slice(0, 64)}...
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Constraint Item Component
const ConstraintItem = ({ icon, label, value }) => {
  return (
    <div className="flex items-start space-x-3 p-3 bg-white rounded-lg border border-gray-200">
      <div className="flex-shrink-0">{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="text-sm font-medium text-gray-900 mt-1 break-words">
          {value}
        </p>
      </div>
    </div>
  );
};

export default IntentMandateManager;
