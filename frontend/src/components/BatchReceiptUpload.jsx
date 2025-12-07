import React, { useState, useRef } from "react";
import {
  Upload,
  X,
  Check,
  AlertCircle,
  Edit2,
  Save,
  Loader,
} from "lucide-react";
import { useToast } from "../hooks/useToast";

const BatchReceiptUpload = ({ onSuccess, onCancel }) => {
  const { success: showSuccess, error: showError } = useToast();
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [extractedData, setExtractedData] = useState([]);
  const [editingIndex, setEditingIndex] = useState(null);
  const [editData, setEditData] = useState({});
  const [creating, setCreating] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();

    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    handleFiles(selectedFiles);
  };

  const handleFiles = (newFiles) => {
    // Validate file types
    const validTypes = [
      "image/jpeg",
      "image/jpg",
      "image/png",
      "image/gif",
      "image/bmp",
      "image/webp",
      "application/pdf",
    ];
    const validFiles = newFiles.filter((file) => {
      if (!validTypes.includes(file.type)) {
        showError(`Invalid file type: ${file.name}`);
        return false;
      }
      if (file.size > 10 * 1024 * 1024) {
        showError(`File too large: ${file.name} (max 10MB)`);
        return false;
      }
      return true;
    });

    if (files.length + validFiles.length > 10) {
      showError("Maximum 10 files per batch");
      return;
    }

    setFiles([...files, ...validFiles]);
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
    setExtractedData(extractedData.filter((_, i) => i !== index));
  };

  const handleUploadAndExtract = async () => {
    if (files.length === 0) {
      showError("Please select at least one file");
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });

      const token = localStorage.getItem("token");
      const response = await fetch("/api/v1/receipts/batch-upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      const data = await response.json();

      // Process results
      const extracted = data.results.map((result, index) => ({
        originalFile: files[index].name,
        tempFilename: result.temp_filename,
        contentType: result.content_type,
        success: result.success,
        error: result.error,
        extractedData: result.extracted_data || {},
        vendor: result.extracted_data?.vendor || "",
        amount: result.extracted_data?.amount || "",
        category: result.extracted_data?.category || "Other",
        description: result.extracted_data?.description || "",
        confidence: result.extracted_data?.confidence || 0,
      }));

      setExtractedData(extracted);
      showSuccess(
        `Extracted data from ${extracted.filter((e) => e.success).length}/${files.length} receipts`,
      );
    } catch (err) {
      showError(err.message || "Failed to upload and extract receipts");
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  const handleEdit = (index) => {
    setEditingIndex(index);
    setEditData(extractedData[index]);
  };

  const handleSaveEdit = () => {
    const updated = [...extractedData];
    updated[editingIndex] = editData;
    setExtractedData(updated);
    setEditingIndex(null);
    setEditData({});
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditData({});
  };

  const handleCreateExpense = async (index) => {
    const item = extractedData[index];

    if (!item.vendor || !item.amount) {
      showError("Vendor and amount are required");
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/api/v1/receipts/create-from-extraction", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          vendor: item.vendor,
          amount: parseFloat(item.amount),
          category: item.category,
          description: item.description,
          temp_filename: item.tempFilename,
          original_filename: item.originalFile,
          content_type: item.contentType,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create expense");
      }

      const data = await response.json();

      // Mark as created
      const updated = [...extractedData];
      updated[index].created = true;
      updated[index].expenseId = data.expense.id;
      setExtractedData(updated);

      showSuccess(`Expense created: ${item.vendor}`);
    } catch (err) {
      showError(err.message || "Failed to create expense");
      console.error(err);
    }
  };

  const handleCreateAll = async () => {
    setCreating(true);
    let successCount = 0;

    for (let i = 0; i < extractedData.length; i++) {
      const item = extractedData[i];
      if (item.success && !item.created) {
        try {
          await handleCreateExpense(i);
          successCount++;
        } catch (err) {
          console.error(`Failed to create expense ${i}:`, err);
        }
      }
    }

    setCreating(false);

    if (successCount > 0) {
      showSuccess(`Created ${successCount} expenses successfully`);

      // Call onSuccess after a short delay to show the success message
      setTimeout(() => {
        onSuccess();
      }, 1500);
    }
  };

  const categories = [
    "Travel",
    "Meals",
    "Software",
    "Office Supplies",
    "Other",
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="inline-flex items-center justify-center w-10 h-10 bg-teal-100 rounded-full">
              <Upload className="w-6 h-6 text-teal-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">
              Batch Receipt Upload
            </h2>
          </div>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Upload Area */}
          {extractedData.length === 0 && (
            <div>
              <div
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-teal-400 hover:bg-teal-50 transition-colors cursor-pointer"
              >
                <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-700 mb-2">
                  Drop receipt images here or click to browse
                </p>
                <p className="text-sm text-gray-500">
                  Supports JPG, PNG, GIF, PDF (max 10MB per file, up to 10
                  files)
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/jpeg,image/jpg,image/png,image/gif,image/bmp,image/webp,application/pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>

              {/* Selected Files */}
              {files.length > 0 && (
                <div className="mt-4 space-y-2">
                  <h3 className="font-medium text-gray-900">
                    Selected Files ({files.length})
                  </h3>
                  <div className="space-y-2">
                    {files.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between bg-gray-50 rounded-lg p-3"
                      >
                        <div className="flex items-center gap-3">
                          <Check className="w-5 h-5 text-green-600" />
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              {file.name}
                            </p>
                            <p className="text-xs text-gray-500">
                              {(file.size / 1024).toFixed(1)} KB
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => removeFile(index)}
                          className="p-1 hover:bg-gray-200 rounded transition-colors"
                        >
                          <X className="w-4 h-4 text-gray-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Upload Button */}
              {files.length > 0 && (
                <div className="flex justify-end mt-4">
                  <button
                    onClick={handleUploadAndExtract}
                    disabled={uploading}
                    className="flex items-center gap-2 px-6 py-3 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {uploading ? (
                      <>
                        <Loader className="w-5 h-5 animate-spin" />
                        Extracting Data...
                      </>
                    ) : (
                      <>
                        <Upload className="w-5 h-5" />
                        Upload & Extract Data
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Extracted Data Review */}
          {extractedData.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  Review Extracted Data (
                  {extractedData.filter((e) => !e.created).length} pending)
                </h3>
                <button
                  onClick={handleCreateAll}
                  disabled={
                    creating ||
                    extractedData.every((e) => e.created || !e.success)
                  }
                  className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creating ? (
                    <>
                      <Loader className="w-5 h-5 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Save className="w-5 h-5" />
                      Create All Expenses
                    </>
                  )}
                </button>
              </div>

              {extractedData.map((item, index) => (
                <div
                  key={index}
                  className={`border rounded-lg p-4 ${
                    item.created
                      ? "bg-green-50 border-green-200"
                      : item.success
                        ? "bg-white"
                        : "bg-red-50 border-red-200"
                  }`}
                >
                  {!item.success ? (
                    <div className="flex items-center gap-3">
                      <AlertCircle className="w-5 h-5 text-red-600" />
                      <div>
                        <p className="font-medium text-gray-900">
                          {item.originalFile}
                        </p>
                        <p className="text-sm text-red-600">{item.error}</p>
                      </div>
                    </div>
                  ) : editingIndex === index ? (
                    // Edit Mode
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Vendor *
                          </label>
                          <input
                            type="text"
                            value={editData.vendor || ""}
                            onChange={(e) =>
                              setEditData({
                                ...editData,
                                vendor: e.target.value,
                              })
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Amount *
                          </label>
                          <input
                            type="number"
                            step="0.01"
                            value={editData.amount || ""}
                            onChange={(e) =>
                              setEditData({
                                ...editData,
                                amount: e.target.value,
                              })
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Category
                        </label>
                        <select
                          value={editData.category || "Other"}
                          onChange={(e) =>
                            setEditData({
                              ...editData,
                              category: e.target.value,
                            })
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        >
                          {categories.map((cat) => (
                            <option key={cat} value={cat}>
                              {cat}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Description
                        </label>
                        <textarea
                          value={editData.description || ""}
                          onChange={(e) =>
                            setEditData({
                              ...editData,
                              description: e.target.value,
                            })
                          }
                          rows="2"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        />
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleSaveEdit}
                          className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors"
                        >
                          <Save className="w-4 h-4" />
                          Save
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    // View Mode
                    <div>
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-semibold text-gray-900">
                              {item.originalFile}
                            </h4>
                            {item.created && (
                              <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                                Created
                              </span>
                            )}
                            {item.confidence > 0 && (
                              <span
                                className={`px-2 py-1 text-xs rounded ${
                                  item.confidence >= 0.8
                                    ? "bg-green-100 text-green-800"
                                    : item.confidence >= 0.6
                                      ? "bg-yellow-100 text-yellow-800"
                                      : "bg-red-100 text-red-800"
                                }`}
                              >
                                {Math.round(item.confidence * 100)}% confidence
                              </span>
                            )}
                          </div>
                        </div>

                        {!item.created && (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleEdit(index)}
                              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                              title="Edit"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleCreateExpense(index)}
                              className="flex items-center gap-1 px-3 py-1 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700 transition-colors"
                            >
                              <Check className="w-4 h-4" />
                              Create
                            </button>
                          </div>
                        )}
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">Vendor</p>
                          <p className="font-medium text-gray-900">
                            {item.vendor || "N/A"}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Amount</p>
                          <p className="font-medium text-gray-900">
                            $
                            {item.amount
                              ? parseFloat(item.amount).toFixed(2)
                              : "0.00"}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Category</p>
                          <p className="font-medium text-gray-900">
                            {item.category}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Description</p>
                          <p className="font-medium text-gray-900 truncate">
                            {item.description || "N/A"}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t px-6 py-4 flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default BatchReceiptUpload;
