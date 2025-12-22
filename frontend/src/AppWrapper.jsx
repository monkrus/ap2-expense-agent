import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import Login from "./components/Login";
import Register from "./components/Register";
import ProtectedRoute from "./components/ProtectedRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import App from "./App";
import GoogleCallback from "./pages/GoogleCallback";
import BillingDashboard from "./pages/BillingDashboard";
import PricingPlans from "./pages/PricingPlans";
import OrganizationManagement from "./components/OrganizationManagement";
import AcceptInvitation from "./components/AcceptInvitation";

const AppContent = () => {
  const [showAuth, setShowAuth] = useState("login");
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const { isAuthenticated, loading } = useAuth();

  // Simple client-side routing
  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // Check if we're on Google OAuth callback page
  if (
    currentPath === "/auth/google/success" ||
    window.location.pathname === "/auth/google/success"
  ) {
    return <GoogleCallback />;
  }

  // Check if we're on invitation acceptance page
  if (
    currentPath.startsWith("/invitations/accept/") ||
    window.location.pathname.startsWith("/invitations/accept/")
  ) {
    const token =
      currentPath.split("/invitations/accept/")[1] ||
      window.location.pathname.split("/invitations/accept/")[1];
    if (isAuthenticated) {
      return (
        <ProtectedRoute>
          <AcceptInvitation token={token} />
        </ProtectedRoute>
      );
    } else {
      // Redirect to login will happen inside AcceptInvitation component
      return <AcceptInvitation token={token} />;
    }
  }

  // Check if we're on organizations page
  if (
    (currentPath === "/organizations" ||
      window.location.pathname === "/organizations") &&
    isAuthenticated
  ) {
    return (
      <ProtectedRoute>
        <OrganizationManagement />
      </ProtectedRoute>
    );
  }

  // Check if we're on billing page
  if (
    (currentPath === "/billing" || window.location.pathname === "/billing") &&
    isAuthenticated
  ) {
    return (
      <ProtectedRoute>
        <BillingDashboard />
      </ProtectedRoute>
    );
  }

  // Check if we're on pricing/plans page
  if (
    currentPath === "/pricing" ||
    currentPath === "/plans" ||
    window.location.pathname === "/pricing" ||
    window.location.pathname === "/plans"
  ) {
    // Pricing page can be accessed without authentication
    if (isAuthenticated) {
      return (
        <ProtectedRoute>
          <PricingPlans />
        </ProtectedRoute>
      );
    } else {
      return <PricingPlans />;
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500">
        <div className="bg-white p-8 rounded-2xl shadow-2xl">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (showAuth === "login") {
      return (
        <Login
          onSuccess={() => setShowAuth("app")}
          onSwitchToRegister={() => setShowAuth("register")}
        />
      );
    } else {
      return (
        <Register
          onSuccess={() => setShowAuth("login")}
          onSwitchToLogin={() => setShowAuth("login")}
        />
      );
    }
  }

  return (
    <ProtectedRoute>
      <App />
    </ProtectedRoute>
  );
};

const AppWrapper = () => {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
};

export default AppWrapper;
