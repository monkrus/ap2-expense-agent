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
} from "lucide-react";
import { useToast } from "../hooks/useToast";

const IntentMandateManager = ({ mandates, onRefresh, onCreateMandate }) => {
  const { success, error: showError } = useToast();
  const [expandedMandate, setExpandedMandate] = useState(null);
  const [filter, setFilter] = useState("all"); // 'all', 'active', 'expired', 'used'

  // Filter mandates to show only intent type
  const intentMandates = mandates.filter((m) => m.type === "intent");

  // Apply status filter
  const filteredMandates = intentMandates.filter((mandate) => {
    if (filter === "all") return true;
    return mandate.status === filter;
  });

  const handleDeleteMandate = async (mandateId) => {
    if (!confirm("Are you sure you want to delete this Intent Mandate?")) {
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
        success("Intent Mandate deleted successfully");
        onRefresh();
      } else {
        throw new Error("Failed to delete mandate");
      }
    } catch (err) {
      showError("Failed to delete Intent Mandate");
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
      used: { bg: "bg-blue-100", text: "text-blue-800", icon: CheckCircle },
      failed: { bg: "bg-red-100", text: "text-red-800", icon: XCircle },
    };

    const badge = badges[status] || badges.active;
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
          <h2 className="text-2xl font-bold text-gray-900">Intent Mandates</h2>
          <p className="text-gray-600 mt-1">
            Manage your AI agent's authorization to make purchases on your
            behalf
          </p>
        </div>
        <button
          onClick={onCreateMandate}
          className="bg-purple-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-purple-700 transition-colors flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>New Mandate</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-1 inline-flex space-x-1">
        {["all", "active", "expired", "used"].map((filterOption) => (
          <button
            key={filterOption}
            onClick={() => setFilter(filterOption)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              filter === filterOption
                ? "bg-purple-100 text-purple-700"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
            <span className="ml-2 text-xs opacity-60">
              (
              {
                intentMandates.filter(
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
            No Intent Mandates Yet
          </h3>
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            Create your first Intent Mandate to authorize your AI agent to
            handle expenses automatically.
          </p>
          <button
            onClick={onCreateMandate}
            className="bg-purple-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-purple-700 transition-colors inline-flex items-center space-x-2"
          >
            <Plus className="w-5 h-5" />
            <span>Create Intent Mandate</span>
          </button>
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
              getStatusBadge={getStatusBadge}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Mandate Card Component
const MandateCard = ({
  mandate,
  expanded,
  onToggle,
  onDelete,
  getStatusBadge,
}) => {
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

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

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="px-6 py-4 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              {getStatusBadge(mandate.status)}
              <span className="text-sm font-mono text-gray-500">
                #{mandate.id.slice(-12)}
              </span>
            </div>
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
          <div className="flex items-center space-x-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Delete mandate"
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
                label="Maximum Amount"
                value={`$${parseFloat(constraints.max_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              />
            )}

            {/* Categories */}
            {constraints.categories && constraints.categories.length > 0 && (
              <ConstraintItem
                icon={<Tag className="w-5 h-5 text-blue-600" />}
                label="Allowed Categories"
                value={constraints.categories.join(", ")}
              />
            )}

            {/* Merchants */}
            {constraints.merchants && constraints.merchants.length > 0 && (
              <ConstraintItem
                icon={<Store className="w-5 h-5 text-purple-600" />}
                label="Allowed Merchants"
                value={constraints.merchants.join(", ")}
              />
            )}

            {/* Approval Required */}
            {constraints.approval_required !== undefined && (
              <ConstraintItem
                icon={<CheckCircle className="w-5 h-5 text-yellow-600" />}
                label="Approval Required"
                value={
                  constraints.approval_required ? "Yes" : "No (Auto-approve)"
                }
              />
            )}

            {/* Recurring */}
            {constraints.recurring && (
              <ConstraintItem
                icon={<Clock className="w-5 h-5 text-indigo-600" />}
                label="Recurring"
                value={constraints.recurring}
              />
            )}

            {/* Custom Constraints */}
            {Object.keys(constraints)
              .filter(
                (key) =>
                  ![
                    "max_amount",
                    "categories",
                    "merchants",
                    "approval_required",
                    "recurring",
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
