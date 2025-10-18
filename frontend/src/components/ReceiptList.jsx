import React from 'react';
import { FileText, Image as ImageIcon, X, Download } from 'lucide-react';

const ReceiptList = ({ receipts, onClose }) => {
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  const getFileIcon = (contentType) => {
    if (contentType.startsWith('image/')) {
      return <ImageIcon className="w-5 h-5 text-blue-600" />;
    }
    return <FileText className="w-5 h-5 text-red-600" />;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800">
            Receipt Details ({receipts.length})
          </h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Receipt List */}
        <div className="max-h-96 overflow-y-auto">
          {receipts.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-2" />
              <p>No receipts uploaded</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {receipts.map((receipt) => (
                <div
                  key={receipt.id}
                  className="p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    {/* File Icon */}
                    <div className="flex-shrink-0 mt-1">
                      {getFileIcon(receipt.content_type)}
                    </div>

                    {/* File Details */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">
                        {receipt.filename}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-500">
                          {formatFileSize(receipt.file_size)}
                        </span>
                        <span className="text-xs text-gray-400">•</span>
                        <span className="text-xs text-gray-500">
                          {formatDate(receipt.uploaded_at)}
                        </span>
                      </div>
                    </div>

                    {/* Download Button */}
                    <button
                      onClick={async () => {
                        try {
                          const token = localStorage.getItem('access_token');
                          const response = await fetch(`/api/v1/receipts/download/${receipt.id}`, {
                            headers: {
                              'Authorization': `Bearer ${token}`
                            }
                          });

                          if (!response.ok) {
                            throw new Error('Failed to download receipt');
                          }

                          // Get the blob and create download link
                          const blob = await response.blob();
                          const url = window.URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = receipt.filename;
                          document.body.appendChild(a);
                          a.click();
                          window.URL.revokeObjectURL(url);
                          document.body.removeChild(a);
                        } catch (error) {
                          console.error('Download error:', error);
                          alert('Failed to download receipt. Please try again.');
                        }
                      }}
                      className="flex-shrink-0 p-2 text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                      title="Download receipt"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReceiptList;
