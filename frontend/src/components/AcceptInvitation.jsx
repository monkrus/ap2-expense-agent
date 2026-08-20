import React, { useState } from "react";
import {
  Mail,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader,
  Building2,
  ArrowRight,
  Lock,
  User,
  Eye,
  EyeOff,
  UserPlus,
  LogIn,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../hooks/useToast";
import organizationAPI from "../services/organizationAPI";

const PasswordRequirement = ({ met, children }) => (
  <div className="flex items-center gap-2 text-xs">
    {met ? (
      <CheckCircle className="w-3.5 h-3.5 text-green-600" />
    ) : (
      <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-300" />
    )}
    <span className={met ? "text-green-600" : "text-gray-500"}>{children}</span>
  </div>
);

const AcceptInvitation = ({ token }) => {
  const { user, login, register } = useAuth();
  const { success, error: showError } = useToast();

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("idle"); // idle, accepting, success, error
  const [errorMessage, setErrorMessage] = useState("");

  // Auth form state (for unauthenticated users)
  const [authMode, setAuthMode] = useState("register"); // "register" or "login"
  const [formData, setFormData] = useState({
    email: "",
    username: "",
    password: "",
    confirmPassword: "",
    full_name: "",
  });
  const [formError, setFormError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordValidation, setPasswordValidation] = useState({
    minLength: false,
    hasUpper: false,
    hasLower: false,
    hasDigit: false,
  });

  const validatePassword = (password) => {
    setPasswordValidation({
      minLength: password.length >= 8,
      hasUpper: /[A-Z]/.test(password),
      hasLower: /[a-z]/.test(password),
      hasDigit: /\d/.test(password),
    });
  };

  const handleAccept = async () => {
    setLoading(true);
    setStatus("accepting");

    try {
      await organizationAPI.acceptInvitation(token);
      setStatus("success");
      success("Invitation accepted! Redirecting...");

      setTimeout(() => {
        window.location.href = "/";
      }, 2000);
    } catch (err) {
      setStatus("error");
      setErrorMessage(err.message || "Failed to accept invitation");
      showError(err.message || "Failed to accept invitation");
    } finally {
      setLoading(false);
    }
  };

  // Register, then login, then accept — all in one flow
  const handleRegisterAndAccept = async (e) => {
    e.preventDefault();
    setFormError("");

    if (formData.password !== formData.confirmPassword) {
      setFormError("Passwords do not match");
      return;
    }
    if (!Object.values(passwordValidation).every(Boolean)) {
      setFormError("Password does not meet all requirements");
      return;
    }

    setLoading(true);

    try {
      // Step 1: Register
      const regResult = await register({
        email: formData.email,
        username: formData.username,
        password: formData.password,
        full_name: formData.full_name || undefined,
        role: "employee",
      });

      if (!regResult.success) {
        setFormError(regResult.error || "Registration failed");
        setLoading(false);
        return;
      }

      // Step 2: Login with the new credentials
      const loginResult = await login(formData.username, formData.password);

      if (!loginResult.success) {
        setFormError(loginResult.error || "Login failed after registration");
        setLoading(false);
        return;
      }

      // Step 3: Accept the invitation (user is now authenticated)
      setStatus("accepting");

      // Small delay to let auth state settle
      setTimeout(async () => {
        try {
          await organizationAPI.acceptInvitation(token);
          setStatus("success");
          success("Account created and invitation accepted!");
        } catch (err) {
          // "already a member" means acceptance worked — treat as success
          const msg = (err.message || "").toLowerCase();
          if (
            msg.includes("already a member") ||
            msg.includes("already used")
          ) {
            setStatus("success");
            success("Account created and invitation accepted!");
          } else {
            setStatus("error");
            setErrorMessage(err.message || "Failed to accept invitation");
            showError(
              err.message ||
                "Account created but failed to accept invitation. Please try the link again.",
            );
          }
        }
        setLoading(false);
        setTimeout(() => {
          window.location.href = "/";
        }, 2000);
      }, 500);
    } catch (err) {
      setFormError(err.message || "An error occurred");
      setLoading(false);
    }
  };

  // Login then accept
  const handleLoginAndAccept = async (e) => {
    e.preventDefault();
    setFormError("");
    setLoading(true);

    try {
      const loginResult = await login(formData.username, formData.password);

      if (!loginResult.success) {
        setFormError(loginResult.error || "Login failed");
        setLoading(false);
        return;
      }

      // Accept after login
      setStatus("accepting");
      setTimeout(async () => {
        try {
          await organizationAPI.acceptInvitation(token);
          setStatus("success");
          success("Invitation accepted!");
        } catch (err) {
          const msg = (err.message || "").toLowerCase();
          if (
            msg.includes("already a member") ||
            msg.includes("already used")
          ) {
            setStatus("success");
            success("Invitation accepted!");
          } else {
            setStatus("error");
            setErrorMessage(err.message || "Failed to accept invitation");
            showError(err.message || "Failed to accept invitation");
          }
        }
        setLoading(false);
        setTimeout(() => {
          window.location.href = "/";
        }, 2000);
      }, 500);
    } catch (err) {
      setFormError(err.message || "An error occurred");
      setLoading(false);
    }
  };

  // ── Success state ──
  if (status === "success") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-6">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Invitation Accepted!
          </h2>
          <p className="text-gray-600 mb-6">
            You've successfully joined the organization
          </p>
          <div className="flex items-center justify-center gap-2 text-indigo-600">
            <span className="text-sm">Redirecting to dashboard</span>
            <ArrowRight className="w-4 h-4 animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  // ── Error state ──
  if (status === "error") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-6">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-8 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <XCircle className="w-8 h-8 text-red-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Unable to Accept Invitation
          </h2>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 text-left">{errorMessage}</p>
            </div>
          </div>
          <div className="space-y-3">
            <button
              onClick={() => {
                setStatus("idle");
                handleAccept();
              }}
              className="w-full px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Try Again
            </button>
            <button
              onClick={() => {
                window.location.href = "/";
              }}
              className="w-full px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Accepting state ──
  if (status === "accepting") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-6">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-8 text-center">
          <Loader className="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Accepting Invitation...
          </h2>
          <p className="text-gray-600">Please wait</p>
        </div>
      </div>
    );
  }

  // ── Already logged in — show accept/decline ──
  if (user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-6">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-8">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Mail className="w-8 h-8 text-indigo-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Organization Invitation
            </h1>
            <p className="text-gray-600">
              You've been invited to join an organization
            </p>
          </div>

          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-3">
              <Building2 className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500">Logged in as</p>
                <p className="font-medium text-gray-900">{user.email}</p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <button
              onClick={handleAccept}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {loading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  Accepting...
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5" />
                  Accept Invitation
                </>
              )}
            </button>
            <button
              onClick={() => {
                window.location.href = "/";
              }}
              disabled={loading}
              className="w-full px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Decline
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Not logged in — show register/login form inline ──
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-6">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-8">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Mail className="w-8 h-8 text-indigo-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Organization Invitation
          </h1>
          <p className="text-gray-600">
            {authMode === "register"
              ? "Create an account to accept this invitation"
              : "Log in to accept this invitation"}
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex rounded-lg bg-gray-100 p-1 mb-6">
          <button
            onClick={() => {
              setAuthMode("register");
              setFormError("");
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              authMode === "register"
                ? "bg-white text-indigo-600 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <UserPlus className="w-4 h-4" />
            New Account
          </button>
          <button
            onClick={() => {
              setAuthMode("login");
              setFormError("");
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              authMode === "login"
                ? "bg-white text-indigo-600 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <LogIn className="w-4 h-4" />
            Existing Account
          </button>
        </div>

        {formError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{formError}</p>
          </div>
        )}

        {authMode === "register" ? (
          <form onSubmit={handleRegisterAndAccept} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                  placeholder="Your email"
                  required
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) =>
                    setFormData({ ...formData, username: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                  placeholder="Choose a username"
                  required
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Full Name (Optional)
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={(e) =>
                    setFormData({ ...formData, full_name: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                  placeholder="Your full name"
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={(e) => {
                    setFormData({ ...formData, password: e.target.value });
                    validatePassword(e.target.value);
                  }}
                  className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                  placeholder="Create a password"
                  required
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
              <div className="mt-1.5 grid grid-cols-2 gap-1">
                <PasswordRequirement met={passwordValidation.minLength}>
                  8+ characters
                </PasswordRequirement>
                <PasswordRequirement met={passwordValidation.hasUpper}>
                  Uppercase
                </PasswordRequirement>
                <PasswordRequirement met={passwordValidation.hasLower}>
                  Lowercase
                </PasswordRequirement>
                <PasswordRequirement met={passwordValidation.hasDigit}>
                  Number
                </PasswordRequirement>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  value={formData.confirmPassword}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      confirmPassword: e.target.value,
                    })
                  }
                  className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                  placeholder="Confirm password"
                  required
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-4"
            >
              {loading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  Creating account...
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5" />
                  Create Account & Accept
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleLoginAndAccept} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username or Email
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) =>
                    setFormData({ ...formData, username: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                  placeholder="Username or email"
                  required
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                  placeholder="Your password"
                  required
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-4"
            >
              {loading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  Logging in...
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  Log In & Accept
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default AcceptInvitation;
