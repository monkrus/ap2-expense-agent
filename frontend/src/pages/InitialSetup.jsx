import React, { useState } from "react";
import { Shield, Building2, CheckCircle, Eye, EyeOff } from "lucide-react";

/**
 * InitialSetup — First-Time Admin Account Creation
 *
 * Shown when the database has zero users (clean-slate deployment or fresh
 * install).  The first user created here is
 * automatically promoted to ADMIN by the backend.
 *
 * After successful creation the user is directed to Login.
 */
const InitialSetup = ({ onComplete }) => {
  const [form, setForm] = useState({
    full_name: "",
    username: "",
    email: "",
    password: "",
    confirm_password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError("");
  };

  const validate = () => {
    if (!form.full_name.trim()) return "Full name is required.";
    if (!form.username.trim()) return "Username is required.";
    if (!form.email.trim()) return "Email is required.";
    if (form.password.length < 8)
      return "Password must be at least 8 characters.";
    if (!/[A-Z]/.test(form.password))
      return "Password must contain an uppercase letter.";
    if (!/[0-9]/.test(form.password)) return "Password must contain a number.";
    if (form.password !== form.confirm_password)
      return "Passwords do not match.";
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: form.full_name,
          username: form.username,
          email: form.email,
          password: form.password,
          role: "admin",
        }),
      });

      if (!res.ok) {
        let errorMessage = "Registration failed. Please try again.";
        try {
          const data = await res.json();
          errorMessage = data.detail || errorMessage;
        } catch {
          if (res.status >= 500)
            errorMessage = "Server error. Please try again later.";
        }
        setError(errorMessage);
        return;
      }

      setDone(true);
    } catch {
      setError("Network error. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-10 max-w-md w-full text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Admin account created!
          </h2>
          <p className="text-gray-600 mb-8">
            You can now log in with your credentials and start configuring your
            organisation.
          </p>
          <button
            onClick={onComplete}
            className="w-full py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-8 py-8 text-white">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <Shield className="w-7 h-7" />
            </div>
            <div>
              <p className="text-sm font-medium text-indigo-200">
                AP2 Expense Agent
              </p>
              <h1 className="text-xl font-bold">First-Time Setup</h1>
            </div>
          </div>
          <div className="flex items-start gap-2 bg-white/10 rounded-xl p-3 text-sm">
            <Building2 className="w-4 h-4 mt-0.5 flex-shrink-0 text-indigo-200" />
            <p className="text-indigo-100">
              No accounts exist yet. Create the initial admin account to get
              started. The first user is always granted full admin privileges.
            </p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-8 py-8 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Full Name
            </label>
            <input
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              placeholder="Jane Smith"
              required
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-colors"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username
              </label>
              <input
                name="username"
                value={form.username}
                onChange={handleChange}
                placeholder="jsmith"
                required
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="jane@company.com"
                required
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <div className="relative">
              <input
                name="password"
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={handleChange}
                placeholder="Min 8 chars, 1 uppercase, 1 number"
                required
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-colors pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password
            </label>
            <input
              name="confirm_password"
              type={showPassword ? "text" : "password"}
              value={form.confirm_password}
              onChange={handleChange}
              placeholder="Repeat password"
              required
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-colors"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-2"
          >
            {loading ? "Creating account…" : "Create Admin Account"}
          </button>

          <p className="text-xs text-center text-gray-400">
            This screen only appears on a clean deployment. Subsequent users are
            added by the admin.
          </p>
        </form>
      </div>
    </div>
  );
};

export default InitialSetup;
