import React, { useState } from 'react';
import { Download, FileText, Table } from 'lucide-react';
import { expenseAPI } from '../services/api';
import { useToast } from '../hooks/useToast';
import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import 'jspdf-autotable';

const ExpenseExport = ({ expenses, onClose }) => {
  const { success, error: showError } = useToast();
  const [exporting, setExporting] = useState(false);
  const [format, setFormat] = useState('excel');

  const handleExport = async () => {
    setExporting(true);

    try {
      if (format === 'excel') {
        exportExcel();
      } else if (format === 'csv') {
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

  const exportExcel = () => {
    // Prepare data for Excel
    const data = expenses.map((expense, index) => ({
      '#': index + 1,
      'Date': formatDate(expense.date),
      'Category': expense.category || '',
      'Vendor': expense.vendor || '',
      'Description': expense.description || '',
      'Amount': expense.amount,
      'Status': expense.status ? expense.status.charAt(0).toUpperCase() + expense.status.slice(1) : '',
      'Expense ID': expense.id.substring(0, 8) // Short ID for reference
    }));

    // Create worksheet
    const worksheet = XLSX.utils.json_to_sheet(data);

    // Auto-fit column widths
    const columnWidths = [
      { wch: 5 },   // # (row number)
      { wch: 12 },  // Date
      { wch: 15 },  // Category
      { wch: 25 },  // Vendor
      { wch: 40 },  // Description
      { wch: 12 },  // Amount
      { wch: 10 },  // Status
      { wch: 10 }   // Expense ID (shortened)
    ];
    worksheet['!cols'] = columnWidths;

    // Format amount column as currency
    const range = XLSX.utils.decode_range(worksheet['!ref']);
    for (let row = range.s.r + 1; row <= range.e.r; row++) {
      const cellAddress = XLSX.utils.encode_cell({ r: row, c: 5 }); // Column F (Amount - 0-indexed, so position 5)
      if (worksheet[cellAddress]) {
        worksheet[cellAddress].z = '$#,##0.00';
      }
    }

    // Create workbook and add worksheet
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Expenses');

    // Generate filename with current date
    const filename = `expenses_${new Date().toISOString().split('T')[0]}.xlsx`;

    // Save file
    XLSX.writeFile(workbook, filename);
  };

  const exportCSV = () => {
    // Helper function to properly escape CSV cells
    const escapeCSVCell = (cell) => {
      if (cell === null || cell === undefined) return '';
      const str = String(cell);
      // Only quote if the cell contains comma, quote, or newline
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };

    // Create CSV content with proper headers
    const headers = ['#', 'Date', 'Category', 'Vendor', 'Description', 'Amount', 'Status', 'Expense ID'];
    const rows = expenses.map((expense, index) => [
      index + 1,
      formatDate(expense.date),
      expense.category || '',
      expense.vendor || '',
      expense.description || '',
      expense.amount.toFixed(2),
      expense.status || '',
      expense.id.substring(0, 8)
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(escapeCSVCell).join(','))
    ].join('\n');

    // Create download with BOM for Excel compatibility
    const BOM = '\uFEFF';
    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
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
    // Create new PDF document (A4 size, portrait orientation)
    const doc = new jsPDF();

    // Add header
    doc.setFontSize(20);
    doc.setTextColor(79, 70, 229); // Indigo color
    doc.text('Expense Report', 105, 20, { align: 'center' });

    // Add generation info
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 35);
    doc.text(`Total Expenses: ${expenses.length}`, 14, 41);
    doc.text(`Total Amount: $${expenses.reduce((sum, e) => sum + e.amount, 0).toFixed(2)}`, 14, 47);

    // Calculate summary stats
    const pending = expenses.filter(e => e.status === 'pending').length;
    const approved = expenses.filter(e => e.status === 'approved').length;
    const rejected = expenses.filter(e => e.status === 'rejected').length;

    doc.text(`Pending: ${pending} | Approved: ${approved} | Rejected: ${rejected}`, 14, 53);

    // Prepare table data
    const tableData = expenses.map((expense, index) => [
      index + 1,
      formatDate(expense.date),
      expense.category || '',
      expense.vendor || '',
      expense.description || '',
      `$${expense.amount.toFixed(2)}`,
      (expense.status || '').toUpperCase()
    ]);

    // Add table with autoTable
    doc.autoTable({
      head: [['#', 'Date', 'Category', 'Vendor', 'Description', 'Amount', 'Status']],
      body: tableData,
      startY: 60,
      theme: 'striped',
      headStyles: {
        fillColor: [79, 70, 229], // Indigo
        textColor: 255,
        fontStyle: 'bold',
        halign: 'left'
      },
      styles: {
        fontSize: 9,
        cellPadding: 3,
        overflow: 'linebreak',
        halign: 'left'
      },
      columnStyles: {
        0: { cellWidth: 10, halign: 'center' },  // #
        1: { cellWidth: 22 },                     // Date
        2: { cellWidth: 22 },                     // Category
        3: { cellWidth: 30 },                     // Vendor
        4: { cellWidth: 50 },                     // Description
        5: { cellWidth: 22, halign: 'right' },    // Amount
        6: { cellWidth: 22, halign: 'center' }    // Status
      },
      didParseCell: function(data) {
        // Color code status cells
        if (data.column.index === 6 && data.section === 'body') {
          const status = data.cell.raw.toLowerCase();
          if (status === 'pending') {
            data.cell.styles.textColor = [245, 158, 11]; // Yellow
            data.cell.styles.fontStyle = 'bold';
          } else if (status === 'approved') {
            data.cell.styles.textColor = [16, 185, 129]; // Green
            data.cell.styles.fontStyle = 'bold';
          } else if (status === 'rejected') {
            data.cell.styles.textColor = [239, 68, 68]; // Red
            data.cell.styles.fontStyle = 'bold';
          }
        }
      },
      margin: { top: 60, left: 14, right: 14 }
    });

    // Add footer
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(150);
      doc.text(
        'AP2 Expense Management System',
        105,
        doc.internal.pageSize.height - 15,
        { align: 'center' }
      );
      doc.text(
        `Page ${i} of ${pageCount}`,
        105,
        doc.internal.pageSize.height - 10,
        { align: 'center' }
      );
    }

    // Save the PDF
    const filename = `expenses_${new Date().toISOString().split('T')[0]}.pdf`;
    doc.save(filename);
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
                ${expenses.reduce((sum, e) => sum + e.amount, 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
          <label className="flex items-center gap-3 p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors border-indigo-500">
            <input
              type="radio"
              name="format"
              value="excel"
              checked={format === 'excel'}
              onChange={(e) => setFormat(e.target.value)}
              className="w-4 h-4 text-indigo-600"
            />
            <Table className="w-8 h-8 text-green-600" />
            <div className="flex-1">
              <div className="font-medium text-gray-800">Excel (.xlsx)</div>
              <div className="text-xs text-gray-600">Properly formatted with auto-fit columns - Recommended</div>
            </div>
          </label>

          <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <input
              type="radio"
              name="format"
              value="csv"
              checked={format === 'csv'}
              onChange={(e) => setFormat(e.target.value)}
              className="w-4 h-4 text-indigo-600"
            />
            <Table className="w-8 h-8 text-blue-600" />
            <div className="flex-1">
              <div className="font-medium text-gray-800">CSV (Plain Text)</div>
              <div className="text-xs text-gray-600">Simple format for Excel or Google Sheets</div>
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
              <div className="text-xs text-gray-600">Professional report with color-coded status</div>
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
