import React, { useState, useEffect, useRef } from "react";
import {
  Bell,
  Check,
  CheckCheck,
  Clock,
  DollarSign,
  Repeat,
  AlertCircle,
  Info,
  X,
  Shield,
  ArrowRight,
  XCircle,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const NotificationCenter = ({ onNavigate, onRuleRequestAction }) => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [denyModal, setDenyModal] = useState(null); // { notificationId, message }
  const [denyNote, setDenyNote] = useState("");
  const [denyLoading, setDenyLoading] = useState(false);
  const dropdownRef = useRef(null);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    fetchNotifications();
    fetchUnreadCount();

    const interval = setInterval(() => {
      fetchUnreadCount();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        if (!denyModal) setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [denyModal]);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("access_token");
      const response = await fetch("/api/notifications?limit=20", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json().catch(() => ({}));
        setNotifications(data.notifications || []);
      }
    } catch (err) {
      console.error("Failed to fetch notifications:", err);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchUnreadCount = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch("/api/notifications/unread-count", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json().catch(() => ({}));
        setUnreadCount(data.unread_count || 0);
      }
    } catch (err) {
      console.error("Failed to fetch unread count:", err);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(
        `/api/notifications/${notificationId}/read`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (response.ok) {
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === notificationId
              ? { ...n, is_read: true, read_at: new Date().toISOString() }
              : n,
          ),
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    }
  };

  const markAllAsRead = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch("/api/notifications/mark-all-read", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setNotifications((prev) =>
          prev.map((n) => ({
            ...n,
            is_read: true,
            read_at: new Date().toISOString(),
          })),
        );
        setUnreadCount(0);
      }
    } catch (err) {
      console.error("Failed to mark all as read:", err);
    }
  };

  const toggleDropdown = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      fetchNotifications();
    }
  };

  // Parse rule request details from notification message
  const parseRuleRequestDetails = (message) => {
    const details = {};
    const categoryMatch = message.match(/Category:\s*([^,\n]+)/);
    const vendorMatch = message.match(/Vendor:\s*([^,\n]+)/);
    const amountMatch = message.match(/Max amount:\s*\$?([\d.]+)/);
    const reasonMatch = message.match(/Reason:\s*(.+)/s);

    if (categoryMatch) details.category = categoryMatch[1].trim();
    if (vendorMatch) details.vendor = vendorMatch[1].trim();
    if (amountMatch) details.max_amount = amountMatch[1].trim();
    if (reasonMatch) details.reason = reasonMatch[1].trim();

    return details;
  };

  // Find rule request ID from backend by matching notification
  const handleApproveRequest = async (notification) => {
    const details = parseRuleRequestDetails(notification.message);
    markAsRead(notification.id);
    setIsOpen(false);

    // First, approve the rule request in backend
    try {
      const token = localStorage.getItem("access_token");
      const orgId = localStorage.getItem("current_organization_id");

      // Fetch rule requests to find matching one
      const response = await fetch("/api/v1/expenses/rule-requests", {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": orgId,
        },
      });

      if (response.ok) {
        const data = await response.json();
        // Find pending request matching this notification's details
        const matchingRequest = (data.requests || []).find(
          (r) => r.status === "pending" &&
            ((details.category && r.category === details.category) || !details.category) &&
            ((details.vendor && r.vendor === details.vendor) || !details.vendor)
        );

        if (matchingRequest) {
          // Approve it
          await fetch(`/api/v1/expenses/rule-requests/${matchingRequest.id}/approve`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "X-Organization-Id": orgId,
            },
          });
        }
      }
    } catch (err) {
      console.error("Failed to approve rule request:", err);
    }

    // Navigate to approval policies with pre-fill data
    if (onRuleRequestAction) {
      onRuleRequestAction("approve", details);
    } else if (onNavigate) {
      onNavigate("approval-policies", { prefill: details });
    }
  };

  const handleDenyRequest = async () => {
    if (!denyModal) return;
    setDenyLoading(true);

    try {
      const token = localStorage.getItem("access_token");
      const orgId = localStorage.getItem("current_organization_id");
      const details = parseRuleRequestDetails(denyModal.message);

      // Find matching pending request
      const response = await fetch("/api/v1/expenses/rule-requests", {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": orgId,
        },
      });

      if (response.ok) {
        const data = await response.json();
        const matchingRequest = (data.requests || []).find(
          (r) => r.status === "pending" &&
            ((details.category && r.category === details.category) || !details.category) &&
            ((details.vendor && r.vendor === details.vendor) || !details.vendor)
        );

        if (matchingRequest) {
          await fetch(`/api/v1/expenses/rule-requests/${matchingRequest.id}/deny`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
              "X-Organization-Id": orgId,
            },
            body: JSON.stringify({ note: denyNote }),
          });
        }
      }

      markAsRead(denyModal.notificationId);
      setDenyModal(null);
      setDenyNote("");
    } catch (err) {
      console.error("Failed to deny rule request:", err);
    } finally {
      setDenyLoading(false);
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case "recurring_submitted":
        return <DollarSign className="w-5 h-5 text-green-600" />;
      case "recurring_reminder":
        return <Clock className="w-5 h-5 text-yellow-600" />;
      case "expense_approved":
        return <Check className="w-5 h-5 text-green-600" />;
      case "expense_rejected":
        return <X className="w-5 h-5 text-red-600" />;
      case "rule_request":
        return <Shield className="w-5 h-5 text-purple-600" />;
      case "rule_request_approved":
        return <Check className="w-5 h-5 text-green-600" />;
      case "rule_request_denied":
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <Info className="w-5 h-5 text-blue-600" />;
    }
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const handleNotificationClick = (notification) => {
    if (!notification.is_read) {
      markAsRead(notification.id);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Icon Button */}
      <button
        onClick={toggleDropdown}
        className="relative p-2 hover:bg-gray-100 rounded-lg transition-colors"
        aria-label="Notifications"
      >
        <Bell className="w-6 h-6 text-gray-600" />
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-red-500 rounded-full">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 md:w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-[500px] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <h3 className="font-semibold text-gray-900">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-xs text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1"
              >
                <CheckCheck className="w-4 h-4" />
                Mark all as read
              </button>
            )}
          </div>

          {/* Notifications List */}
          <div className="overflow-y-auto flex-1">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-8 px-4">
                <Bell className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">No notifications yet</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    onClick={() => handleNotificationClick(notification)}
                    className={`px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                      !notification.is_read ? "bg-blue-50" : ""
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-1">
                        {getNotificationIcon(notification.notification_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p
                          className={`text-sm font-medium text-gray-900 ${
                            !notification.is_read ? "font-semibold" : ""
                          }`}
                        >
                          {notification.title}
                        </p>
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2 whitespace-pre-line">
                          {notification.message}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <p className="text-xs text-gray-500">
                            {formatTime(notification.created_at)}
                          </p>
                          {!notification.is_read && (
                            <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                          )}
                        </div>

                        {/* Rule Request Actions - Admin only */}
                        {notification.notification_type === "rule_request" && isAdmin && (
                          <div className="flex items-center gap-2 mt-3">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleApproveRequest(notification);
                              }}
                              className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 transition-colors"
                            >
                              <Check className="w-3.5 h-3.5" />
                              Approve & Create Rule
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setDenyModal({
                                  notificationId: notification.id,
                                  message: notification.message,
                                });
                              }}
                              className="flex items-center gap-1 px-3 py-1.5 bg-red-100 text-red-700 text-xs font-medium rounded-lg hover:bg-red-200 transition-colors"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              Deny
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="border-t px-4 py-2 bg-gray-50">
              <button
                onClick={() => {
                  setIsOpen(false);
                }}
                className="text-xs text-indigo-600 hover:text-indigo-700 font-medium w-full text-center"
              >
                View all notifications
              </button>
            </div>
          )}
        </div>
      )}

      {/* Deny Modal */}
      {denyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4" onClick={() => { setDenyModal(null); setDenyNote(""); }}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <XCircle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900">Deny Rule Request</h3>
                <p className="text-sm text-gray-500">The employee will be notified</p>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Reason for denial (optional)
              </label>
              <textarea
                value={denyNote}
                onChange={(e) => setDenyNote(e.target.value)}
                rows="3"
                placeholder="e.g., This category is already covered by existing policies, or the amount is too high for auto-approval..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none text-sm"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => { setDenyModal(null); setDenyNote(""); }}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleDenyRequest}
                disabled={denyLoading}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium text-sm disabled:opacity-50"
              >
                {denyLoading ? "Sending..." : "Deny Request"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationCenter;
