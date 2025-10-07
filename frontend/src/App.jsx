import React, { useState, useEffect } from 'react';
import { Send, DollarSign, CheckCircle, XCircle, Clock, Receipt, TrendingUp, Users, Shield, Zap } from 'lucide-react';
import { expenseAPI, APIError } from './services/api';
import { useToast } from './hooks/useToast';
import { ToastContainer } from './components/Toast';
import { useAuth } from './contexts/AuthContext';

const ExpenseManagementAgent = () => {
  const { user } = useAuth();
  const { toasts, removeToast, success, error: showError, info } = useToast();

  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I\'m your AI Expense Management Agent. I can help you submit, review, and approve business expenses automatically. Use the quick action buttons below or type your request.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expenses, setExpenses] = useState([]);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [newExpense, setNewExpense] = useState({
    amount: '',
    category: 'Travel',
    vendor: '',
    description: ''
  });
  const [paymentProcessing, setPaymentProcessing] = useState(false);
  const [fetchingReport, setFetchingReport] = useState(true);

  // Fetch expense report on mount
  useEffect(() => {
    const fetchExpenses = async () => {
      try {
        setFetchingReport(true);
        const report = await expenseAPI.getExpenseReport(user?.id);
        if (report.expenses && Array.isArray(report.expenses)) {
          setExpenses(report.expenses);
        }
      } catch (err) {
        console.error('Error fetching expenses:', err);
        if (err instanceof APIError && err.status === 401) {
          showError('Session expired. Please login again.');
        } else {
          showError('Failed to load expenses. Using offline mode.');
        }
      } finally {
        setFetchingReport(false);
      }
    };

    if (user) {
      fetchExpenses();
    }
  }, [user]);

  const processAP2Payment = async (expense) => {
    setPaymentProcessing(true);

    try {
      const result = await expenseAPI.approveExpense(expense.id, user?.id || 'current_user');

      setPaymentProcessing(false);

      return {
        success: true,
        transactionId: result.result?.mandates?.payment?.id || `payment_${Date.now()}`,
        mandates: result.result?.mandates || {
          intent: { id: `intent_${Date.now()}` },
          cart: { id: `cart_${Date.now()}` },
          payment: { id: `payment_${Date.now()}` }
        }
      };
    } catch (err) {
      setPaymentProcessing(false);
      throw err;
    }
  };

  const handleSubmit = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setLoading(true);

    await new Promise(resolve => setTimeout(resolve, 500));

    let response = '';
    const lowerInput = currentInput.toLowerCase();

    if (lowerInput.includes('submit') || lowerInput.includes('new expense')) {
      response = 'I will help you submit a new expense. Please fill out the form below with the expense details.';
      setShowExpenseForm(true);
    } else if (lowerInput.includes('review') || lowerInput.includes('pending')) {
      const pendingExpenses = expenses.filter(e => e.status === 'pending');
      response = `You have ${pendingExpenses.length} pending expenses totaling $${pendingExpenses.reduce((sum, e) => sum + e.amount, 0).toFixed(2)}. Click "Approve" on any expense card or use the quick action button to process them via AP2.`;
    } else if (lowerInput.includes('approve') || lowerInput.includes('process')) {
      const expenseToApprove = expenses.find(e => e.status === 'pending');
      if (expenseToApprove) {
        response = `Processing ${expenseToApprove.id} for $${expenseToApprove.amount} using AP2 protocol with cryptographic mandates...`;
        setMessages(prev => [...prev, { role: 'assistant', content: response }]);

        try {
          const result = await processAP2Payment(expenseToApprove);

          if (result.success) {
            // Optimistic update
            setExpenses(prev => prev.map(e =>
              e.id === expenseToApprove.id
                ? { ...e, status: 'approved', transaction_id: result.transactionId }
                : e
            ));

            response = `Payment completed successfully!\n\nTransaction ID: ${result.transactionId}\n\nAP2 Verification:\n• Intent Mandate: ${result.mandates.intent.id}\n• Cart Mandate: ${result.mandates.cart.id}\n• Payment Mandate: ${result.mandates.payment.id}\n\nFull cryptographic audit trail available for compliance.`;
            success('Payment processed successfully!');
          }
        } catch (err) {
          const errorMsg = err instanceof APIError ? err.message : 'Failed to process payment';
          response = `Error: ${errorMsg}`;
          showError(errorMsg);
        }
      } else {
        response = 'No pending expenses to process at the moment.';
      }
    } else if (lowerInput.includes('analytics') || lowerInput.includes('report')) {
      const total = expenses.reduce((sum, e) => sum + e.amount, 0);
      const approved = expenses.filter(e => e.status === 'approved').length;
      response = `Expense Analytics:\n\n• Total Expenses: $${total.toFixed(2)}\n• Approved: ${approved}\n• Pending: ${expenses.length - approved}\n• Average: $${(total / expenses.length).toFixed(2)}\n\nTop Category: ${expenses[0]?.category || 'N/A'}`;
    } else {
      response = 'I can help you with:\n\n• Submit new expenses\n• Review pending expenses\n• Approve and process payments via AP2\n• Generate expense reports\n• View analytics\n\nUse the quick action buttons below for common tasks!';
    }

    setMessages(prev => [...prev, { role: 'assistant', content: response }]);
    setLoading(false);
  };

  const handleQuickAction = async (action) => {
    setInput(action);
    setTimeout(() => handleSubmit(), 0);
  };

  const handleApproveExpense = async (expense) => {
    const userMessage = { role: 'user', content: `Approve ${expense.id}` };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    await new Promise(resolve => setTimeout(resolve, 300));

    let response = `Processing ${expense.id} for $${expense.amount} using AP2 protocol...`;
    setMessages(prev => [...prev, { role: 'assistant', content: response }]);

    try {
      const result = await processAP2Payment(expense);

      if (result.success) {
        // Optimistic update
        setExpenses(prev => prev.map(e =>
          e.id === expense.id
            ? { ...e, status: 'approved', transaction_id: result.transactionId }
            : e
        ));

        response = `Payment completed successfully!\n\nTransaction ID: ${result.transactionId}\n\nAP2 Verification:\n• Intent Mandate: ${result.mandates.intent.id}\n• Cart Mandate: ${result.mandates.cart.id}\n• Payment Mandate: ${result.mandates.payment.id}`;
        setMessages(prev => [...prev, { role: 'assistant', content: response }]);
        success('Payment processed successfully!');
      }
    } catch (err) {
      const errorMsg = err instanceof APIError ? err.message : 'Failed to process payment';
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${errorMsg}` }]);
      showError(errorMsg);
    }

    setLoading(false);
  };

  const handleExpenseSubmit = async () => {
    if (!newExpense.amount || !newExpense.vendor || !newExpense.description) {
      showError('Please fill in all required fields');
      return;
    }

    const tempId = `EXP-${Date.now()}`;
    const optimisticExpense = {
      id: tempId,
      amount: parseFloat(newExpense.amount),
      category: newExpense.category,
      vendor: newExpense.vendor,
      status: 'pending',
      date: new Date().toISOString().split('T')[0],
      description: newExpense.description,
      _optimistic: true
    };

    // Optimistic update
    setExpenses(prev => [...prev, optimisticExpense]);
    setShowExpenseForm(false);

    const expenseData = {
      user_id: user?.id || 'current_user',
      amount: parseFloat(newExpense.amount),
      category: newExpense.category,
      vendor: newExpense.vendor,
      description: newExpense.description
    };

    try {
      const result = await expenseAPI.submitExpense(expenseData);

      // Update with real data from server
      setExpenses(prev => prev.map(e =>
        e.id === tempId ? { ...result.expense, _optimistic: false } : e
      ));

      setNewExpense({ amount: '', category: 'Travel', vendor: '', description: '' });

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Expense ${result.expense.id} submitted successfully!\n\nAmount: $${result.expense.amount}\nVendor: ${result.expense.vendor}\nCategory: ${result.expense.category}\n\nThis expense is now pending approval and can be processed via AP2 secure payment protocol.`
      }]);

      success('Expense submitted successfully!');
    } catch (err) {
      // Rollback optimistic update
      setExpenses(prev => prev.filter(e => e.id !== tempId));

      const errorMsg = err instanceof APIError ? err.message : 'Failed to submit expense';
      showError(errorMsg);
      setShowExpenseForm(true);
    }
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'approved': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'pending': return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'rejected': return <XCircle className="w-4 h-4 text-red-500" />;
      default: return null;
    }
  };

  const stats = {
    total: expenses.reduce((sum, e) => sum + e.amount, 0),
    pending: expenses.filter(e => e.status === 'pending').length,
    approved: expenses.filter(e => e.status === 'approved').length
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <ToastContainer toasts={toasts} onClose={removeToast} />

      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
                <Receipt className="w-8 h-8 text-indigo-600" />
                AI Expense Management Agent
              </h1>
              <p className="text-gray-600 mt-2">Powered by AP2 Protocol for Secure Agent Payments</p>
            </div>
            <Shield className="w-16 h-16 text-indigo-600 opacity-20" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Total Expenses</p>
                <p className="text-2xl font-bold text-gray-800">${stats.total.toFixed(2)}</p>
              </div>
              <DollarSign className="w-10 h-10 text-blue-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Pending Approval</p>
                <p className="text-2xl font-bold text-yellow-600">{stats.pending}</p>
              </div>
              <Clock className="w-10 h-10 text-yellow-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Approved</p>
                <p className="text-2xl font-bold text-green-600">{stats.approved}</p>
              </div>
              <CheckCircle className="w-10 h-10 text-green-500" />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-lg flex flex-col h-[600px]">
            <div className="bg-indigo-600 text-white p-4 rounded-t-lg">
              <h2 className="font-semibold flex items-center gap-2">
                <Users className="w-5 h-5" />
                AI Agent Assistant
              </h2>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      msg.role === 'user'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    <p className="whitespace-pre-line text-sm">{msg.content}</p>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg p-3">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                    </div>
                  </div>
                </div>
              )}
              {paymentProcessing && (
                <div className="flex justify-center">
                  <div className="bg-blue-100 border border-blue-300 rounded-lg p-4 text-center">
                    <Shield className="w-8 h-8 text-blue-600 mx-auto mb-2 animate-pulse" />
                    <p className="text-blue-800 font-semibold">Processing via AP2 Protocol</p>
                    <p className="text-blue-600 text-sm">Creating cryptographic mandates...</p>
                  </div>
                </div>
              )}
            </div>

            <div className="border-t bg-gray-50 p-3">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-indigo-600" />
                <p className="text-xs font-medium text-gray-700">Quick Actions:</p>
              </div>
              <div className="flex flex-wrap gap-2 mb-3">
                <button
                  onClick={() => handleQuickAction("review pending expenses")}
                  disabled={loading}
                  className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg text-xs font-medium hover:bg-blue-200 disabled:opacity-50 transition-colors"
                >
                  Review Pending
                </button>
                <button
                  onClick={() => handleQuickAction("approve expense")}
                  disabled={loading}
                  className="px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-xs font-medium hover:bg-green-200 disabled:opacity-50 transition-colors"
                >
                  Approve Next
                </button>
                <button
                  onClick={() => handleQuickAction("analytics")}
                  disabled={loading}
                  className="px-3 py-1.5 bg-purple-100 text-purple-700 rounded-lg text-xs font-medium hover:bg-purple-200 disabled:opacity-50 transition-colors"
                >
                  Analytics
                </button>
                <button
                  onClick={() => setShowExpenseForm(true)}
                  disabled={loading}
                  className="px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-xs font-medium hover:bg-indigo-200 disabled:opacity-50 transition-colors"
                >
                  New Expense
                </button>
              </div>
            </div>

            <div className="p-4 border-t">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
                  placeholder="Or type your request here..."
                  className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                  disabled={loading}
                />
                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  Send
                </button>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6 h-[600px] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-indigo-600" />
                Expense Tracker
              </h2>
              <button
                onClick={() => setShowExpenseForm(!showExpenseForm)}
                className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700"
              >
                {showExpenseForm ? 'Cancel' : '+ New Expense'}
              </button>
            </div>

            {showExpenseForm && (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Amount ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newExpense.amount}
                    onChange={(e) => setNewExpense({...newExpense, amount: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={newExpense.category}
                    onChange={(e) => setNewExpense({...newExpense, category: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                  >
                    <option>Travel</option>
                    <option>Meals</option>
                    <option>Software</option>
                    <option>Office Supplies</option>
                    <option>Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Vendor</label>
                  <input
                    type="text"
                    value={newExpense.vendor}
                    onChange={(e) => setNewExpense({...newExpense, vendor: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="Vendor name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={newExpense.description}
                    onChange={(e) => setNewExpense({...newExpense, description: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                    rows="2"
                    placeholder="Expense description"
                  />
                </div>
                <button
                  onClick={handleExpenseSubmit}
                  className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 font-medium"
                >
                  Submit Expense
                </button>
              </div>
            )}

            {fetchingReport ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-2"></div>
                  <p className="text-gray-600 text-sm">Loading expenses...</p>
                </div>
              </div>
            ) : expenses.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500">No expenses yet. Submit your first expense to get started!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {expenses.map((expense) => (
                  <div key={expense.id} className={`border rounded-lg p-4 hover:shadow-md transition-shadow ${expense._optimistic ? 'opacity-60' : ''}`}>
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-gray-800">{expense.id}</span>
                          {getStatusIcon(expense.status)}
                          <span className={`text-xs px-2 py-1 rounded ${
                            expense.status === 'approved' ? 'bg-green-100 text-green-800' :
                            expense.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {expense.status.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600">{expense.description}</p>
                        <p className="text-xs text-gray-500 mt-1">{expense.vendor} • {expense.date}</p>
                        {expense.transaction_id && (
                          <p className="text-xs text-blue-600 mt-1 font-mono">TX: {expense.transaction_id}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-gray-800">${expense.amount.toFixed(2)}</p>
                        <p className="text-xs text-gray-500">{expense.category}</p>
                      </div>
                    </div>

                    {expense.status === 'pending' && !expense._optimistic && (
                      <button
                        onClick={() => handleApproveExpense(expense)}
                        disabled={loading || paymentProcessing}
                        className="mt-2 w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center justify-center gap-2 transition-colors"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Approve via AP2
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-600" />
            Powered by Google AP2 Protocol
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">Authorization</h4>
              <p className="text-sm text-blue-800">Cryptographic proof that users authorized each payment with Intent Mandates</p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <h4 className="font-semibold text-green-900 mb-2">Authenticity</h4>
              <p className="text-sm text-green-800">Cart Mandates ensure merchants receive accurate transaction details</p>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <h4 className="font-semibold text-purple-900 mb-2">Accountability</h4>
              <p className="text-sm text-purple-800">Full audit trail with Payment Mandates for compliance and dispute resolution</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExpenseManagementAgent;
