import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import { OrganizationProvider } from "./contexts/OrganizationContext";
import Login from "./components/Login";
import Register from "./components/Register";
import ProtectedRoute from "./components/ProtectedRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import App from "./App";
import GoogleCallback from "./pages/GoogleCallback";
import BillingDashboard from "./pages/BillingDashboard";
import PricingPlans from "./pages/PricingPlans";
import InitialSetup from "./pages/InitialSetup";
import OrganizationManagement from "./components/OrganizationManagement";
import OrganizationSetupWizard from "./components/OrganizationSetupWizard";
import AcceptInvitation from "./components/AcceptInvitation";

// Key used to track whether this admin has dismissed the setup wizard
const WIZARD_DISMISSED_KEY = "ap2_setup_wizard_dismissed";

const AppContent = () => {
  const [showAuth, setShowAuth] = useState("login");
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const { isAuthenticated, loading, user } = useAuth();

  // null = loading, true = needs setup, false = has users
  const [needsSetup, setNeedsSetup] = useState(null);
  const [showWizard, setShowWizard] = useState(false);

  // --- First-run detection ---
  useEffect(() => {
    fetch("/api/v1/auth/setup-status")
      .then((r) => {
        if (!r.ok) throw new Error(`Setup status check failed: ${r.status}`);
        return r.json();
      })
      .then((data) => {
        const isNew = data.needs_setup === true;
        setNeedsSetup(isNew);
        // Fresh deployment — clear any stale wizard-dismissed flag so the
        // wizard always appears for the first admin on a new installation.
        if (isNew) localStorage.removeItem(WIZARD_DISMISSED_KEY);
      })
      .catch(() => setNeedsSetup(false)); // on error, assume normal flow
  }, []);

  // --- Show setup wizard for admin after first login ---
  useEffect(() => {
    if (
      isAuthenticated &&
      user?.role === "admin" &&
      !localStorage.getItem(WIZARD_DISMISSED_KEY)
    ) {
      setShowWizard(true);
    }
  }, [isAuthenticated, user]);

  // --- Path-based routing ---
  useEffect(() => {
    const handlePopState = () => setCurrentPath(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // Google OAuth callback
  if (
    currentPath === "/auth/google/success" ||
    window.location.pathname === "/auth/google/success"
  ) {
    return <GoogleCallback />;
  }

  // Invitation acceptance
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
    }
    return <AcceptInvitation token={token} />;
  }

  // Organizations page
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

  // Billing page
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

  // Pricing / Plans page
  if (
    currentPath === "/pricing" ||
    currentPath === "/plans" ||
    window.location.pathname === "/pricing" ||
    window.location.pathname === "/plans"
  ) {
    if (isAuthenticated) {
      return (
        <ProtectedRoute>
          <PricingPlans />
        </ProtectedRoute>
      );
    }
    return <PricingPlans />;
  }

  // --- Loading spinner (auth + setup-status check) ---
  if (loading || needsSetup === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500">
        <div className="bg-white p-8 rounded-2xl shadow-2xl">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading…</p>
        </div>
      </div>
    );
  }

  // --- First-time setup (no users in DB) ---
  // Shown to every brand-new deployment or fresh GCP Marketplace purchase.
  if (needsSetup) {
    return (
      <InitialSetup
        onComplete={() => {
          setNeedsSetup(false);
          setShowAuth("login");
        }}
      />
    );
  }

  // --- Not authenticated → Login / Register ---
  if (!isAuthenticated) {
    if (showAuth === "login") {
      return (
        <Login
          onSuccess={() => setShowAuth("app")}
          onSwitchToRegister={() => setShowAuth("register")}
        />
      );
    }
    return (
      <Register
        onSuccess={() => setShowAuth("login")}
        onSwitchToLogin={() => setShowAuth("login")}
      />
    );
  }

  // --- Authenticated: show setup wizard for first-time admin ---
  if (showWizard) {
    return (
      <ProtectedRoute>
        <OrganizationSetupWizard
          onComplete={() => {
            localStorage.setItem(WIZARD_DISMISSED_KEY, "1");
            setShowWizard(false);
          }}
        />
      </ProtectedRoute>
    );
  }

  // --- Check for pending invitation redirect after login ---
  const pendingInvitation = localStorage.getItem("pending_invitation");
  if (pendingInvitation) {
    localStorage.removeItem("pending_invitation");
    window.location.href = pendingInvitation;
    return null;
  }

  // --- Normal authenticated app ---
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
          <OrganizationProvider>
            <AppContent />
          </OrganizationProvider>
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
};

export default AppWrapper;
