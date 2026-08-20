import React, { useState, useEffect } from "react";
import {
  Bot,
  Sparkles,
  CheckCircle,
  ArrowRight,
  Zap,
  Shield,
  Clock,
  X,
} from "lucide-react";
import { useToast } from "../hooks/useToast";

const STORAGE_KEY = "ap2_onboarding_dismissed";

const AP2Onboarding = ({ onComplete }) => {
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState([]);
  const [creating, setCreating] = useState(null);
  const [created, setCreated] = useState([]);
  const { success, error: showError } = useToast();

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await fetch("/api/ap2/sample-mandates", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setTemplates(data.templates || []);
      }
    } catch {
      // silent
    }
  };

  const createFromTemplate = async (template) => {
    setCreating(template.name);
    try {
      const response = await fetch("/api/ap2/intent-mandate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({
          constraints: template.constraints,
          expiration_hours: template.expiration_hours,
        }),
      });
      if (response.ok) {
        setCreated((prev) => [...prev, template.name]);
        success(`"${template.name}" rule created!`);
      } else {
        const errorData = await response.json().catch(() => ({}));
        showError(errorData.detail || "Failed to create rule");
      }
    } catch {
      showError("Failed to create rule");
    } finally {
      setCreating(null);
    }
  };

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    if (onComplete) onComplete();
  };

  const steps = [
    // Step 0: Welcome
    <div key="welcome" className="text-center">
      <div className="w-16 h-16 bg-purple-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
        <Bot className="w-8 h-8 text-purple-600" />
      </div>
      <h2 className="text-2xl font-bold text-gray-900 mb-3">
        Welcome to AP2 Automation
      </h2>
      <p className="text-gray-600 mb-8 max-w-md mx-auto">
        AP2 uses Intent Mandates to auto-approve your routine expenses
        instantly. No more waiting days for manager approval on everyday
        purchases.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8 max-w-lg mx-auto">
        <div className="bg-green-50 rounded-xl p-4 text-center">
          <Zap className="w-6 h-6 text-green-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-green-900">Instant</p>
          <p className="text-xs text-green-700">Approved in seconds</p>
        </div>
        <div className="bg-purple-50 rounded-xl p-4 text-center">
          <Shield className="w-6 h-6 text-purple-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-purple-900">Secure</p>
          <p className="text-xs text-purple-700">Cryptographic audit trail</p>
        </div>
        <div className="bg-blue-50 rounded-xl p-4 text-center">
          <Clock className="w-6 h-6 text-blue-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-blue-900">Save Time</p>
          <p className="text-xs text-blue-700">~3 min per expense</p>
        </div>
      </div>
      <button
        onClick={() => setStep(1)}
        className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium flex items-center gap-2 mx-auto"
      >
        See How It Works
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>,

    // Step 1: How it works
    <div key="how">
      <h2 className="text-xl font-bold text-gray-900 mb-6 text-center">
        How Auto-Approval Works
      </h2>
      <div className="space-y-4 mb-8">
        <div className="flex items-start gap-4 p-4 bg-purple-50 rounded-xl">
          <div className="w-8 h-8 bg-purple-600 text-white rounded-full flex items-center justify-center flex-shrink-0 font-bold text-sm">
            1
          </div>
          <div>
            <p className="font-semibold text-purple-900">
              You create a rule (Intent Mandate)
            </p>
            <p className="text-sm text-purple-700 mt-1">
              Example: "Auto-approve office supplies up to $100 each, max
              $300/month"
            </p>
          </div>
        </div>
        <div className="flex items-start gap-4 p-4 bg-blue-50 rounded-xl">
          <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center flex-shrink-0 font-bold text-sm">
            2
          </div>
          <div>
            <p className="font-semibold text-blue-900">You submit an expense</p>
            <p className="text-sm text-blue-700 mt-1">
              Submit a $45 office supplies expense like you normally would.
            </p>
          </div>
        </div>
        <div className="flex items-start gap-4 p-4 bg-green-50 rounded-xl">
          <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center flex-shrink-0 font-bold text-sm">
            3
          </div>
          <div>
            <p className="font-semibold text-green-900">
              AI approves it instantly
            </p>
            <p className="text-sm text-green-700 mt-1">
              The AI agent checks your rule, sees it matches, and approves
              immediately. No manager needed!
            </p>
          </div>
        </div>
      </div>
      <div className="flex gap-3 justify-center">
        <button
          onClick={() => setStep(0)}
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
        >
          Back
        </button>
        <button
          onClick={() => setStep(2)}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium flex items-center gap-2"
        >
          Create Your First Rule
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>,

    // Step 2: Sample mandates
    <div key="templates">
      <h2 className="text-xl font-bold text-gray-900 mb-2 text-center">
        Quick-Start Templates
      </h2>
      <p className="text-sm text-gray-500 text-center mb-6">
        Click to create a rule. You can modify or delete them anytime.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">
        {templates.map((t) => {
          const isCreated = created.includes(t.name);
          return (
            <div
              key={t.name}
              className={`p-4 rounded-xl border-2 transition-colors ${
                isCreated
                  ? "bg-green-50 border-green-300"
                  : "bg-white border-gray-200 hover:border-purple-300"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-gray-900">{t.name}</p>
                  <p className="text-sm text-gray-500 mt-1">{t.description}</p>
                  <div className="flex gap-3 mt-2 text-xs text-gray-400">
                    <span>Max: ${t.constraints.max_amount}</span>
                    <span>Monthly: ${t.constraints.monthly_limit}</span>
                  </div>
                </div>
                {isCreated ? (
                  <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
                ) : (
                  <button
                    onClick={() => createFromTemplate(t)}
                    disabled={creating === t.name}
                    className="px-3 py-1.5 bg-purple-600 text-white text-xs font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 flex-shrink-0"
                  >
                    {creating === t.name ? "..." : "Create"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex gap-3 justify-center">
        <button
          onClick={() => setStep(1)}
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
        >
          Back
        </button>
        <button
          onClick={dismiss}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
        >
          {created.length > 0 ? "Done - Go to Dashboard" : "Skip for Now"}
        </button>
      </div>
    </div>,
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-purple-200 p-8 relative">
      <button
        onClick={dismiss}
        className="absolute top-4 right-4 p-1 text-gray-400 hover:text-gray-600 rounded"
        title="Dismiss"
      >
        <X className="w-5 h-5" />
      </button>

      {/* Progress dots */}
      <div className="flex justify-center gap-2 mb-8">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={`w-2.5 h-2.5 rounded-full transition-colors ${
              i === step
                ? "bg-purple-600"
                : i < step
                  ? "bg-purple-300"
                  : "bg-gray-200"
            }`}
          />
        ))}
      </div>

      {steps[step]}
    </div>
  );
};

AP2Onboarding.STORAGE_KEY = STORAGE_KEY;
export default AP2Onboarding;
