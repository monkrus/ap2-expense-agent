/**
 * Receipts API Service
 * Handles receipt upload, OCR, and management
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/**
 * Get authentication headers
 */
const getAuthHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    Authorization: `Bearer ${token}`,
  };
};

/**
 * Get authentication headers for multipart form data
 */
const getMultipartAuthHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    Authorization: `Bearer ${token}`,
    // Don't set Content-Type for multipart/form-data - browser will set it with boundary
  };
};

// ============================================================================
// Receipt Management
// ============================================================================

/**
 * Upload a receipt file
 * @param {File} file - The receipt image file (JPG, PNG, PDF)
 * @param {string} expenseId - Optional expense ID to attach to
 * @returns {Promise<Object>} Receipt object with ID
 */
export const uploadReceipt = async (file, expenseId = null) => {
  const formData = new FormData();
  formData.append("file", file);
  if (expenseId) {
    formData.append("expense_id", expenseId);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/receipts/upload`, {
    method: "POST",
    headers: getMultipartAuthHeaders(),
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to upload receipt");
  }

  return response.json();
};

/**
 * Get receipt details
 * @param {string} receiptId - Receipt ID
 * @returns {Promise<Object>} Receipt details
 */
export const getReceipt = async (receiptId) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/receipts/${receiptId}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch receipt");
  }

  return response.json();
};

/**
 * Delete a receipt
 * @param {string} receiptId - Receipt ID
 * @returns {Promise<boolean>}
 */
export const deleteReceipt = async (receiptId) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/receipts/${receiptId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete receipt");
  }

  return true;
};

/**
 * Trigger OCR on a receipt
 * @param {string} receiptId - Receipt ID
 * @returns {Promise<Object>} OCR extracted data
 */
export const triggerOCR = async (receiptId) => {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/receipts/${receiptId}/ocr`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to process receipt with OCR");
  }

  return response.json();
};

/**
 * Upload receipt and automatically trigger OCR
 * @param {File} file - Receipt file
 * @param {string} expenseId - Optional expense ID
 * @returns {Promise<Object>} Receipt with OCR data
 */
export const uploadAndProcessReceipt = async (file, expenseId = null) => {
  try {
    // Step 1: Upload receipt
    const receipt = await uploadReceipt(file, expenseId);

    // Step 2: Trigger OCR
    const ocrResult = await triggerOCR(receipt.id);

    return {
      receipt,
      ocrData: ocrResult,
    };
  } catch (error) {
    throw new Error(`Failed to upload and process receipt: ${error.message}`);
  }
};

export default {
  uploadReceipt,
  getReceipt,
  deleteReceipt,
  triggerOCR,
  uploadAndProcessReceipt,
};
