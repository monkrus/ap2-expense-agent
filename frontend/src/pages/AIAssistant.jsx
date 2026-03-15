import React, { useState, useEffect } from "react";
import {
  Bot,
  Zap,
  Shield,
  TrendingUp,
  Settings,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ChevronRight,
  Sparkles,
  Activity,
  Target,
  Copy,
  Search,
  Send,
  DollarSign,
  FileText,
  BarChart3,
  HelpCircle,
} from "lucide-react";
import { useToast } from "../hooks/useToast";
import { useAuth } from "../contexts/AuthContext";
import IntentMandateManager from "../components/IntentMandateManager";
import AgentActivityMonitor from "../components/AgentActivityMonitor";
import ConstraintBuilder from "../components/ConstraintBuilder";
import AP2CompleteFlow from "../components/AP2CompleteFlow";

const AIAssistant = () => {
  const { user } = useAuth();
  const { success, error: showError } = useToast();

  // Check if user is admin
  const isAdmin = user?.role === "admin";

  const [activeView, setActiveView] = useState("overview"); // 'overview', 'mandates', 'activity', 'flow', 'check', 'request'
  const [mandates, setMandates] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreateMandate, setShowCreateMandate] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  // Fetch AP2 stats and mandates
  useEffect(() => {
    fetchData();
  }, [showArchived]);

  const fetchData = async () => {
    try {
      setLoading(true);

      // Fetch AP2 stats
      const statsResponse = await fetch("/api/ap2/stats", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      } else if (statsResponse.status !== 404) {
        console.warn("Failed to fetch AP2 stats:", statsResponse.status);
      }

      // Fetch user's mandates
      const mandatesResponse = await fetch(
        `/api/ap2/user/mandates?limit=50&include_deleted=${showArchived}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      if (mandatesResponse.ok) {
        const mandatesData = await mandatesResponse.json();
        setMandates(mandatesData.mandates || []);
      } else {
        console.warn("Failed to fetch mandates:", mandatesResponse.status);
        showError("Failed to load mandate data");
      }
    } catch (err) {
      console.error("Error fetching AP2 data:", err);
      showError("Failed to load AP2 Automation data");
    } finally {
      setLoading(false);
    }
  };

  // Use stats endpoint for accurate count (not limited by mandate list size)
  const activeMandatesCount = stats?.intent_mandates?.active
    ?? mandates.filter((m) => m.type === "intent" && m.status === "active").length;

  // Calculate total processed amount
  const totalProcessed = stats?.total_amount_processed || 0;

  // Completed payments count
  const completedPayments = stats?.payment_mandates?.completed || 0;

  // Success rate
  const totalPayments = completedPayments + (stats?.payment_mandates?.failed || 0);
  const successRate = totalPayments > 0 ? Math.round((completedPayments / totalPayments) * 100) : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-white/10 rounded-xl backdrop-blur-sm">
              <Bot className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">AP2 Automation</h1>
              <p className="text-purple-100 mt-1">
                {isAdmin
                  ? "Define approval rules that automatically approve or deny submitted expenses. Unlike Recurring (which creates expenses), AP2 handles the approval step."
                  : "Your submitted expenses are automatically approved or denied based on rules set by your admin. This handles approval \u2014 use the Recurring tab to automate submission."}
              </p>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm">Active Authorizations</p>
                  <p className="text-2xl font-bold mt-1">
                    {activeMandatesCount}
                  </p>
                </div>
                <Target className="w-8 h-8 text-purple-200" />
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm">Total Processed</p>
                  <p className="text-2xl font-bold mt-1">
                    $
                    {totalProcessed.toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </p>
                </div>
                <TrendingUp className="w-8 h-8 text-purple-200" />
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm">Completed Payments</p>
                  <p className="text-2xl font-bold mt-1">
                    {completedPayments}
                  </p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-300" />
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm">Success Rate</p>
                  <p className="text-2xl font-bold mt-1">
                    {totalPayments > 0 ? `${successRate}%` : "N/A"}
                  </p>
                </div>
                <Zap className="w-8 h-8 text-yellow-300" />
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex space-x-4 mt-8 border-b border-white/20">
            <button
              onClick={() => setActiveView("overview")}
              className={`px-4 py-3 font-medium transition-colors ${
                activeView === "overview"
                  ? "text-white border-b-2 border-white"
                  : "text-purple-200 hover:text-white"
              }`}
            >
              Overview
            </button>
            {/* Reusable Authorizations - Admin Only */}
            {isAdmin && (
              <button
                onClick={() => setActiveView("mandates")}
                className={`px-4 py-3 font-medium transition-colors ${
                  activeView === "mandates"
                    ? "text-white border-b-2 border-white"
                    : "text-purple-200 hover:text-white"
                }`}
              >
                Reusable Authorizations
              </button>
            )}
            {/* Employee: Check Expense */}
            {!isAdmin && (
              <button
                onClick={() => setActiveView("check")}
                className={`px-4 py-3 font-medium transition-colors ${
                  activeView === "check"
                    ? "text-white border-b-2 border-white"
                    : "text-purple-200 hover:text-white"
                }`}
              >
                Check Expense
              </button>
            )}
            <button
              onClick={() => setActiveView("activity")}
              className={`px-4 py-3 font-medium transition-colors ${
                activeView === "activity"
                  ? "text-white border-b-2 border-white"
                  : "text-purple-200 hover:text-white"
              }`}
            >
              Activity
            </button>
            {/* Employee: Request Rule */}
            {!isAdmin && (
              <button
                onClick={() => setActiveView("request")}
                className={`px-4 py-3 font-medium transition-colors ${
                  activeView === "request"
                    ? "text-white border-b-2 border-white"
                    : "text-purple-200 hover:text-white"
                }`}
              >
                Request a Rule
              </button>
            )}
            {/* One-time Authorization - Admin Only */}
            {isAdmin && (
              <button
                onClick={() => setActiveView("flow")}
                className={`px-4 py-3 font-medium transition-colors ${
                  activeView === "flow"
                    ? "text-white border-b-2 border-white"
                    : "text-purple-200 hover:text-white"
                }`}
              >
                One-time Authorization
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
          </div>
        ) : (
          <>
            {activeView === "overview" && (
              <OverviewView
                mandates={mandates}
                stats={stats}
                isAdmin={isAdmin}
              />
            )}

            {/* Reusable Authorizations - Admin Only */}
            {activeView === "mandates" && isAdmin && (
              <IntentMandateManager
                mandates={mandates}
                onRefresh={fetchData}
                onCreateMandate={() => setShowCreateMandate(true)}
                showArchived={showArchived}
                setShowArchived={setShowArchived}
              />
            )}

            {activeView === "activity" && (
              <AgentActivityMonitor mandates={mandates} stats={stats} />
            )}

            {/* Employee: Check Expense */}
            {activeView === "check" && !isAdmin && <CheckExpenseView />}

            {/* Employee: Request Rule */}
            {activeView === "request" && !isAdmin && <RequestRuleView />}

            {/* One-time Authorization - Admin Only */}
            {activeView === "flow" && isAdmin && <AP2CompleteFlow mandates={mandates} onRefresh={fetchData} />}
          </>
        )}
      </div>

      {/* Create Mandate Modal */}
      {showCreateMandate && (
        <ConstraintBuilder
          onClose={() => setShowCreateMandate(false)}
          onSuccess={() => {
            setShowCreateMandate(false);
            fetchData();
            success("Reusable Authorization created successfully!");
          }}
        />
      )}
    </div>
  );
};

// Overview View Component
const OverviewView = ({ mandates, stats, isAdmin }) => {
  const activeIntentMandates = mandates.filter(
    (m) => m.type === "intent" && m.status === "active",
  );
  // Show cart and payment mandates as activity, sorted newest first
  const recentActivity = mandates
    .filter((m) => m.type === "cart" || m.type === "payment")
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5);

  // Employee-specific overview
  if (!isAdmin) {
    return <EmployeeOverview activeIntentMandates={activeIntentMandates} recentActivity={recentActivity} />;
  }

  // Admin overview
  return <AdminOverview activeIntentMandates={activeIntentMandates} recentActivity={recentActivity} />;
};

const AdminOverview = ({ activeIntentMandates, recentActivity }) => {
  const [ruleRequests, setRuleRequests] = useState([]);
  const [loadingRequests, setLoadingRequests] = useState(true);

  useEffect(() => {
    fetchRuleRequests();
  }, []);

  const fetchRuleRequests = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const orgId = localStorage.getItem("current_organization_id");
      const response = await fetch("/api/v1/expenses/rule-requests", {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": orgId,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setRuleRequests(data.requests || []);
      }
    } catch (err) {
      console.error("Failed to fetch rule requests:", err);
    } finally {
      setLoadingRequests(false);
    }
  };

  const pendingRequests = ruleRequests.filter(r => r.status === "pending");

  return (
    <div className="space-y-6">
      {/* Pending Rule Requests Banner */}
      {pendingRequests.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Shield className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-purple-900">
              Pending Rule Requests ({pendingRequests.length})
            </h3>
          </div>
          <p className="text-sm text-purple-700 mb-4">
            Employees have requested auto-approval rules. Review them in your notification bell.
          </p>
          <div className="space-y-3">
            {pendingRequests.map((req) => (
              <div key={req.id} className="flex items-center justify-between p-3 bg-white rounded-lg border border-purple-200">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {req.requester_name || req.requester_email} requested:
                    {" "}
                    {[req.category?.replace(/_/g, " "), req.vendor, req.max_amount ? `$${req.max_amount}` : null].filter(Boolean).join(", ") || "General rule"}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">{req.reason}</p>
                </div>
                <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">Pending</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Welcome Card */}
      <div className="bg-gradient-to-r from-purple-500 to-indigo-600 rounded-2xl p-8 text-white">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-4">
              <Sparkles className="w-6 h-6" />
              <h2 className="text-2xl font-bold">
                Welcome to AP2 Automation
              </h2>
            </div>
            <p className="text-purple-100 mb-6 max-w-2xl">
              <strong>AP2 handles approval</strong>, not submission. Create <strong>Reusable Authorizations</strong> to auto-approve
              expenses matching your rules (e.g. "approve software under $500"), or use <strong>One-time Authorizations</strong> for
              quick single purchases. To automate expense <em>creation</em>, use the Recurring tab instead.
            </p>
          </div>
          <div className="hidden lg:block">
            <Bot className="w-32 h-32 text-purple-300 opacity-50" />
          </div>
        </div>
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <FeatureCard
          icon={<Shield className="w-6 h-6" />}
          title="Secure & Compliant"
          description="AP2 protocol ensures cryptographic audit trails for every transaction"
          color="blue"
        />
        <FeatureCard
          icon={<Zap className="w-6 h-6" />}
          title="Instant Approvals"
          description="One-time authorizations execute the full payment flow in a single step"
          color="yellow"
        />
        <FeatureCard
          icon={<TrendingUp className="w-6 h-6" />}
          title="Budget Enforcement"
          description="Proactive budget checks warn you before limits are exceeded"
          color="green"
        />
      </div>

      {/* Active Mandates/Policies */}
      {activeIntentMandates.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Active Reusable Authorizations
            </h3>
            <span className="text-sm text-gray-500">
              {activeIntentMandates.length} active
            </span>
          </div>
          <div className="divide-y divide-gray-200">
            {activeIntentMandates.map((mandate) => (
              <MandateListItem key={mandate.id} mandate={mandate} />
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Recent Activity
          </h3>
        </div>
        <div className="divide-y divide-gray-200">
          {recentActivity.length > 0 ? (
            recentActivity.map((mandate) => (
              <ActivityItem key={mandate.id} mandate={mandate} />
            ))
          ) : (
            <div className="px-6 py-12 text-center text-gray-500">
              <Activity className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p>No activity yet. Create a Reusable Authorization to enable automatic expense approvals!</p>
            </div>
          )}
        </div>
      </div>

      {/* Rule Request History */}
      {!loadingRequests && ruleRequests.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Rule Request History</h3>
            <span className="text-sm text-gray-500">{ruleRequests.length} total</span>
          </div>
          <div className="divide-y divide-gray-100">
            {ruleRequests.map((req) => (
              <div key={req.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      req.status === "approved" ? "bg-green-100 text-green-800" :
                      req.status === "denied" ? "bg-red-100 text-red-800" :
                      "bg-yellow-100 text-yellow-800"
                    }`}>
                      {req.status.charAt(0).toUpperCase() + req.status.slice(1)}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {req.requester_name || req.requester_email}
                      </p>
                      <p className="text-xs text-gray-500">
                        {[req.category?.replace(/_/g, " "), req.vendor, req.max_amount ? `$${req.max_amount}` : null].filter(Boolean).join(", ") || "General"}
                        {" - "}{req.reason}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400">
                    {new Date(req.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </span>
                </div>
                {req.admin_note && (
                  <p className="text-xs text-gray-600 mt-2 ml-16 bg-gray-50 rounded px-2 py-1">Note: {req.admin_note}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Feature Card Component
const FeatureCard = ({ icon, title, description, color }) => {
  const colorClasses = {
    blue: "bg-blue-100 text-blue-600",
    yellow: "bg-yellow-100 text-yellow-600",
    green: "bg-green-100 text-green-600",
    purple: "bg-purple-100 text-purple-600",
  };

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
      <div
        className={`w-12 h-12 rounded-lg ${colorClasses[color]} flex items-center justify-center mb-4`}
      >
        {icon}
      </div>
      <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
};

// Mandate List Item Component
const MandateListItem = ({ mandate }) => {
  const [expanded, setExpanded] = React.useState(false);

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const dateStr = dateString.endsWith("Z") ? dateString : dateString + "Z";
    return new Date(dateStr).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const statusStyles = {
    active: { bg: "bg-green-100", text: "text-green-800", Icon: CheckCircle },
    expired: { bg: "bg-gray-100", text: "text-gray-800", Icon: Clock },
    revoked: { bg: "bg-orange-100", text: "text-orange-800", Icon: XCircle },
    failed: { bg: "bg-red-100", text: "text-red-800", Icon: XCircle },
    deleted: { bg: "bg-gray-100", text: "text-gray-600", Icon: AlertTriangle },
  };

  const style = statusStyles[mandate.status] || statusStyles.active;
  const StatusIcon = style.Icon;

  return (
    <div>
      <div
        className="px-6 py-4 hover:bg-gray-50 transition-colors cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-1">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
                <StatusIcon className="w-3 h-3 mr-1" />
                {mandate.status}
              </span>
              <span className="text-sm font-medium text-gray-900">
                Authorization #{mandate.id.slice(-8)}
              </span>
            </div>
            <p className="text-sm text-gray-600">
              Created {formatDate(mandate.created_at)} • Expires{" "}
              {formatDate(mandate.expiration)}
            </p>
          </div>
          <ChevronRight
            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? "rotate-90" : ""}`}
          />
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">Constraints</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            {mandate.merchant && (
              <div>
                <span className="text-gray-600">Merchant:</span>
                <p className="font-medium text-gray-900">{mandate.merchant}</p>
              </div>
            )}
            {mandate.category && (
              <div>
                <span className="text-gray-600">Category:</span>
                <p className="font-medium text-gray-900">{mandate.category}</p>
              </div>
            )}
            {mandate.max_amount && (
              <div>
                <span className="text-gray-600">Max Amount:</span>
                <p className="font-medium text-gray-900">${mandate.max_amount.toFixed(2)}</p>
              </div>
            )}
            {mandate.monthly_limit && (
              <div>
                <span className="text-gray-600">Monthly Limit:</span>
                <p className="font-medium text-gray-900">${mandate.monthly_limit.toFixed(2)}</p>
              </div>
            )}
            <div>
              <span className="text-gray-600">Authorization ID:</span>
              <p className="font-mono text-xs text-gray-900 inline-flex items-center">
                {mandate.id}
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
              </p>
            </div>
            <div>
              <span className="text-gray-600">Status:</span>
              <p className={`font-medium ${style.text}`}>{mandate.status}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Activity Item Component
const ActivityItem = ({ mandate }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "active":
      case "pending":
        return <Clock className="w-5 h-5 text-yellow-500" />;
      case "failed":
        return <XCircle className="w-5 h-5 text-red-500" />;
      case "expired":
        return <Clock className="w-5 h-5 text-gray-400" />;
      case "revoked":
        return <XCircle className="w-5 h-5 text-orange-500" />;
      default:
        return <AlertTriangle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getMandateTypeLabel = (type) => {
    switch (type) {
      case "intent":
        return "Reusable Authorization";
      case "cart":
        return "Cart Authorization";
      case "payment":
        return "Payment";
      default:
        return type;
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const dateStr = dateString.endsWith("Z") ? dateString : dateString + "Z";
    return new Date(dateStr).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const statusBadgeClass = {
    completed: "bg-green-100 text-green-800",
    active: "bg-yellow-100 text-yellow-800",
    pending: "bg-blue-100 text-blue-800",
    expired: "bg-gray-100 text-gray-800",
    revoked: "bg-orange-100 text-orange-800",
    failed: "bg-red-100 text-red-800",
    deleted: "bg-gray-100 text-gray-600",
  };

  return (
    <div className="px-6 py-4 hover:bg-gray-50 transition-colors">
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0 mt-1">
          {getStatusIcon(mandate.status)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900">
            {getMandateTypeLabel(mandate.type)}
            {mandate.total && (
              <span className="ml-2 text-gray-600">
                ${parseFloat(mandate.total).toFixed(2)}
              </span>
            )}
            {mandate.merchant && (
              <span className="ml-2 text-gray-500">
                @ {mandate.merchant}
              </span>
            )}
          </p>
          <p className="text-sm text-gray-500">
            {formatDate(mandate.created_at)}
          </p>
        </div>
        <div className="flex-shrink-0">
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              statusBadgeClass[mandate.status] || "bg-gray-100 text-gray-800"
            }`}
          >
            {mandate.status}
          </span>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// EMPLOYEE COMPONENTS
// ============================================================================

// Employee Overview with policies, stats, and how-it-works
const EmployeeOverview = ({ activeIntentMandates, recentActivity }) => {
  const [policies, setPolicies] = useState([]);
  const [approvalStats, setApprovalStats] = useState(null);
  const [ruleRequests, setRuleRequests] = useState([]);
  const [loadingPolicies, setLoadingPolicies] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingRequests, setLoadingRequests] = useState(true);

  useEffect(() => {
    fetchPolicies();
    fetchApprovalStats();
    fetchRuleRequests();
  }, []);

  const fetchPolicies = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const orgId = localStorage.getItem("current_organization_id");
      const response = await fetch("/api/v1/approval-policies?active_only=true", {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": orgId,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setPolicies(data);
      }
    } catch (err) {
      console.error("Failed to fetch policies:", err);
    } finally {
      setLoadingPolicies(false);
    }
  };

  const fetchApprovalStats = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const orgId = localStorage.getItem("current_organization_id");
      const response = await fetch("/api/v1/expenses/my-approval-stats", {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": orgId,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setApprovalStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch approval stats:", err);
    } finally {
      setLoadingStats(false);
    }
  };

  const fetchRuleRequests = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const orgId = localStorage.getItem("current_organization_id");
      const response = await fetch("/api/v1/expenses/rule-requests", {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": orgId,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setRuleRequests(data.requests || []);
      }
    } catch (err) {
      console.error("Failed to fetch rule requests:", err);
    } finally {
      setLoadingRequests(false);
    }
  };

  const formatPolicyDescription = (policy) => {
    const parts = [];
    const conditions = policy.conditions || {};

    if (conditions.categories && conditions.categories.length > 0) {
      parts.push(conditions.categories.map(c => c.replace(/_/g, " ")).join(", "));
    } else {
      parts.push("Any category");
    }

    if (conditions.vendors && conditions.vendors.length > 0) {
      parts.push(`from ${conditions.vendors.join(", ")}`);
    }

    if (policy.limits?.max_amount_per_expense) {
      parts.push(`up to $${policy.limits.max_amount_per_expense}`);
    }

    return parts.join(" ");
  };

  return (
    <div className="space-y-6">
      {/* How It Works */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center space-x-3 mb-6">
          <Sparkles className="w-6 h-6 text-purple-600" />
          <h2 className="text-2xl font-bold text-gray-900">How AP2 Works For You</h2>
        </div>
        <p className="text-gray-600 mb-8">
          When you submit an expense, AP2 checks it against approval rules set by your admin.
          If it matches a rule, it's approved instantly — no waiting for manual review.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 text-center">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-blue-700 font-bold">1</span>
            </div>
            <h4 className="font-semibold text-blue-900 mb-1">You Submit</h4>
            <p className="text-sm text-blue-700">Submit an expense manually or via Recurring</p>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-xl p-5 text-center">
            <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-purple-700 font-bold">2</span>
            </div>
            <h4 className="font-semibold text-purple-900 mb-1">AP2 Checks</h4>
            <p className="text-sm text-purple-700">Expense is checked against admin approval rules</p>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-xl p-5 text-center">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-green-700 font-bold">3a</span>
            </div>
            <h4 className="font-semibold text-green-900 mb-1">Auto-Approved</h4>
            <p className="text-sm text-green-700">Matches a rule? Approved instantly</p>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 text-center">
            <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-amber-700 font-bold">3b</span>
            </div>
            <h4 className="font-semibold text-amber-900 mb-1">Manual Review</h4>
            <p className="text-sm text-amber-700">No matching rule? Sent to admin for review</p>
          </div>
        </div>
      </div>

      {/* What Gets Auto-Approved */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <Shield className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">What Gets Auto-Approved</h3>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          These are the active rules your admin has set up. Expenses matching these rules are approved instantly.
        </p>

        {loadingPolicies ? (
          <div className="flex justify-center py-6">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
          </div>
        ) : policies.length > 0 || activeIntentMandates.length > 0 ? (
          <div className="space-y-3">
            {/* Approval Policies */}
            {policies.map((policy) => (
              <div key={policy.id} className="flex items-center justify-between p-4 bg-green-50 rounded-lg border border-green-200">
                <div>
                  <p className="font-medium text-green-900">{policy.name}</p>
                  <p className="text-sm text-green-700 mt-1">{formatPolicyDescription(policy)}</p>
                  {policy.description && (
                    <p className="text-xs text-green-600 mt-1">{policy.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">Policy</span>
                  <CheckCircle className="w-5 h-5 text-green-600" />
                </div>
              </div>
            ))}

            {/* AP2 Intent Mandates */}
            {activeIntentMandates.map((mandate) => (
              <div key={mandate.id} className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div>
                  <p className="font-medium text-purple-900">
                    {mandate.merchant || mandate.category || "General"} expenses
                  </p>
                  {mandate.max_amount && (
                    <p className="text-sm text-purple-700 mt-1">Up to ${mandate.max_amount.toFixed(2)}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-1 bg-purple-100 text-purple-800 rounded">AP2 Mandate</span>
                  <CheckCircle className="w-5 h-5 text-purple-600" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 bg-gray-50 rounded-lg">
            <Clock className="w-10 h-10 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No auto-approval rules set up yet.</p>
            <p className="text-xs text-gray-400 mt-1">Ask your admin to create rules, or use the "Request a Rule" tab.</p>
          </div>
        )}
      </div>

      {/* Your Approval Stats */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <BarChart3 className="w-5 h-5 text-indigo-600" />
          <h3 className="text-lg font-semibold text-gray-900">Your Approval Breakdown</h3>
        </div>

        {loadingStats ? (
          <div className="flex justify-center py-6">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
          </div>
        ) : approvalStats ? (
          <div>
            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-green-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-green-700">{approvalStats.auto_approved}</p>
                <p className="text-xs text-green-600 mt-1">Auto-Approved</p>
              </div>
              <div className="bg-blue-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-blue-700">{approvalStats.manually_approved}</p>
                <p className="text-xs text-blue-600 mt-1">Manually Approved</p>
              </div>
              <div className="bg-yellow-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-yellow-700">{approvalStats.pending}</p>
                <p className="text-xs text-yellow-600 mt-1">Pending Review</p>
              </div>
              <div className="bg-purple-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-purple-700">{approvalStats.auto_rate_percent}%</p>
                <p className="text-xs text-purple-600 mt-1">Auto-Approval Rate</p>
              </div>
            </div>

            {/* Progress Bar */}
            {approvalStats.total_expenses > 0 && (
              <div className="mb-4">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Auto-approved vs Manual</span>
                  <span>{approvalStats.auto_approved} of {approvalStats.total_expenses} total</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 flex overflow-hidden">
                  <div
                    className="bg-green-500 h-full transition-all"
                    style={{ width: `${approvalStats.auto_rate_percent}%` }}
                  />
                  <div
                    className="bg-blue-500 h-full transition-all"
                    style={{ width: `${approvalStats.total_expenses > 0 ? (approvalStats.manually_approved / approvalStats.total_expenses * 100) : 0}%` }}
                  />
                  <div
                    className="bg-yellow-400 h-full transition-all"
                    style={{ width: `${approvalStats.total_expenses > 0 ? (approvalStats.pending / approvalStats.total_expenses * 100) : 0}%` }}
                  />
                </div>
                <div className="flex gap-4 mt-2 text-xs text-gray-500">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span> Auto</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> Manual</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-400"></span> Pending</span>
                </div>
              </div>
            )}

            {/* Time Saved */}
            {approvalStats.time_saved_minutes > 0 && (
              <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 flex items-center gap-3">
                <Zap className="w-6 h-6 text-indigo-600" />
                <div>
                  <p className="font-medium text-indigo-900">
                    ~{approvalStats.time_saved_minutes} minutes saved
                  </p>
                  <p className="text-sm text-indigo-700">
                    AP2 auto-approved ${approvalStats.auto_approved_amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} worth of expenses without manual review
                  </p>
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-gray-500 text-sm text-center py-4">No expense data yet.</p>
        )}
      </div>

      {/* Your Rule Requests */}
      {!loadingRequests && ruleRequests.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <FileText className="w-5 h-5 text-orange-600" />
            <h3 className="text-lg font-semibold text-gray-900">Your Rule Requests</h3>
          </div>
          <div className="space-y-3">
            {ruleRequests.map((req) => (
              <div key={req.id} className={`p-4 rounded-lg border ${
                req.status === "approved" ? "bg-green-50 border-green-200" :
                req.status === "denied" ? "bg-red-50 border-red-200" :
                "bg-yellow-50 border-yellow-200"
              }`}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      req.status === "approved" ? "bg-green-100 text-green-800" :
                      req.status === "denied" ? "bg-red-100 text-red-800" :
                      "bg-yellow-100 text-yellow-800"
                    }`}>
                      {req.status.charAt(0).toUpperCase() + req.status.slice(1)}
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      {[req.category?.replace(/_/g, " "), req.vendor, req.max_amount ? `$${req.max_amount}` : null].filter(Boolean).join(" - ") || "General"}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(req.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{req.reason}</p>
                {req.admin_note && (
                  <p className="text-sm text-red-700 mt-2 bg-red-100 rounded px-3 py-1.5">
                    Admin: {req.admin_note}
                  </p>
                )}
                {req.status === "approved" && req.reviewer_name && (
                  <p className="text-xs text-green-700 mt-1">Approved by {req.reviewer_name}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Recent AP2 Activity</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {recentActivity.length > 0 ? (
            recentActivity.map((mandate) => (
              <ActivityItem key={mandate.id} mandate={mandate} />
            ))
          ) : (
            <div className="px-6 py-8 text-center text-gray-500">
              <Activity className="w-10 h-10 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">No AP2 activity yet.</p>
              <p className="text-xs text-gray-400 mt-1">
                Submit an expense and it will appear here if AP2 processes it.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};


// Check Expense View - pre-check if expense would be auto-approved
const CheckExpenseView = () => {
  const [formData, setFormData] = useState({
    amount: "",
    category: "",
    vendor: "",
    has_receipt: true,
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const categories = [
    { value: "", label: "Any Category" },
    { value: "OFFICE_SUPPLIES", label: "Office Supplies" },
    { value: "SOFTWARE", label: "Software" },
    { value: "TRAVEL", label: "Travel" },
    { value: "MEALS", label: "Meals" },
    { value: "ENTERTAINMENT", label: "Entertainment" },
    { value: "UTILITIES", label: "Utilities" },
    { value: "MARKETING", label: "Marketing" },
    { value: "HARDWARE", label: "Hardware" },
    { value: "PROFESSIONAL_SERVICES", label: "Professional Services" },
    { value: "OTHER", label: "Other" },
  ];

  const handleCheck = async (e) => {
    e.preventDefault();
    if (!formData.amount || parseFloat(formData.amount) <= 0) return;

    setLoading(true);
    setResult(null);

    try {
      const token = localStorage.getItem("access_token");
      const orgId = localStorage.getItem("current_organization_id");
      const response = await fetch("/api/v1/approval-policies/test", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Organization-Id": orgId,
        },
        body: JSON.stringify({
          amount: parseFloat(formData.amount),
          category: formData.category || null,
          vendor: formData.vendor || "",
          has_receipt: formData.has_receipt,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        setResult({ error: true, reason: "Failed to check. Try again." });
      }
    } catch (err) {
      setResult({ error: true, reason: "Network error. Try again." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center space-x-3 mb-2">
          <Search className="w-6 h-6 text-purple-600" />
          <h2 className="text-2xl font-bold text-gray-900">Check Before You Submit</h2>
        </div>
        <p className="text-gray-600 mb-8">
          Enter expense details below to see if it would be auto-approved or require manual review.
        </p>

        <form onSubmit={handleCheck} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Amount <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  placeholder="0.00"
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                {categories.map((cat) => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Vendor</label>
            <input
              type="text"
              value={formData.vendor}
              onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
              placeholder="e.g., AWS, Uber, Staples (optional)"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="has_receipt"
              checked={formData.has_receipt}
              onChange={(e) => setFormData({ ...formData, has_receipt: e.target.checked })}
              className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
            />
            <label htmlFor="has_receipt" className="text-sm text-gray-700">I have a receipt</label>
          </div>

          <button
            type="submit"
            disabled={loading || !formData.amount}
            className="w-full flex items-center justify-center gap-2 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
            ) : (
              <>
                <Search className="w-5 h-5" />
                Check Expense
              </>
            )}
          </button>
        </form>

        {/* Result */}
        {result && !result.error && (
          <div className={`mt-6 p-5 rounded-xl border-2 ${
            result.would_auto_approve
              ? "bg-green-50 border-green-300"
              : "bg-amber-50 border-amber-300"
          }`}>
            <div className="flex items-center gap-3 mb-2">
              {result.would_auto_approve ? (
                <CheckCircle className="w-6 h-6 text-green-600" />
              ) : (
                <Clock className="w-6 h-6 text-amber-600" />
              )}
              <h4 className={`text-lg font-bold ${result.would_auto_approve ? "text-green-900" : "text-amber-900"}`}>
                {result.would_auto_approve ? "Would Be Auto-Approved!" : "Would Need Manual Review"}
              </h4>
            </div>
            <p className={`text-sm ${result.would_auto_approve ? "text-green-700" : "text-amber-700"}`}>
              {result.reason}
            </p>
            {result.matching_policy && (
              <p className="text-xs text-gray-500 mt-2">
                Matching rule: {result.matching_policy.name}
              </p>
            )}
            {result.remaining_limits && (
              <div className="mt-3 text-xs text-gray-600">
                <p className="font-medium mb-1">Remaining limits:</p>
                {result.remaining_limits.per_expense_remaining != null && (
                  <p>Per expense: ${result.remaining_limits.per_expense_remaining.toFixed(2)}</p>
                )}
                {result.remaining_limits.daily_remaining != null && (
                  <p>Daily: ${result.remaining_limits.daily_remaining.toFixed(2)}</p>
                )}
                {result.remaining_limits.monthly_remaining != null && (
                  <p>Monthly: ${result.remaining_limits.monthly_remaining.toFixed(2)}</p>
                )}
              </div>
            )}
          </div>
        )}

        {result && result.error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{result.reason}</p>
          </div>
        )}
      </div>
    </div>
  );
};


// Request Rule View - employee asks admin for a new auto-approval rule
const RequestRuleView = () => {
  const [formData, setFormData] = useState({
    category: "",
    vendor: "",
    max_amount: "",
    reason: "",
  });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const categories = [
    { value: "", label: "Any / Not Specific" },
    { value: "OFFICE_SUPPLIES", label: "Office Supplies" },
    { value: "SOFTWARE", label: "Software" },
    { value: "TRAVEL", label: "Travel" },
    { value: "MEALS", label: "Meals" },
    { value: "ENTERTAINMENT", label: "Entertainment" },
    { value: "UTILITIES", label: "Utilities" },
    { value: "MARKETING", label: "Marketing" },
    { value: "HARDWARE", label: "Hardware" },
    { value: "PROFESSIONAL_SERVICES", label: "Professional Services" },
    { value: "OTHER", label: "Other" },
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!formData.reason.trim()) {
      setError("Please explain why you need this rule");
      return;
    }

    setLoading(true);

    try {
      const token = localStorage.getItem("access_token");
      const orgId = localStorage.getItem("current_organization_id");
      const response = await fetch("/api/v1/expenses/request-approval-rule", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Organization-Id": orgId,
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setSubmitted(true);
      } else {
        const data = await response.json().catch(() => ({}));
        setError(data.detail || "Failed to send request");
      }
    } catch (err) {
      setError("Network error. Try again.");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Request Sent!</h2>
          <p className="text-gray-600 mb-6">
            Your admin has been notified. They'll review your request and may set up an auto-approval rule for you.
          </p>
          <button
            onClick={() => { setSubmitted(false); setFormData({ category: "", vendor: "", max_amount: "", reason: "" }); }}
            className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
          >
            Submit Another Request
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center space-x-3 mb-2">
          <Send className="w-6 h-6 text-purple-600" />
          <h2 className="text-2xl font-bold text-gray-900">Request an Auto-Approval Rule</h2>
        </div>
        <p className="text-gray-600 mb-8">
          Have a recurring expense that always needs manual approval? Ask your admin to set up an auto-approval rule so it gets approved instantly next time.
        </p>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                {categories.map((cat) => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Vendor</label>
              <input
                type="text"
                value={formData.vendor}
                onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
                placeholder="e.g., AWS, GitHub, Uber"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Suggested Max Amount</label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={formData.max_amount}
                onChange={(e) => setFormData({ ...formData, max_amount: e.target.value })}
                placeholder="e.g., 500.00"
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">The max amount per expense you'd like auto-approved</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Why do you need this? <span className="text-red-500">*</span>
            </label>
            <textarea
              value={formData.reason}
              onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
              rows="3"
              placeholder="e.g., I pay for our AWS bill every month ($450). Currently it takes 2 days to get approved each time..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading || !formData.reason.trim()}
            className="w-full flex items-center justify-center gap-2 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
            ) : (
              <>
                <Send className="w-5 h-5" />
                Send Request to Admin
              </>
            )}
          </button>
        </form>
      </div>

      {/* Tips */}
      <div className="bg-purple-50 border border-purple-200 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <HelpCircle className="w-5 h-5 text-purple-600" />
          <h4 className="font-medium text-purple-900">Tips for a good request</h4>
        </div>
        <ul className="space-y-2 text-sm text-purple-800">
          <li className="flex items-start gap-2">
            <span className="text-purple-400 mt-0.5">-</span>
            Be specific about the vendor and typical amount
          </li>
          <li className="flex items-start gap-2">
            <span className="text-purple-400 mt-0.5">-</span>
            Explain how often this expense occurs (weekly, monthly, etc.)
          </li>
          <li className="flex items-start gap-2">
            <span className="text-purple-400 mt-0.5">-</span>
            Mention if the amount is always the same or varies
          </li>
          <li className="flex items-start gap-2">
            <span className="text-purple-400 mt-0.5">-</span>
            Your admin will see this as a notification and can create the rule from their AP2 settings
          </li>
        </ul>
      </div>
    </div>
  );
};


export default AIAssistant;
