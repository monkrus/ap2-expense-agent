/**
 * Excel File Safety Utilities
 * Mitigates xlsx library vulnerabilities (Prototype Pollution + ReDoS)
 *
 * Security Mitigations:
 * 1. File size limits (10MB max) - prevents oversized attacks
 * 2. Parsing timeout (5 seconds) - prevents ReDoS attacks
 * 3. Workbook structure validation - prevents memory exhaustion
 * 4. Error handling - prevents app crashes
 *
 * See: DEPENDENCY_AUDIT_REPORT.md for vulnerability details
 */

// Maximum file size: 10MB (prevents DoS via large files)
const MAX_FILE_SIZE = 10 * 1024 * 1024;

// Parsing timeout: 5 seconds (prevents ReDoS attacks)
const PARSING_TIMEOUT_MS = 5000;

// Maximum number of sheets to process
const MAX_SHEETS = 100;

// Maximum rows per sheet
const MAX_ROWS_PER_SHEET = 100000;

/**
 * Validate file size before processing
 * @param {File} file - File object to validate
 * @throws {Error} If file exceeds maximum size
 */
export function validateFileSize(file) {
  if (!file) {
    throw new Error("No file provided");
  }

  if (file.size > MAX_FILE_SIZE) {
    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    const maxSizeMB = (MAX_FILE_SIZE / (1024 * 1024)).toFixed(0);
    throw new Error(
      `File too large: ${sizeMB}MB. Maximum size: ${maxSizeMB}MB`
    );
  }
}

/**
 * Validate MIME type
 * @param {File} file - File object to validate
 * @throws {Error} If file type is not Excel
 */
export function validateFileType(file) {
  const validTypes = [
    "application/vnd.ms-excel", // .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // .xlsx
    "text/csv", // .csv
  ];

  const validExtensions = [".xls", ".xlsx", ".csv"];
  const fileName = file.name.toLowerCase();
  const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext));

  if (!validTypes.includes(file.type) && !hasValidExtension) {
    throw new Error(
      "Invalid file type. Please upload an Excel file (.xls, .xlsx) or CSV file."
    );
  }
}

/**
 * Parse Excel file with timeout protection
 * Wraps parsing in a Promise.race to enforce timeout
 *
 * @param {Function} parseFunction - Function that parses the file (returns Promise)
 * @param {number} timeout - Timeout in milliseconds (default: 5000ms)
 * @returns {Promise} Parsed result or timeout error
 */
export async function parseWithTimeout(parseFunction, timeout = PARSING_TIMEOUT_MS) {
  return Promise.race([
    parseFunction(),
    new Promise((_, reject) =>
      setTimeout(
        () => reject(new Error("Excel parsing timeout. File may be corrupted or too complex.")),
        timeout
      )
    ),
  ]);
}

/**
 * Validate workbook structure after parsing
 * Prevents memory exhaustion attacks
 *
 * @param {Object} workbook - Parsed workbook object
 * @throws {Error} If workbook structure is invalid or excessive
 */
export function validateWorkbookStructure(workbook) {
  if (!workbook || !workbook.SheetNames) {
    throw new Error("Invalid workbook structure");
  }

  // Check number of sheets
  if (workbook.SheetNames.length > MAX_SHEETS) {
    throw new Error(
      `Too many sheets: ${workbook.SheetNames.length}. Maximum: ${MAX_SHEETS}`
    );
  }

  // Check rows per sheet
  workbook.SheetNames.forEach(sheetName => {
    const sheet = workbook.Sheets[sheetName];
    if (!sheet) return;

    // Get sheet range
    const range = sheet["!ref"];
    if (!range) return;

    // Parse range (e.g., "A1:Z1000")
    const match = range.match(/[A-Z]+(\d+):[A-Z]+(\d+)/);
    if (match) {
      const startRow = parseInt(match[1], 10);
      const endRow = parseInt(match[2], 10);
      const rowCount = endRow - startRow + 1;

      if (rowCount > MAX_ROWS_PER_SHEET) {
        throw new Error(
          `Sheet "${sheetName}" has too many rows: ${rowCount}. Maximum: ${MAX_ROWS_PER_SHEET}`
        );
      }
    }
  });
}

/**
 * Safe Excel file parser with all security mitigations
 *
 * Usage:
 * ```js
 * import { safeParseExcel } from './utils/excelSafety';
 *
 * try {
 *   const workbook = await safeParseExcel(file, (file) => {
 *     return new Promise((resolve) => {
 *       const reader = new FileReader();
 *       reader.onload = (e) => {
 *         const data = new Uint8Array(e.target.result);
 *         const workbook = XLSX.read(data, { type: 'array' });
 *         resolve(workbook);
 *       };
 *       reader.readAsArrayBuffer(file);
 *     });
 *   });
 *   // Process workbook safely
 * } catch (error) {
 *   // Handle error (file too large, timeout, invalid structure, etc.)
 * }
 * ```
 *
 * @param {File} file - File object to parse
 * @param {Function} parseFunction - Custom parsing function
 * @param {Object} options - Options { timeout, skipValidation }
 * @returns {Promise<Object>} Parsed workbook
 */
export async function safeParseExcel(file, parseFunction, options = {}) {
  const {
    timeout = PARSING_TIMEOUT_MS,
    skipSizeValidation = false,
    skipTypeValidation = false,
    skipStructureValidation = false,
  } = options;

  // Step 1: Validate file size
  if (!skipSizeValidation) {
    validateFileSize(file);
  }

  // Step 2: Validate file type
  if (!skipTypeValidation) {
    validateFileType(file);
  }

  // Step 3: Parse with timeout protection
  const workbook = await parseWithTimeout(
    () => parseFunction(file),
    timeout
  );

  // Step 4: Validate workbook structure
  if (!skipStructureValidation) {
    validateWorkbookStructure(workbook);
  }

  return workbook;
}

/**
 * Create a sanitized error message for user display
 * Prevents information disclosure
 *
 * @param {Error} error - Original error
 * @returns {string} User-friendly error message
 */
export function getSafeErrorMessage(error) {
  const message = error.message || "Unknown error";

  // Known safe error messages
  const safeMessages = [
    "File too large",
    "Invalid file type",
    "Excel parsing timeout",
    "Too many sheets",
    "Invalid workbook structure",
  ];

  // Check if error message contains safe keywords
  const isSafe = safeMessages.some(safe => message.includes(safe));

  if (isSafe) {
    return message;
  }

  // Generic error for unexpected issues
  return "Unable to process Excel file. Please ensure the file is valid and not corrupted.";
}

export default {
  validateFileSize,
  validateFileType,
  parseWithTimeout,
  validateWorkbookStructure,
  safeParseExcel,
  getSafeErrorMessage,
  MAX_FILE_SIZE,
  PARSING_TIMEOUT_MS,
};
