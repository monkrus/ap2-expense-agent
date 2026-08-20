import React, { useState, useEffect } from "react";
import {
  X,
  Save,
  Repeat,
  Calendar,
  DollarSign,
  Tag,
  FileText,
  Clock,
  CheckCircle,
} from "lucide-react";

const RecurringExpenseForm = ({ template, onSuccess, onCancel }) => {
  const isEditing = !!template;

  const [formData, setFormData] = useState({
    vendor: template?.vendor || "",
    amount: template?.amount || "",
    category: template?.category || "TRAVEL",
    description: template?.description || "",
    frequency: template?.frequency || "monthly",
    start_date: template?.start_date
      ? new Date(template.start_date).toISOString().split("T")[0]
      : new Date().toISOString().split("T")[0],
    end_date: template?.end_date
      ? new Date(template.end_date).toISOString().split("T")[0]
      : "",
    auto_submit: template?.auto_submit ?? true,
    intent_mandate_id: template?.intent_mandate_id || "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mandates, setMandates] = useState([]);

  useEffect(() => {
    fetchIntentMandates();
  }, []);

  const fetchIntentMandates = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch("/api/ap2/user/mandates", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json().catch(() => ({}));
        setMandates(data.mandates || []);
      }
    } catch (err) {
      console.error("Failed to fetch intent mandates:", err);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const validateForm = () => {
    if (!formData.vendor.trim()) {
      setError("Vendor is required");
      return false;
    }
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      setError("Amount must be greater than 0");
      return false;
    }
    if (!formData.description.trim()) {
      setError("Description is required");
      return false;
    }
    if (!formData.start_date) {
      setError("Start date is required");
      return false;
    }
    if (
      formData.end_date &&
      new Date(formData.end_date) <= new Date(formData.start_date)
    ) {
      setError("End date must be after start date");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!validateForm()) return;

    setLoading(true);

    try {
      const token = localStorage.getItem("access_token");
      const url = isEditing
        ? `/api/recurring-expenses/${template.id}`
        : "/api/recurring-expenses";

      const method = isEditing ? "PATCH" : "POST";

      // Prepare data
      const submitData = {
        vendor: formData.vendor,
        amount: parseFloat(formData.amount),
        category: formData.category,
        description: formData.description,
        frequency: formData.frequency,
        auto_submit: formData.auto_submit,
      };

      // Only include dates for POST (create), not PATCH (update)
      if (!isEditing) {
        submitData.start_date = new Date(formData.start_date).toISOString();
        if (formData.end_date) {
          submitData.end_date = new Date(formData.end_date).toISOString();
        }
      } else {
        // For updates, only include end_date if changed
        if (formData.end_date) {
          submitData.end_date = new Date(formData.end_date).toISOString();
        }
      }

      // Include intent mandate if selected
      if (formData.intent_mandate_id) {
        submitData.intent_mandate_id = formData.intent_mandate_id;
      }

      const response = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(submitData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to save recurring expense");
      }

      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const categories = [
    { value: "OFFICE_SUPPLIES", label: "Office Supplies" },
    { value: "SOFTWARE", label: "Software" },
    { value: "TRAVEL", label: "Travel" },
    { value: "MEALS", label: "Meals" },
    { value: "ENTERTAINMENT", label: "Entertainment" },
    { value: "UTILITIES", label: "Utilities" },
    { value: "MARKETING", label: "Marketing" },
    { value: "HARDWARE", label: "Hardware" },
    { value: "PROFESSIONAL_SERVICES", label: "Professional Services" },
    { value: "OTHER", label: "Other" },
  ];
  const frequencies = [
    { value: "weekly", label: "Weekly" },
    { value: "biweekly", label: "Bi-weekly" },
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
    { value: "yearly", label: "Yearly" },
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Repeat className="w-6 h-6 text-indigo-600" />
            <h2 className="text-xl font-bold text-gray-900">
              {isEditing ? "Edit Recurring Expense" : "New Recurring Expense"}
            </h2>
          </div>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Vendor */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Vendor <span className="text-red-600">*</span>
            </label>
            <div className="relative">
              <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                name="vendor"
                value={formData.vendor}
                onChange={handleChange}
                placeholder="e.g., AWS, GitHub, Office Depot"
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                required
              />
            </div>
          </div>

          {/* Amount and Category */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Amount <span className="text-red-600">*</span>
              </label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="number"
                  name="amount"
                  value={formData.amount}
                  onChange={handleChange}
                  step="0.01"
                  min="0.01"
                  placeholder="0.00"
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Category <span className="text-red-600">*</span>
              </label>
              <select
                name="category"
                value={formData.category}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                required
              >
                {categories.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description <span className="text-red-600">*</span>
            </label>
            <div className="relative">
              <FileText className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                rows="3"
                placeholder="Describe this recurring expense..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                required
              />
            </div>
          </div>

          {/* Frequency */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Frequency <span className="text-red-600">*</span>
            </label>
            <div className="relative">
              <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <select
                name="frequency"
                value={formData.frequency}
                onChange={handleChange}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                required
              >
                {frequencies.map((freq) => (
                  <option key={freq.value} value={freq.value}>
                    {freq.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Start and End Date */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Start Date <span className="text-red-600">*</span>
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleChange}
                  disabled={isEditing}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                  required
                />
              </div>
              {isEditing && (
                <p className="text-xs text-gray-500 mt-1">
                  Start date cannot be changed
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                End Date <span className="text-gray-500">(Optional)</span>
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleChange}
                  min={formData.start_date}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Leave blank for no end date
              </p>
            </div>
          </div>

          {/* Auto-submit Toggle */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <label className="flex items-center justify-between cursor-pointer">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-indigo-600" />
                <div>
                  <p className="font-medium text-gray-900">
                    Auto-submit expenses
                  </p>
                  <p className="text-sm text-gray-600">
                    {formData.auto_submit
                      ? "Expenses will be created and sent for approval automatically on each cycle. Best for fixed costs like subscriptions and rent."
                      : "You'll get a reminder notification on each cycle, but need to submit the expense manually. Best for variable amounts like team lunches or travel."}
                  </p>
                </div>
              </div>
              <input
                type="checkbox"
                name="auto_submit"
                checked={formData.auto_submit}
                onChange={handleChange}
                className="w-5 h-5 text-indigo-600 rounded focus:ring-2 focus:ring-indigo-500"
              />
            </label>
            {!formData.auto_submit && (
              <p className="text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded px-3 py-2 mt-2">
                When disabled, you'll receive reminders but expenses won't be
                submitted automatically
              </p>
            )}
          </div>

          {/* Intent Mandate Selector */}
          {mandates.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Link to Intent Mandate{" "}
                <span className="text-gray-500">(Optional)</span>
              </label>
              <select
                name="intent_mandate_id"
                value={formData.intent_mandate_id}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                <option value="">No Intent Mandate</option>
                {mandates.map((mandate) => (
                  <option key={mandate.id} value={mandate.id}>
                    {mandate.id} - Max $
                    {mandate.constraints?.max_amount || "unlimited"}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Link to an Intent Mandate for automatic approval
              </p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onCancel}
              className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-5 h-5" />
              {loading ? "Saving..." : isEditing ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RecurringExpenseForm;
