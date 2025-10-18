import React, { useState } from 'react';
import { Download, FileText, Table } from 'lucide-react';
import { expenseAPI } from '../services/api';
import { useToast } from '../hooks/useToast';

const ExpenseExport = ({ expenses, onClose }) => {
  const { success, error: showError } = useToast();
  const [exporting, setExporting] = useState(false);
  const [format, setFormat] = useState('csv');

  const handleExport = async () => {
    setExporting(true);

    try {
      if (format === 'csv') {
        exportCSV();
      } else {
        exportPDF();
      }

      success(`Expenses exported as ${format.toUpperCase()} successfully`);
      setTimeout(() => onClose(), 1000);
    } catch (err) {
      showError(`Failed to export expenses: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const exportCSV = () => {
    // Create CSV content
    const headers = ['ID', 'Date', 'Category', 'Vendor', 'Description', 'Amount', 'Status'];
    const rows = expenses.map(expense => [
      expense.id,
      formatDate(expense.date),
      expense.category,
      expense.vendor,
      expense.description,
      expense.amount.toFixed(2),
      expense.status
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    // Create download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `expenses_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportPDF = () => {
    // Create HTML content for PDF
    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body {
            font-family: Arial, sans-serif;
            padding: 20px;
          }
          h1 {
            color: #4f46e5;
            text-align: center;
            margin-bottom: 30px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
          }
          th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
          }
          th {
            background-color: #4f46e5;
            color: white;
          }
          tr:nth-child(even) {
            background-color: #f9f9f9;
          }
          .status-pending { color: #f59e0b; font-weight: bold; }
          .status-approved { color: #10b981; font-weight: bold; }
          .status-rejected { color: #ef4444; font-weight: bold; }
          .footer {
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 12px;
          }
        </style>
      </head>
      <body>
        <h1>Expense Report</h1>
        <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
        <p><strong>Total Expenses:</strong> ${expenses.length}</p>
        <p><strong>Total Amount:</strong> $${expenses.reduce((sum, e) => sum + e.amount, 0).toFixed(2)}</p>

        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Date</th>
              <th>Category</th>
              <th>Vendor</th>
              <th>Description</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${expenses.map(expense => `
              <tr>
                <td>${expense.id}</td>
                <td>${formatDate(expense.date)}</td>
                <td>${expense.category}</td>
                <td>${expense.vendor}</td>
                <td>${expense.description}</td>
                <td>$${expense.amount.toFixed(2)}</td>
                <td class="status-${expense.status}">${expense.status.toUpperCase()}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>

        <div class="footer">
          <p>AP2 Expense Management System</p>
          <p>This document was generated automatically</p>
        </div>
      </body>
      </html>
    `;

    // Create PDF using print functionality
    const printWindow = window.open('', '', 'width=800,height=600');
    printWindow.document.write(htmlContent);
    printWindow.document.close();

    // Wait for content to load, then print
    printWindow.onload = function() {
      printWindow.print();
      printWindow.onafterprint = function() {
        printWindow.close();
      };
    };
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <Download className="w-6 h-6 text-indigo-600" />
            Export Expenses
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <span className="text-2xl text-gray-600">&times;</span>
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-6">
          Export {expenses.length} expense{expenses.length !== 1 ? 's' : ''} to a file format of your choice.
        </p>

        {/* Summary */}
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-gray-800 mb-2">Export Summary</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-600">Total Expenses:</span>
              <span className="font-semibold ml-2">{expenses.length}</span>
            </div>
            <div>
              <span className="text-gray-600">Total Amount:</span>
              <span className="font-semibold ml-2">
                ${expenses.reduce((sum, e) => sum + e.amount, 0).toFixed(2)}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Pending:</span>
              <span className="font-semibold ml-2 text-yellow-600">
                {expenses.filter(e => e.status === 'pending').length}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Approved:</span>
              <span className="font-semibold ml-2 text-green-600">
                {expenses.filter(e => e.status === 'approved').length}
              </span>
            </div>
          </div>
        </div>

        {/* Format Selection */}
        <div className="space-y-3 mb-6">
          <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <input
              type="radio"
              name="format"
              value="csv"
              checked={format === 'csv'}
              onChange={(e) => setFormat(e.target.value)}
              className="w-4 h-4 text-indigo-600"
            />
            <Table className="w-8 h-8 text-green-600" />
            <div className="flex-1">
              <div className="font-medium text-gray-800">CSV (Excel)</div>
              <div className="text-xs text-gray-600">Open in Excel or Google Sheets</div>
            </div>
          </label>

          <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <input
              type="radio"
              name="format"
              value="pdf"
              checked={format === 'pdf'}
              onChange={(e) => setFormat(e.target.value)}
              className="w-4 h-4 text-indigo-600"
            />
            <FileText className="w-8 h-8 text-red-600" />
            <div className="flex-1">
              <div className="font-medium text-gray-800">PDF Document</div>
              <div className="text-xs text-gray-600">Printable report format</div>
            </div>
          </label>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            disabled={exporting}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {exporting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Exporting...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Export {format.toUpperCase()}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExpenseExport;
