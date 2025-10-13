import React, { useState } from 'react';
import { Edit2, X, Save } from 'lucide-react';
import { expenseAPI, APIError } from '../services/api';
import { useToast } from '../hooks/useToast';

const ExpenseEdit = ({ expense, onSuccess, onCancel }) => {
  const { success, error: showError } = useToast();
  const [formData, setFormData] = useState({
    amount: expense.amount.toString(),
    category: expense.category,
    vendor: expense.vendor,
    description: expense.description
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!formData.amount || !formData.vendor || !formData.description) {
      showError('Please fill in all required fields');
      return;
    }

    setSaving(true);

    try {
      const updatedData = {
        user_id: expense.user_id,  // Include user_id from original expense
        amount: parseFloat(formData.amount),
        category: formData.category,
        vendor: formData.vendor,
        description: formData.description
      };

      const result = await expenseAPI.updateExpense(expense.id, updatedData);

      success('Expense updated successfully');
      onSuccess(result.expense);
    } catch (err) {
      const errorMsg = err instanceof APIError ? err.message : 'Failed to update expense';
      showError(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <Edit2 className="w-6 h-6 text-indigo-600" />
            Edit Expense
          </h2>
          <button
            onClick={onCancel}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          Editing expense <span className="font-mono font-semibold">{expense.id}</span>
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Amount ($) <span className="text-red-600">*</span>
            </label>
            <input
              type="number"
              step="0.01"
              value={formData.amount}
              onChange={(e) => setFormData({...formData, amount: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
              placeholder="0.00"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select
              value={formData.category}
              onChange={(e) => setFormData({...formData, category: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
              required
            >
              <option>Travel</option>
              <option>Meals</option>
              <option>Software</option>
              <option>Office Supplies</option>
              <option>Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Vendor <span className="text-red-600">*</span>
            </label>
            <input
              type="text"
              value={formData.vendor}
              onChange={(e) => setFormData({...formData, vendor: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
              placeholder="Vendor name"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-red-600">*</span>
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
              rows="3"
              placeholder="Expense description"
              required
            />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onCancel}
            disabled={saving}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExpenseEdit;
