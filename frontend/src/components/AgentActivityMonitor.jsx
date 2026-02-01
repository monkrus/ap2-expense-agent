import React, { useState, useEffect } from "react";
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  TrendingUp,
  Target,
  DollarSign,
  Calendar,
  ChevronRight,
  Filter,
  Download,
  Search,
} from "lucide-react";

const AgentActivityMonitor = ({ mandates, stats }) => {
  const [filter, setFilter] = useState("all"); // 'all', 'intent', 'cart', 'payment'
  const [statusFilter, setStatusFilter] = useState("all"); // 'all', 'active', 'pending', 'completed', 'failed'
  const [searchQuery, setSearchQuery] = useState("");
  const [sortedMandates, setSortedMandates] = useState([]);

  // Sort and filter mandates
  useEffect(() => {
    let filtered = [...mandates];

    // Type filter
    if (filter !== "all") {
      filtered = filtered.filter((m) => m.type === filter);
    }

    // Status filter
    if (statusFilter !== "all") {
      filtered = filtered.filter((m) => m.status === statusFilter);
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (m) =>
          // Search by ID
          m.id.toLowerCase().includes(query) ||
          // Search by merchant (Intent and Cart mandates)
          (m.merchant && m.merchant.toLowerCase().includes(query)) ||
          (m.constraints?.merchant && m.constraints.merchant.toLowerCase().includes(query)) ||
          // Search by total amount (Cart mandates)
          (m.total && m.total.toString().includes(query)) ||
          // Search by max_amount (Intent mandates - check both direct and constraints)
          (m.max_amount && m.max_amount.toString().includes(query)) ||
          (m.constraints?.max_amount && m.constraints.max_amount.toString().includes(query)) ||
          // Search by monthly_limit (Intent mandates - check both direct and constraints)
          (m.monthly_limit && m.monthly_limit.toString().includes(query)) ||
          (m.constraints?.monthly_limit && m.constraints.monthly_limit.toString().includes(query)) ||
          // Search by category (check both direct and constraints)
          (m.category && m.category.toLowerCase().includes(query)) ||
          (m.constraints?.category && m.constraints.category.toLowerCase().includes(query)) ||
          // Search by payment_method (Payment mandates)
          (m.payment_method && m.payment_method.toLowerCase().includes(query)),
      );
    }

    // Sort by creation date (newest first)
    filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    setSortedMandates(filtered);
  }, [mandates, filter, statusFilter, searchQuery]);

  // Calculate statistics
  const totalTransactions = mandates.length;
  const completedTransactions = mandates.filter(
    (m) => m.status === "completed",
  ).length;
  const activeTransactions = mandates.filter(
    (m) => m.status === "active" || m.status === "pending",
  ).length;
  const failedTransactions = mandates.filter(
    (m) => m.status === "failed",
  ).length;

  return (
    <div className="space-y-6">
      {/* Header & Stats */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Agent Activity
        </h2>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            icon={<Activity className="w-5 h-5" />}
            label="Total Transactions"
            value={totalTransactions}
            color="blue"
          />
          <StatCard
            icon={<CheckCircle className="w-5 h-5" />}
            label="Completed"
            value={completedTransactions}
            color="green"
          />
          <StatCard
            icon={<Clock className="w-5 h-5" />}
            label="Active/Pending"
            value={activeTransactions}
            color="yellow"
          />
          <StatCard
            icon={<XCircle className="w-5 h-5" />}
            label="Failed"
            value={failedTransactions}
            color="red"
          />
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col md:flex-row md:items-center md:space-x-4 space-y-4 md:space-y-0">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search by ID, merchant, amount, category, payment method..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
              />
            </div>
          </div>

          {/* Type Filter */}
          <div className="flex space-x-2">
            <span className="text-sm font-medium text-gray-700 self-center">
              Type:
            </span>
            {["all", "intent", "cart", "payment"].map((type) => (
              <button
                key={type}
                onClick={() => setFilter(type)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  filter === type
                    ? "bg-purple-100 text-purple-700"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>

          {/* Status Filter */}
          <div className="flex space-x-2">
            <span className="text-sm font-medium text-gray-700 self-center">
              Status:
            </span>
            {["all", "active", "pending", "completed", "failed"].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  statusFilter === status
                    ? "bg-purple-100 text-purple-700"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Activity Timeline */}
      {sortedMandates.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <Activity className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Activity Found
          </h3>
          <p className="text-gray-600">
            {searchQuery || filter !== "all" || statusFilter !== "all"
              ? "Try adjusting your filters or search query."
              : "Your AI agent activity will appear here once you create Intent Mandates."}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="divide-y divide-gray-200">
            {sortedMandates.map((mandate, index) => (
              <ActivityTimelineItem
                key={mandate.id}
                mandate={mandate}
                isFirst={index === 0}
              />
            ))}
          </div>
        </div>
      )}

      {/* Export Option */}
      {sortedMandates.length > 0 && (
        <div className="flex justify-end">
          <button
            onClick={() => exportActivity(sortedMandates)}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Export Activity Log</span>
          </button>
        </div>
      )}
    </div>
  );
};

// Stat Card Component
const StatCard = ({ icon, label, value, color }) => {
  const colors = {
    blue: "bg-blue-100 text-blue-600",
    green: "bg-green-100 text-green-600",
    yellow: "bg-yellow-100 text-yellow-600",
    red: "bg-red-100 text-red-600",
    purple: "bg-purple-100 text-purple-600",
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center space-x-3">
        <div className={`p-2 rounded-lg ${colors[color]}`}>{icon}</div>
        <div className="flex-1">
          <p className="text-sm text-gray-600">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
};

// Activity Timeline Item Component
const ActivityTimelineItem = ({ mandate, isFirst }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatDate = (dateString) => {
    // Fix timezone: backend sends UTC time without 'Z', so append it
    const dateStr = dateString.endsWith('Z') ? dateString : dateString + 'Z';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
    if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
    if (days < 7) return `${days} day${days > 1 ? "s" : ""} ago`;

    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const getStatusConfig = (status) => {
    const configs = {
      completed: {
        bg: "bg-green-100",
        text: "text-green-800",
        icon: CheckCircle,
        iconColor: "text-green-600",
        dot: "bg-green-500",
      },
      active: {
        bg: "bg-yellow-100",
        text: "text-yellow-800",
        icon: Clock,
        iconColor: "text-yellow-600",
        dot: "bg-yellow-500",
      },
      pending: {
        bg: "bg-blue-100",
        text: "text-blue-800",
        icon: Clock,
        iconColor: "text-blue-600",
        dot: "bg-blue-500",
      },
      failed: {
        bg: "bg-red-100",
        text: "text-red-800",
        icon: XCircle,
        iconColor: "text-red-600",
        dot: "bg-red-500",
      },
      expired: {
        bg: "bg-gray-100",
        text: "text-gray-800",
        icon: AlertTriangle,
        iconColor: "text-gray-600",
        dot: "bg-gray-500",
      },
    };

    return configs[status] || configs.pending;
  };

  const getMandateTypeInfo = (type) => {
    const types = {
      intent: {
        label: "Intent Mandate",
        description: "User authorization created",
        icon: Target,
        color: "text-purple-600",
      },
      cart: {
        label: "Cart Mandate",
        description: "Items prepared for approval",
        icon: DollarSign,
        color: "text-blue-600",
      },
      payment: {
        label: "Payment Mandate",
        description: "Payment processed",
        icon: CheckCircle,
        color: "text-green-600",
      },
    };

    return types[type] || types.intent;
  };

  const statusConfig = getStatusConfig(mandate.status);
  const typeInfo = getMandateTypeInfo(mandate.type);
  const StatusIcon = statusConfig.icon;
  const TypeIcon = typeInfo.icon;

  return (
    <div className="px-6 py-4 hover:bg-gray-50 transition-colors relative">
      {/* Timeline Dot & Line */}
      <div
        className="absolute left-0 top-4 bottom-0 w-px bg-gray-200 ml-10"
        style={{ display: isFirst ? "none" : "block" }}
      ></div>

      <div
        className="flex items-start space-x-4 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Icon */}
        <div className="relative flex-shrink-0">
          <div
            className={`w-10 h-10 rounded-full ${statusConfig.bg} flex items-center justify-center`}
          >
            <TypeIcon className={`w-5 h-5 ${typeInfo.color}`} />
          </div>
          <div
            className={`absolute -top-1 -right-1 w-3 h-3 rounded-full ${statusConfig.dot} border-2 border-white`}
          ></div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-1">
                <h4 className="text-sm font-semibold text-gray-900">
                  {typeInfo.label}
                </h4>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.text}`}
                >
                  <StatusIcon className="w-3 h-3 mr-1" />
                  {mandate.status}
                </span>
              </div>
              <p className="text-sm text-gray-600">{typeInfo.description}</p>
            </div>

            <div className="text-right flex-shrink-0 ml-4">
              <p className="text-xs text-gray-500">
                {formatDate(mandate.created_at)}
              </p>
            </div>
          </div>

          {/* Details */}
          <div className="flex flex-wrap gap-4 text-sm text-gray-600 mt-3">
            <div className="flex items-center space-x-1">
              <Calendar className="w-4 h-4" />
              <span className="font-mono text-xs">{mandate.id.slice(-12)}</span>
            </div>

            {mandate.total && (
              <div className="flex items-center space-x-1">
                <DollarSign className="w-4 h-4" />
                <span className="font-medium text-gray-900">
                  ${parseFloat(mandate.total).toFixed(2)}
                </span>
              </div>
            )}

            {mandate.merchant && (
              <div className="flex items-center space-x-1">
                <span className="font-medium text-gray-900">
                  {mandate.merchant}
                </span>
              </div>
            )}

            {mandate.payment_method && (
              <div className="flex items-center space-x-1">
                <span className="text-gray-500">
                  via {mandate.payment_method}
                </span>
              </div>
            )}
          </div>

          {/* Expiration (for intent mandates) */}
          {mandate.type === "intent" && mandate.expiration && (
            <div className="mt-2 text-xs text-gray-500">
              Expires:{" "}
              {new Date(mandate.expiration).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </div>
          )}
        </div>

        {/* View Details Arrow */}
        <div className="flex-shrink-0">
          <ChevronRight
            className={`w-5 h-5 text-gray-400 transition-transform ${
              isExpanded ? "rotate-90" : ""
            }`}
          />
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="mt-4 ml-14 pl-4 border-l-2 border-purple-200 bg-gray-50 rounded-lg p-4">
          <h5 className="text-sm font-semibold text-gray-900 mb-3">
            Mandate Details
          </h5>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Full ID:</span>
              <p className="font-mono text-xs text-gray-900 mt-1 break-all">
                {mandate.id}
              </p>
            </div>

            <div>
              <span className="text-gray-500">Type:</span>
              <p className="text-gray-900 mt-1 capitalize">{mandate.type}</p>
            </div>

            <div>
              <span className="text-gray-500">Status:</span>
              <p className="text-gray-900 mt-1 capitalize">{mandate.status}</p>
            </div>

            {mandate.max_amount && (
              <div>
                <span className="text-gray-500">Max Amount:</span>
                <p className="text-gray-900 mt-1 font-medium">
                  ${parseFloat(mandate.max_amount).toFixed(2)}
                </p>
              </div>
            )}

            {mandate.monthly_limit && (
              <div>
                <span className="text-gray-500">Monthly Limit:</span>
                <p className="text-gray-900 mt-1 font-medium">
                  ${parseFloat(mandate.monthly_limit).toFixed(2)}
                </p>
              </div>
            )}

            {mandate.category && (
              <div>
                <span className="text-gray-500">Category:</span>
                <p className="text-gray-900 mt-1">{mandate.category}</p>
              </div>
            )}

            {mandate.merchant && (
              <div>
                <span className="text-gray-500">Merchant:</span>
                <p className="text-gray-900 mt-1">{mandate.merchant}</p>
              </div>
            )}

            {mandate.total && (
              <div>
                <span className="text-gray-500">Total Amount:</span>
                <p className="text-gray-900 mt-1 font-medium">
                  ${parseFloat(mandate.total).toFixed(2)}
                </p>
              </div>
            )}

            {mandate.payment_method && (
              <div>
                <span className="text-gray-500">Payment Method:</span>
                <p className="text-gray-900 mt-1 capitalize">
                  {mandate.payment_method}
                </p>
              </div>
            )}

            {mandate.timestamp && (
              <div>
                <span className="text-gray-500">Timestamp:</span>
                <p className="text-gray-900 mt-1 text-xs">
                  {new Date(mandate.timestamp).toLocaleString()}
                </p>
              </div>
            )}

            {mandate.expiration && (
              <div>
                <span className="text-gray-500">Expiration:</span>
                <p className="text-gray-900 mt-1 text-xs">
                  {new Date(mandate.expiration).toLocaleString()}
                </p>
              </div>
            )}
          </div>

          {/* Constraints for Intent Mandates */}
          {mandate.type === "intent" && mandate.constraints && (
            <div className="mt-4">
              <span className="text-gray-500 text-sm">Full Constraints:</span>
              <pre className="mt-2 text-xs bg-white p-3 rounded border border-gray-200 overflow-x-auto">
                {JSON.stringify(mandate.constraints, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Export activity function
const exportActivity = (mandates) => {
  const csv = [
    [
      "ID",
      "Type",
      "Status",
      "Total",
      "Merchant",
      "Created At",
      "Timestamp",
    ].join(","),
    ...mandates.map((m) =>
      [
        m.id,
        m.type,
        m.status,
        m.total || "",
        m.merchant || "",
        new Date(m.created_at).toISOString(),
        m.timestamp || "",
      ].join(","),
    ),
  ].join("\n");

  const blob = new Blob([csv], { type: "text/csv" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ap2-activity-${new Date().toISOString().split("T")[0]}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

export default AgentActivityMonitor;
