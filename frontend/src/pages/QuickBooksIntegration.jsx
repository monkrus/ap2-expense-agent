import React, { useState, useEffect, useCallback } from "react";
import {
  ArrowLeft,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Link2,
  Unlink,
  Clock,
  Database,
  Loader2,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const API_BASE = import.meta.env.VITE_API_URL || "";

const QuickBooksIntegration = () => {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const [error, setError] = useState(null);

  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/v1/quickbooks/status`, {
        headers,
      });
      if (!res.ok) throw new Error("Failed to fetch status");
      const data = await res.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();

    // Check if we just connected (redirect from OAuth callback)
    const params = new URLSearchParams(window.location.search);
    if (params.get("qb") === "connected") {
      // Clean up URL
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [fetchStatus]);

  const handleConnect = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/quickbooks/connect`, {
        headers,
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to start connection");
      }
      const data = await res.json();
      // Redirect to Intuit OAuth
      window.location.href = data.authorization_url;
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm("Disconnect QuickBooks? This will stop all expense syncing.")) {
      return;
    }
    try {
      setDisconnecting(true);
      const res = await fetch(`${API_BASE}/api/v1/quickbooks/disconnect`, {
        method: "DELETE",
        headers,
      });
      if (!res.ok) throw new Error("Failed to disconnect");
      setStatus({ connected: false });
      setSyncResult(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setDisconnecting(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      setSyncResult(null);
      const res = await fetch(`${API_BASE}/api/v1/quickbooks/sync`, {
        method: "POST",
        headers,
      });
      if (!res.ok) throw new Error("Sync failed");
      const data = await res.json();
      setSyncResult(data);
      // Refresh status to update last_sync_at
      await fetchStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  };

  const isAdmin = user?.role === "admin" || user?.role === "owner";

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => (window.location.href = "/")}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800 mb-4 text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </button>
          <h1 className="text-2xl font-bold text-gray-800">
            QuickBooks Integration
          </h1>
          <p className="text-gray-600 mt-1">
            Connect your QuickBooks Online account to automatically sync
            approved expenses.
          </p>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-800 font-medium">Error</p>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-600"
            >
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-lg shadow-lg p-12 text-center">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-3" />
            <p className="text-gray-600">Loading integration status...</p>
          </div>
        ) : !status?.connected ? (
          /* Not connected */
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="text-center max-w-md mx-auto">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Database className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">
                Connect to QuickBooks Online
              </h2>
              <p className="text-gray-600 mb-6">
                Link your QuickBooks account to automatically sync approved
                expenses as Purchase entries. Category mapping and vendor
                matching are handled automatically.
              </p>

              {isAdmin ? (
                <button
                  onClick={handleConnect}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-[#2CA01C] text-white font-semibold rounded-lg hover:bg-[#1a8a0e] transition-colors shadow-md"
                >
                  <Link2 className="w-5 h-5" />
                  Connect to QuickBooks
                </button>
              ) : (
                <p className="text-sm text-gray-500 italic">
                  Only organization admins can connect QuickBooks.
                </p>
              )}

              <div className="mt-8 text-left space-y-3">
                <h3 className="font-medium text-gray-700">
                  What gets synced:
                </h3>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                    Approved expenses are created as Purchases in QuickBooks
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                    Expense categories mapped to your Chart of Accounts
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                    Vendors auto-matched or created in QuickBooks
                  </li>
                </ul>
              </div>
            </div>
          </div>
        ) : (
          /* Connected */
          <div className="space-y-6">
            {/* Connection status card */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-gray-800">
                      QuickBooks Connected
                    </h2>
                    <p className="text-sm text-gray-500">
                      Company ID: {status.realm_id}
                    </p>
                  </div>
                </div>
                {isAdmin && (
                  <button
                    onClick={handleDisconnect}
                    disabled={disconnecting}
                    className="flex items-center gap-2 px-4 py-2 text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors text-sm disabled:opacity-50"
                  >
                    {disconnecting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Unlink className="w-4 h-4" />
                    )}
                    Disconnect
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">
                    Sync Status
                  </p>
                  <p className="font-medium text-gray-800 mt-1">
                    {status.sync_enabled ? (
                      <span className="flex items-center gap-1 text-green-700">
                        <CheckCircle className="w-4 h-4" /> Enabled
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-gray-500">
                        <XCircle className="w-4 h-4" /> Disabled
                      </span>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">
                    Last Synced
                  </p>
                  <p className="font-medium text-gray-800 mt-1 flex items-center gap-1">
                    <Clock className="w-4 h-4 text-gray-400" />
                    {status.last_sync_at
                      ? new Date(status.last_sync_at).toLocaleString()
                      : "Never"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">
                    Token Status
                  </p>
                  <p className="font-medium mt-1">
                    {status.token_valid ? (
                      <span className="text-green-700 flex items-center gap-1">
                        <CheckCircle className="w-4 h-4" /> Valid
                      </span>
                    ) : (
                      <span className="text-amber-600 flex items-center gap-1">
                        <AlertCircle className="w-4 h-4" /> Expired — will
                        auto-refresh on next sync
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>

            {/* Sync actions */}
            {isAdmin && (
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h3 className="font-semibold text-gray-800 mb-3">
                  Manual Sync
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Push all approved expenses that haven't been synced yet to
                  QuickBooks.
                </p>
                <button
                  onClick={handleSync}
                  disabled={syncing}
                  className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
                >
                  {syncing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  {syncing ? "Syncing..." : "Sync Now"}
                </button>

                {/* Sync result */}
                {syncResult && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <p className="font-medium text-gray-800">
                      Sync Complete
                    </p>
                    <div className="flex gap-6 mt-2 text-sm">
                      <span className="text-green-700">
                        {syncResult.synced} synced
                      </span>
                      {syncResult.failed > 0 && (
                        <span className="text-red-600">
                          {syncResult.failed} failed
                        </span>
                      )}
                      <span className="text-gray-500">
                        {syncResult.total} total
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Info card */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 mb-1">
                How syncing works
              </h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>
                  Approved expenses are pushed to QuickBooks as Purchase entries.
                </li>
                <li>
                  Categories are mapped to your QuickBooks Chart of Accounts
                  automatically.
                </li>
                <li>
                  If a vendor doesn't exist in QuickBooks, it will be created.
                </li>
                <li>
                  Tokens are refreshed automatically when they expire.
                </li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default QuickBooksIntegration;
