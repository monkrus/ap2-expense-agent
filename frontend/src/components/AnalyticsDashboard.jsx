import React, { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  FileText,
  Users,
  Clock,
  AlertCircle,
} from "lucide-react";
import { expenseAPI } from "../services/api";

const COLORS = {
  primary: "#3B82F6",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  purple: "#8B5CF6",
  indigo: "#6366F1",
  pink: "#EC4899",
  teal: "#14B8A6",
};

const CATEGORY_COLORS = {
  TRAVEL: COLORS.primary,
  MEALS: COLORS.success,
  SOFTWARE: COLORS.purple,
  OFFICE_SUPPLIES: COLORS.warning,
  MARKETING: COLORS.pink,
  UTILITIES: COLORS.indigo,
  OTHER: COLORS.teal,
};

const STATUS_COLORS = {
  PENDING: COLORS.warning,
  APPROVED: COLORS.success,
  REJECTED: COLORS.danger,
  PAID: COLORS.indigo,
  WITHDRAWN: "#9CA3AF",
};

const AnalyticsDashboard = () => {
  const [analytics, setAnalytics] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState(30); // days

  useEffect(() => {
    loadAnalytics();
  }, [timeRange]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);

      const [analyticsData, summaryData] = await Promise.all([
        expenseAPI.getAnalytics(timeRange),
        expenseAPI.getAnalyticsSummary(),
      ]);

      setAnalytics(analyticsData);
      setSummary(summaryData);
    } catch (err) {
      console.error("Failed to load analytics:", err);
      setError(err.message || "Failed to load analytics data");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const calculatePercentage = (value, total) => {
    if (total === 0) return 0;
    return ((value / total) * 100).toFixed(1);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-6 h-6 text-red-600" />
          <div>
            <h3 className="font-semibold text-red-900">Failed to load analytics</h3>
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        </div>
        <button
          onClick={loadAnalytics}
          className="mt-4 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!analytics || !summary) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <p className="text-yellow-800">No analytics data available</p>
      </div>
    );
  }

  // Calculate totals for category breakdown percentages
  const totalCategoryAmount = analytics.category_breakdown.reduce(
    (sum, cat) => sum + cat.amount,
    0
  );

  return (
    <div className="space-y-6">
      {/* Header with Time Range Selector */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h2>
        <div className="flex gap-2">
          {[7, 30, 90].map((days) => (
            <button
              key={days}
              onClick={() => setTimeRange(days)}
              className={`px-4 py-2 rounded-lg transition-colors ${
                timeRange === days
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-50 border border-gray-300"
              }`}
            >
              {days} days
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* This Month Spending */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
          <div className="flex items-center justify-between mb-2">
            <p className="text-gray-600 text-sm font-medium">This Month</p>
            <DollarSign className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(summary.this_month.amount)}
          </p>
          <div className="flex items-center mt-2 text-sm">
            {analytics.monthly_comparison.changes.amount_change_percent >= 0 ? (
              <>
                <TrendingUp className="w-4 h-4 text-green-600 mr-1" />
                <span className="text-green-600">
                  {analytics.monthly_comparison.changes.amount_change_percent.toFixed(1)}%
                </span>
              </>
            ) : (
              <>
                <TrendingDown className="w-4 h-4 text-red-600 mr-1" />
                <span className="text-red-600">
                  {Math.abs(analytics.monthly_comparison.changes.amount_change_percent).toFixed(1)}%
                </span>
              </>
            )}
            <span className="text-gray-500 ml-1">vs last month</span>
          </div>
        </div>

        {/* Total Expenses */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
          <div className="flex items-center justify-between mb-2">
            <p className="text-gray-600 text-sm font-medium">Total Expenses</p>
            <FileText className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {summary.this_month.count}
          </p>
          <div className="flex items-center mt-2 text-sm">
            {analytics.monthly_comparison.changes.count_change_percent >= 0 ? (
              <>
                <TrendingUp className="w-4 h-4 text-green-600 mr-1" />
                <span className="text-green-600">
                  {analytics.monthly_comparison.changes.count_change_percent.toFixed(1)}%
                </span>
              </>
            ) : (
              <>
                <TrendingDown className="w-4 h-4 text-red-600 mr-1" />
                <span className="text-red-600">
                  {Math.abs(analytics.monthly_comparison.changes.count_change_percent).toFixed(1)}%
                </span>
              </>
            )}
            <span className="text-gray-500 ml-1">vs last month</span>
          </div>
        </div>

        {/* Pending Approvals */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-yellow-500">
          <div className="flex items-center justify-between mb-2">
            <p className="text-gray-600 text-sm font-medium">Pending Approval</p>
            <Clock className="w-5 h-5 text-yellow-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{summary.pending_approvals}</p>
          <p className="text-sm text-gray-500 mt-2">Awaiting review</p>
        </div>

        {/* Active Users */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-purple-500">
          <div className="flex items-center justify-between mb-2">
            <p className="text-gray-600 text-sm font-medium">Active Users</p>
            <Users className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{summary.active_users}</p>
          <p className="text-sm text-gray-500 mt-2">In organization</p>
        </div>
      </div>

      {/* Charts Row 1: Spending Over Time */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Spending Trend (Last {timeRange} Days)
        </h3>
        {analytics.spending_over_time.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={analytics.spending_over_time}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 12 }}
              />
              <YAxis tickFormatter={(value) => `$${value}`} tick={{ fontSize: 12 }} />
              <Tooltip
                formatter={(value) => formatCurrency(value)}
                labelFormatter={formatDate}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="amount"
                stroke={COLORS.primary}
                strokeWidth={2}
                name="Spending"
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-500 text-center py-12">No spending data available</p>
        )}
      </div>

      {/* Charts Row 2: Category Breakdown and Top Spenders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown Pie Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Spending by Category
          </h3>
          {analytics.category_breakdown.length > 0 ? (
            <div>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={analytics.category_breakdown}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ category, amount }) =>
                      `${category}: ${formatCurrency(amount)}`
                    }
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="amount"
                  >
                    {analytics.category_breakdown.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={CATEGORY_COLORS[entry.category] || COLORS.teal}
                      />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatCurrency(value)} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-4 space-y-2">
                {analytics.category_breakdown.map((cat) => (
                  <div key={cat.category} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: CATEGORY_COLORS[cat.category] || COLORS.teal }}
                      ></div>
                      <span className="text-gray-700">{cat.category}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-gray-600">{cat.count} expenses</span>
                      <span className="font-semibold text-gray-900">
                        {formatCurrency(cat.amount)}
                      </span>
                      <span className="text-gray-500 text-xs">
                        ({calculatePercentage(cat.amount, totalCategoryAmount)}%)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-12">No category data available</p>
          )}
        </div>

        {/* Top Spenders Bar Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Spenders</h3>
          {analytics.top_spenders.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={analytics.top_spenders.slice(0, 5)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(value) => `$${value}`} tick={{ fontSize: 12 }} />
                <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => formatCurrency(value)} />
                <Bar dataKey="total_amount" fill={COLORS.success} name="Total Spent" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-center py-12">No spender data available</p>
          )}
          <div className="mt-4 space-y-2">
            {analytics.top_spenders.slice(0, 5).map((spender, idx) => (
              <div key={spender.username} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 font-medium">#{idx + 1}</span>
                  <span className="text-gray-700">{spender.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-gray-600">{spender.expense_count} expenses</span>
                  <span className="font-semibold text-gray-900">
                    {formatCurrency(spender.total_amount)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Row 3: Status Distribution and Top Vendors */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Expense Status</h3>
          {analytics.status_distribution.length > 0 ? (
            <div>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={analytics.status_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                    label={({ status, count }) => `${status}: ${count}`}
                  >
                    {analytics.status_distribution.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={STATUS_COLORS[entry.status] || "#9CA3AF"}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-4 space-y-2">
                {analytics.status_distribution.map((status) => (
                  <div key={status.status} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: STATUS_COLORS[status.status] || "#9CA3AF" }}
                      ></div>
                      <span className="text-gray-700">{status.status}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-gray-600">{status.count} expenses</span>
                      <span className="font-semibold text-gray-900">
                        {formatCurrency(status.amount)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-12">No status data available</p>
          )}
        </div>

        {/* Top Vendors */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Vendors</h3>
          {analytics.top_vendors.length > 0 ? (
            <div className="space-y-3">
              {analytics.top_vendors.slice(0, 8).map((vendor, idx) => (
                <div
                  key={vendor.vendor}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500 font-semibold text-sm">#{idx + 1}</span>
                    <div>
                      <p className="font-medium text-gray-900">{vendor.vendor}</p>
                      <p className="text-sm text-gray-500">{vendor.count} transactions</p>
                    </div>
                  </div>
                  <span className="font-semibold text-gray-900">
                    {formatCurrency(vendor.amount)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-12">No vendor data available</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
