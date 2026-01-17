import React, { useState } from "react";
import {
  X,
  Plus,
  Trash2,
  DollarSign,
  Tag,
  Store,
  Clock,
  CheckCircle,
  AlertCircle,
  Calendar,
  Sparkles,
} from "lucide-react";
import { useToast } from "../hooks/useToast";

const ConstraintBuilder = ({ onClose, onSuccess }) => {
  const { success, error: showError } = useToast();
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1); // 1: Basic, 2: Advanced, 3: Review

  const [formData, setFormData] = useState({
    maxAmount: "",
    categories: [],
    merchants: [],
    approvalRequired: true,
    recurring: "",
    expirationHours: "720", // 30 days default
  });

  const [categoryInput, setCategoryInput] = useState("");
  const [merchantInput, setMerchantInput] = useState("");

  // Predefined categories for quick selection
  const predefinedCategories = [
    "Travel",
    "Meals",
    "Software",
    "Office Supplies",
    "Transportation",
    "Entertainment",
    "Equipment",
    "Marketing",
    "Training",
    "Consulting",
  ];

  const recurringOptions = [
    { value: "", label: "One-time" },
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    // Build constraints object
    const constraints = {
      max_amount: parseFloat(formData.maxAmount) || null,
      categories: formData.categories.length > 0 ? formData.categories : null,
      merchants: formData.merchants.length > 0 ? formData.merchants : null,
      approval_required: formData.approvalRequired,
    };

    if (formData.recurring) {
      constraints.recurring = formData.recurring;
    }

    // Remove null values
    Object.keys(constraints).forEach((key) => {
      if (constraints[key] === null) delete constraints[key];
    });

    try {
      const response = await fetch("/api/ap2/intent-mandate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({
          constraints,
          expiration_hours: parseInt(formData.expirationHours),
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to create Intent Mandate");
      }

      const result = await response.json();
      onSuccess(result);
    } catch (err) {
      console.error(err);
      showError("Failed to create Intent Mandate. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const addCategory = (category) => {
    if (category && !formData.categories.includes(category)) {
      setFormData({
        ...formData,
        categories: [...formData.categories, category],
      });
      setCategoryInput("");
    }
  };

  const removeCategory = (category) => {
    setFormData({
      ...formData,
      categories: formData.categories.filter((c) => c !== category),
    });
  };

  const addMerchant = () => {
    if (
      merchantInput.trim() &&
      !formData.merchants.includes(merchantInput.trim())
    ) {
      setFormData({
        ...formData,
        merchants: [...formData.merchants, merchantInput.trim()],
      });
      setMerchantInput("");
    }
  };

  const removeMerchant = (merchant) => {
    setFormData({
      ...formData,
      merchants: formData.merchants.filter((m) => m !== merchant),
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Create Intent Mandate</h2>
              <p className="text-purple-100 text-sm">Step {step} of 3</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Progress Steps */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            {[
              { num: 1, label: "Basic Settings" },
              { num: 2, label: "Advanced Rules" },
              { num: 3, label: "Review & Create" },
            ].map((s, idx) => (
              <React.Fragment key={s.num}>
                <div className="flex items-center space-x-2">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold ${
                      step >= s.num
                        ? "bg-purple-600 text-white"
                        : "bg-gray-200 text-gray-600"
                    }`}
                  >
                    {step > s.num ? <CheckCircle className="w-5 h-5" /> : s.num}
                  </div>
                  <span
                    className={`text-sm font-medium ${
                      step >= s.num ? "text-gray-900" : "text-gray-500"
                    }`}
                  >
                    {s.label}
                  </span>
                </div>
                {idx < 2 && (
                  <div
                    className={`flex-1 h-1 mx-4 rounded ${
                      step > s.num ? "bg-purple-600" : "bg-gray-200"
                    }`}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Form Content */}
        <form
          onSubmit={handleSubmit}
          className="p-6 overflow-y-auto max-h-[calc(90vh-240px)]"
        >
          {/* Step 1: Basic Settings */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Basic Settings
                </h3>
                <p className="text-sm text-gray-600 mb-6">
                  Set the fundamental constraints for what your AI agent can do.
                </p>
              </div>

              {/* Max Amount */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <DollarSign className="w-4 h-4 inline mr-1" />
                  Maximum Amount (Optional)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.maxAmount}
                  onChange={(e) =>
                    setFormData({ ...formData, maxAmount: e.target.value })
                  }
                  placeholder="e.g., 1000.00"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Leave empty for no limit. Agent will not process expenses
                  above this amount.
                </p>
              </div>

              {/* Expiration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  Expires After
                </label>
                <select
                  value={formData.expirationHours}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      expirationHours: e.target.value,
                    })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                >
                  <option value="24">24 hours (1 day)</option>
                  <option value="168">1 week</option>
                  <option value="720">30 days (recommended)</option>
                  <option value="2160">90 days</option>
                  <option value="4320">180 days</option>
                  <option value="8760">1 year</option>
                </select>
              </div>

              {/* Approval Required */}
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <label className="flex items-start space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.approvalRequired}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        approvalRequired: e.target.checked,
                      })
                    }
                    className="mt-1 w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                  />
                  <div className="flex-1">
                    <span className="text-sm font-medium text-gray-900 block">
                      Require Manual Approval
                    </span>
                    <span className="text-xs text-gray-600 block mt-1">
                      When checked, all expenses will require your approval.
                      Uncheck for full automation (not recommended for first
                      mandate).
                    </span>
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* Step 2: Advanced Rules */}
          {step === 2 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Advanced Rules
                </h3>
                <p className="text-sm text-gray-600 mb-6">
                  Refine your agent's permissions with categories, merchants,
                  and recurring options.
                </p>
              </div>

              {/* Categories */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Tag className="w-4 h-4 inline mr-1" />
                  Allowed Categories (Optional)
                </label>

                {/* Predefined Categories */}
                <div className="flex flex-wrap gap-2 mb-3">
                  {predefinedCategories.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => addCategory(cat)}
                      disabled={formData.categories.includes(cat)}
                      className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                        formData.categories.includes(cat)
                          ? "bg-purple-100 text-purple-700"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {formData.categories.includes(cat) ? (
                        <CheckCircle className="w-3 h-3 inline mr-1" />
                      ) : (
                        <Plus className="w-3 h-3 inline mr-1" />
                      )}
                      {cat}
                    </button>
                  ))}
                </div>

                {/* Custom Category Input */}
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={categoryInput}
                    onChange={(e) => setCategoryInput(e.target.value)}
                    onKeyPress={(e) =>
                      e.key === "Enter" &&
                      (e.preventDefault(), addCategory(categoryInput))
                    }
                    placeholder="Or type custom category..."
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => addCategory(categoryInput)}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    Add
                  </button>
                </div>

                {/* Selected Categories */}
                {formData.categories.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {formData.categories.map((cat) => (
                      <span
                        key={cat}
                        className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800"
                      >
                        {cat}
                        <button
                          type="button"
                          onClick={() => removeCategory(cat)}
                          className="ml-2 hover:text-purple-900"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                <p className="text-xs text-gray-500 mt-2">
                  Leave empty to allow all categories. Agent will only process
                  expenses in selected categories.
                </p>
              </div>

              {/* Merchants */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Store className="w-4 h-4 inline mr-1" />
                  Allowed Merchants (Optional)
                </label>

                <div className="flex space-x-2 mb-3">
                  <input
                    type="text"
                    value={merchantInput}
                    onChange={(e) => setMerchantInput(e.target.value)}
                    onKeyPress={(e) =>
                      e.key === "Enter" && (e.preventDefault(), addMerchant())
                    }
                    placeholder="e.g., Amazon, Starbucks, Uber..."
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={addMerchant}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    Add
                  </button>
                </div>

                {formData.merchants.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {formData.merchants.map((merchant) => (
                      <span
                        key={merchant}
                        className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
                      >
                        {merchant}
                        <button
                          type="button"
                          onClick={() => removeMerchant(merchant)}
                          className="ml-2 hover:text-blue-900"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                <p className="text-xs text-gray-500 mt-2">
                  Leave empty to allow all merchants.
                </p>
              </div>

              {/* Recurring */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Clock className="w-4 h-4 inline mr-1" />
                  Recurring Schedule
                </label>
                <select
                  value={formData.recurring}
                  onChange={(e) =>
                    setFormData({ ...formData, recurring: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                >
                  {recurringOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Set if this mandate should handle recurring expenses
                  automatically.
                </p>
              </div>
            </div>
          )}

          {/* Step 3: Review */}
          {step === 3 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Review & Create
                </h3>
                <p className="text-sm text-gray-600 mb-6">
                  Review your Intent Mandate settings before creating.
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-6 space-y-4">
                <ReviewItem
                  label="Maximum Amount"
                  value={
                    formData.maxAmount
                      ? `$${parseFloat(formData.maxAmount).toFixed(2)}`
                      : "No limit"
                  }
                  icon={<DollarSign className="w-5 h-5 text-green-600" />}
                />

                <ReviewItem
                  label="Expires After"
                  value={`${formData.expirationHours} hours (${Math.round(parseInt(formData.expirationHours) / 24)} days)`}
                  icon={<Calendar className="w-5 h-5 text-blue-600" />}
                />

                <ReviewItem
                  label="Approval Required"
                  value={
                    formData.approvalRequired ? "Yes" : "No (Auto-approve)"
                  }
                  icon={<CheckCircle className="w-5 h-5 text-yellow-600" />}
                />

                {formData.categories.length > 0 && (
                  <ReviewItem
                    label="Allowed Categories"
                    value={formData.categories.join(", ")}
                    icon={<Tag className="w-5 h-5 text-purple-600" />}
                  />
                )}

                {formData.merchants.length > 0 && (
                  <ReviewItem
                    label="Allowed Merchants"
                    value={formData.merchants.join(", ")}
                    icon={<Store className="w-5 h-5 text-indigo-600" />}
                  />
                )}

                {formData.recurring && (
                  <ReviewItem
                    label="Recurring Schedule"
                    value={
                      recurringOptions.find(
                        (o) => o.value === formData.recurring,
                      )?.label
                    }
                    icon={<Clock className="w-5 h-5 text-orange-600" />}
                  />
                )}
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-900">
                  <p className="font-medium mb-1">AP2 Protocol Security</p>
                  <p className="text-blue-800">
                    Your Intent Mandate will be cryptographically signed and
                    stored with a complete audit trail. All expenses processed
                    under this mandate will be traceable and compliant.
                  </p>
                </div>
              </div>
            </div>
          )}
        </form>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <div>
            {step > 1 && (
              <button
                type="button"
                onClick={() => setStep(step - 1)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors font-medium"
              >
                Back
              </button>
            )}
          </div>

          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors font-medium"
            >
              Cancel
            </button>

            {step < 3 ? (
              <button
                type="button"
                onClick={() => setStep(step + 1)}
                className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
              >
                Next
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={loading}
                className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Creating...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    <span>Create Mandate</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Review Item Component
const ReviewItem = ({ label, value, icon }) => {
  return (
    <div className="flex items-start space-x-3">
      <div className="flex-shrink-0">{icon}</div>
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-900">{label}</p>
        <p className="text-sm text-gray-600 mt-0.5">{value}</p>
      </div>
    </div>
  );
};

export default ConstraintBuilder;
