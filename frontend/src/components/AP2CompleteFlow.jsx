import React, { useState } from "react";
import {
  Zap,
  Plus,
  Trash2,
  AlertCircle,
  DollarSign,
  Package,
} from "lucide-react";
import { useToast } from "../hooks/useToast";

const AP2CompleteFlow = ({ mandates, onRefresh }) => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          One-time Authorization
        </h2>
        <p className="text-gray-600">
          Execute one-time purchases with automatic authorization and payment
        </p>
      </div>

      {/* Complete Flow Form */}
      <CompleteFlowForm mandates={mandates} onRefresh={onRefresh} />
    </div>
  );
};

// Complete Flow Form (All 3 steps at once)
const CompleteFlowForm = ({ mandates, onRefresh }) => {
  const { success, error: showError } = useToast();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([
    { description: "", amount: "", category: "OFFICE_SUPPLIES" },
  ]);
  const [merchant, setMerchant] = useState("");

  const addItem = () => {
    setItems([
      ...items,
      { description: "", amount: "", category: "OFFICE_SUPPLIES" },
    ]);
  };

  const removeItem = (index) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const updateItem = (index, field, value) => {
    const newItems = [...items];
    newItems[index][field] = value;
    setItems(newItems);
  };

  const calculateTotal = () => {
    return items.reduce(
      (sum, item) => sum + (parseFloat(item.amount) || 0),
      0,
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Validate items
      const validItems = items.filter(
        (item) => item.description && item.amount,
      );
      if (validItems.length === 0) {
        showError("Please add at least one item");
        return;
      }

      // Auto-derive constraints from items for one-time authorization
      const total = validItems.reduce((sum, item) => sum + parseFloat(item.amount), 0);
      const primaryCategory = validItems[0].category;
      const maxAmount = Math.ceil(total * 1.05 * 100) / 100; // total + 5% buffer

      const requestData = {
        items: validItems.map((item) => ({
          description: item.description,
          amount: parseFloat(item.amount),
          category: item.category,
        })),
        merchant: merchant,
        constraints: {
          max_amount: maxAmount,
          monthly_limit: maxAmount,
          category: primaryCategory,
          merchant: merchant,
        },
      };

      const response = await fetch("/api/ap2/complete-flow", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to complete AP2 flow");
      }

      const data = await response.json().catch(() => ({}));
      success(
        `AP2 flow completed! Total: $${calculateTotal().toFixed(2)}`,
      );

      // Reset form and refresh data
      setItems([{ description: "", amount: "", category: "OFFICE_SUPPLIES" }]);
      setMerchant("");
      if (onRefresh) onRefresh();
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Info Box */}
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <div className="flex items-start">
          <Zap className="w-5 h-5 text-purple-600 mt-0.5 mr-3 flex-shrink-0" />
          <div className="text-sm text-purple-900">
            <p className="font-medium mb-1">Quick One-time Authorization</p>
            <p>
              This flow creates a temporary authorization and executes the complete AP2 protocol in one transaction.
              Perfect for one-time purchases where you don't need ongoing approval automation.
            </p>
            <p className="mt-2">
              <strong>How it works:</strong> Creates Intent → Cart → Payment mandates and executes payment automatically.
            </p>
            <p className="mt-2 text-xs">
              💡 <strong>Tip:</strong> For recurring purchases (monthly software, regular expenses), use the "Reusable Authorizations" tab instead to set up standing permissions.
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Package className="w-5 h-5 mr-2 text-purple-600" />
          Items
        </h3>

        <div className="space-y-4">
          {items.map((item, index) => (
            <div key={index} className="flex gap-4 items-start">
              <div className="flex-1 grid grid-cols-3 gap-4">
                <input
                  type="text"
                  placeholder="Description"
                  value={item.description}
                  onChange={(e) =>
                    updateItem(index, "description", e.target.value)
                  }
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                  required
                />
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={item.amount}
                    onChange={(e) => updateItem(index, "amount", e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                    required
                  />
                </div>
                <select
                  value={item.category}
                  onChange={(e) =>
                    updateItem(index, "category", e.target.value)
                  }
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                >
                  <option value="OFFICE_SUPPLIES">Office Supplies</option>
                  <option value="SOFTWARE">Software</option>
                  <option value="TRAVEL">Travel</option>
                  <option value="MEALS">Meals</option>
                  <option value="COFFEE">Coffee</option>
                  <option value="ENTERTAINMENT">Entertainment</option>
                  <option value="UTILITIES">Utilities</option>
                  <option value="MARKETING">Marketing</option>
                  <option value="HARDWARE">Hardware</option>
                  <option value="PROFESSIONAL_SERVICES">Professional Services</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
              {items.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeItem(index)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              )}
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={addItem}
          className="mt-4 text-purple-600 hover:text-purple-700 font-medium flex items-center"
        >
          <Plus className="w-4 h-4 mr-1" />
          Add Item
        </button>

        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex justify-between text-lg font-semibold">
            <span>Total:</span>
            <span className="text-purple-600">
              ${calculateTotal().toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Merchant */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Merchant
        </h3>
        <input
          type="text"
          value={merchant}
          onChange={(e) => setMerchant(e.target.value)}
          placeholder="e.g., Amazon, Uber, Staples"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
          required
        />
        <p className="mt-2 text-sm text-gray-500">
          Authorization limit is automatically set to your item total + 5% buffer.
        </p>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-purple-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
      >
        {loading ? (
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
        ) : (
          <>
            <Zap className="w-5 h-5 mr-2" />
            Execute One-time Authorization
          </>
        )}
      </button>

      {/* Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
          <div className="text-sm text-blue-900">
            <p className="font-medium mb-1">Complete Flow executes all 4 AP2 steps automatically:</p>
            <ol className="list-decimal ml-4 space-y-1">
              <li>Creates Intent Mandate with your constraints</li>
              <li>Creates Cart Mandate with items</li>
              <li>Creates Payment Mandate</li>
              <li>Executes payment (if Stripe configured)</li>
            </ol>
            <p className="mt-2 text-xs">
              <strong>When to use:</strong> Perfect for quick one-time authorizations where you trust the AI agent to make purchases within your specified constraints without manual approval.
            </p>
          </div>
        </div>
      </div>
    </form>
  );
};

export default AP2CompleteFlow;
