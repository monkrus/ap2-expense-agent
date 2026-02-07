import React, { useState, useEffect } from "react";
import {
  Bot,
  Zap,
  Shield,
  TrendingUp,
  Plus,
  Settings,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ChevronRight,
  Sparkles,
  Activity,
  Target,
} from "lucide-react";
import { expenseAPI, APIError } from "../services/api";
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

  const [activeView, setActiveView] = useState("overview"); // 'overview', 'mandates', 'activity', 'flow'
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
      }
    } catch (err) {
      console.error("Error fetching AP2 data:", err);
      showError("Failed to load AP2 Automation data");
    } finally {
      setLoading(false);
    }
  };

  // Calculate active mandates count
  const activeMandatesCount = mandates.filter(
    (m) => m.type === "intent" && m.status === "active",
  ).length;

  // Calculate total processed amount
  const totalProcessed = stats?.total_amount_processed || 0;

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
                  ? "Manage automated expense approval policies using Agent Payments Protocol"
                  : "Your expenses are automatically approved based on admin-defined policies"}
              </p>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm">Active Mandates</p>
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
                    {stats?.payment_mandates?.completed || 0}
                  </p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-300" />
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm">Time Saved</p>
                  <p className="text-2xl font-bold mt-1">
                    {Math.round(
                      (stats?.payment_mandates?.completed || 0) * 2.5,
                    )}{" "}
                    min
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
                onCreateMandate={() => setShowCreateMandate(true)}
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

            {/* One-time Authorization - Admin Only */}
            {activeView === "flow" && isAdmin && <AP2CompleteFlow mandates={mandates} />}
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
            success("Intent Mandate created successfully!");
          }}
        />
      )}
    </div>
  );
};

// Overview View Component
const OverviewView = ({ mandates, stats, onCreateMandate, isAdmin }) => {
  const activeIntentMandates = mandates.filter(
    (m) => m.type === "intent" && m.status === "active",
  );
  const recentActivity = mandates.slice(0, 5);

  return (
    <div className="space-y-6">
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
              {isAdmin ? (
                <>
                  Automate expense approvals: Create <strong>Reusable Authorizations</strong> (policies) for automatic approvals,
                  or use <strong>One-time Authorizations</strong> for quick single purchases.
                  Save hours of manual work every week with AP2 protocol automation.
                </>
              ) : (
                <>
                  Your expenses are automatically approved or denied based on policies set by your admin.
                  Check the Activity tab to see your expense status and approval history.
                </>
              )}
            </p>
            {/* Create button - Admin Only */}
            {isAdmin && activeIntentMandates.length === 0 && (
              <button
                onClick={onCreateMandate}
                className="bg-white text-purple-600 px-6 py-3 rounded-lg font-semibold hover:bg-purple-50 transition-colors flex items-center space-x-2"
              >
                <Plus className="w-5 h-5" />
                <span>Create Reusable Authorization</span>
              </button>
            )}
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
          title="Auto-Submit Recurring"
          description="Never manually enter a recurring expense again. Set it once, forget it."
          color="yellow"
        />
        <FeatureCard
          icon={<TrendingUp className="w-6 h-6" />}
          title="Smart Insights"
          description="AI analyzes your spending patterns and suggests optimizations"
          color="green"
        />
      </div>

      {/* Active Mandates/Policies */}
      {activeIntentMandates.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              {isAdmin ? "Active Reusable Authorizations" : "Active Approval Policies"}
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
              <p>
                {isAdmin
                  ? "No activity yet. Create a Reusable Authorization to enable automatic expense approvals!"
                  : "No activity yet. Submit an expense to see it automatically processed based on admin policies."}
              </p>
            </div>
          )}
        </div>
      </div>
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
    // Fix timezone issue: parse as local time if no timezone specified
    if (!dateString) return 'N/A';

    // Split date and time parts
    const parts = dateString.split('T');
    if (parts.length === 2) {
      const [datePart, timePart] = parts;
      const [year, month, day] = datePart.split('-');

      // Create date using local timezone
      const date = new Date(year, month - 1, day);

      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    }

    // Fallback to standard parsing
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="border-b border-gray-200">
      <div
        className="px-6 py-4 hover:bg-gray-50 transition-colors cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-1">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                <CheckCircle className="w-3 h-3 mr-1" />
                Active
              </span>
              <span className="text-sm font-medium text-gray-900">
                Mandate #{mandate.id.slice(-8)}
              </span>
            </div>
            <p className="text-sm text-gray-600">
              Created {formatDate(mandate.created_at)} • Expires{" "}
              {formatDate(mandate.expiration)}
            </p>
          </div>
          <ChevronRight
            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
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
              <span className="text-gray-600">Mandate ID:</span>
              <p className="font-mono text-xs text-gray-900">{mandate.id}</p>
            </div>
            <div>
              <span className="text-gray-600">Status:</span>
              <p className="font-medium text-green-600">Active</p>
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
      default:
        return <AlertTriangle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getMandateTypeLabel = (type) => {
    switch (type) {
      case "intent":
        return "Intent Mandate";
      case "cart":
        return "Cart Mandate";
      case "payment":
        return "Payment Mandate";
      default:
        return type;
    }
  };

  const formatDate = (dateString) => {
    // Fix timezone: backend sends UTC time without 'Z', so append it
    const dateStr = dateString.endsWith('Z') ? dateString : dateString + 'Z';
    return new Date(dateStr).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
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
          </p>
          <p className="text-sm text-gray-500">
            {formatDate(mandate.created_at)}
          </p>
        </div>
        <div className="flex-shrink-0">
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              mandate.status === "completed"
                ? "bg-green-100 text-green-800"
                : mandate.status === "active"
                  ? "bg-yellow-100 text-yellow-800"
                  : mandate.status === "pending"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-red-100 text-red-800"
            }`}
          >
            {mandate.status}
          </span>
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;
