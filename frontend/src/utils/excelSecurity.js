/**
 * Excel Security Utilities
 *
 * Mitigations for xlsx library vulnerabilities:
 * - CVE: GHSA-4r6h-8v6p-xvw6 (Prototype Pollution)
 * - CVE: GHSA-5pgg-2g8v-p4x9 (ReDoS)
 *
 * See: DEPENDENCY_AUDIT_REPORT.md for full details
 */

// Security constants
export const EXCEL_SECURITY = {
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  MAX_FILE_SIZE_LABEL: '10MB',
  PARSING_TIMEOUT: 5000, // 5 seconds
  PARSING_TIMEOUT_LABEL: '5 seconds',
  MAX_ROWS: 50000, // Safety limit for row count
  MAX_COLUMNS: 100, // Safety limit for column count
};

/**
 * Validates file size before processing
 * @param {File} file - File object to validate
 * @throws {Error} If file exceeds size limit
 */
export function validateFileSize(file) {
  if (!file) {
    throw new Error('No file provided');
  }

  if (file.size > EXCEL_SECURITY.MAX_FILE_SIZE) {
    throw new Error(
      `File too large. Maximum size: ${EXCEL_SECURITY.MAX_FILE_SIZE_LABEL}. ` +
      `Your file: ${(file.size / 1024 / 1024).toFixed(2)}MB`
    );
  }

  return true;
}

/**
 * Validates file type
 * @param {File} file - File object to validate
 * @param {string[]} allowedTypes - Allowed MIME types
 * @throws {Error} If file type is not allowed
 */
export function validateFileType(file, allowedTypes = [
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
  'application/vnd.ms-excel', // .xls
  'text/csv', // .csv
]) {
  if (!file) {
    throw new Error('No file provided');
  }

  if (!allowedTypes.includes(file.type)) {
    throw new Error(
      `Invalid file type. Allowed types: ${allowedTypes.join(', ')}`
    );
  }

  return true;
}

/**
 * Execute a promise with timeout
 * @param {Promise} promise - Promise to execute
 * @param {number} timeoutMs - Timeout in milliseconds
 * @returns {Promise} Promise that resolves or rejects based on timeout
 */
export function withTimeout(promise, timeoutMs = EXCEL_SECURITY.PARSING_TIMEOUT) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(
        () => reject(new Error(
          `Operation timed out after ${timeoutMs / 1000} seconds. ` +
          `This may indicate a malformed or overly complex file.`
        )),
        timeoutMs
      )
    ),
  ]);
}

/**
 * Safely parse Excel file with timeout protection
 * @param {Function} parseFunction - Function that parses the file
 * @param {any} args - Arguments to pass to parse function
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise} Parsed data or error
 */
export async function safeExcelParse(parseFunction, args, timeout = EXCEL_SECURITY.PARSING_TIMEOUT) {
  try {
    return await withTimeout(
      Promise.resolve(parseFunction(args)),
      timeout
    );
  } catch (error) {
    console.error('Excel parsing error:', error);
    throw error;
  }
}

/**
 * Validate workbook structure to prevent excessive memory usage
 * @param {Object} workbook - XLSX workbook object
 * @throws {Error} If workbook structure is dangerous
 */
export function validateWorkbookStructure(workbook) {
  if (!workbook || !workbook.SheetNames) {
    throw new Error('Invalid workbook structure');
  }

  // Check sheet count
  if (workbook.SheetNames.length > 50) {
    throw new Error(
      `Too many sheets. Maximum: 50. Found: ${workbook.SheetNames.length}`
    );
  }

  // Validate each sheet
  for (const sheetName of workbook.SheetNames) {
    const sheet = workbook.Sheets[sheetName];

    if (!sheet || !sheet['!ref']) {
      continue; // Empty sheet
    }

    // Parse range to get dimensions
    const range = parseRange(sheet['!ref']);

    if (!range) {
      throw new Error(`Invalid range in sheet: ${sheetName}`);
    }

    const rowCount = range.e.r - range.s.r + 1;
    const colCount = range.e.c - range.s.c + 1;

    if (rowCount > EXCEL_SECURITY.MAX_ROWS) {
      throw new Error(
        `Sheet "${sheetName}" has too many rows. ` +
        `Maximum: ${EXCEL_SECURITY.MAX_ROWS}. Found: ${rowCount}`
      );
    }

    if (colCount > EXCEL_SECURITY.MAX_COLUMNS) {
      throw new Error(
        `Sheet "${sheetName}" has too many columns. ` +
        `Maximum: ${EXCEL_SECURITY.MAX_COLUMNS}. Found: ${colCount}`
      );
    }
  }

  return true;
}

/**
 * Parse Excel cell range (simplified version)
 * @param {string} range - Range string like "A1:Z100"
 * @returns {Object|null} Parsed range object
 */
function parseRange(range) {
  if (!range || typeof range !== 'string') {
    return null;
  }

  try {
    const parts = range.split(':');
    if (parts.length !== 2) {
      return null;
    }

    const start = parseCell(parts[0]);
    const end = parseCell(parts[1]);

    if (!start || !end) {
      return null;
    }

    return {
      s: start, // start
      e: end,   // end
    };
  } catch (error) {
    console.error('Range parsing error:', error);
    return null;
  }
}

/**
 * Parse Excel cell reference (simplified version)
 * @param {string} cell - Cell reference like "A1"
 * @returns {Object|null} Parsed cell object with row and column
 */
function parseCell(cell) {
  if (!cell || typeof cell !== 'string') {
    return null;
  }

  const match = cell.match(/^([A-Z]+)(\d+)$/);
  if (!match) {
    return null;
  }

  const col = columnToIndex(match[1]);
  const row = parseInt(match[2], 10) - 1; // 0-indexed

  return { r: row, c: col };
}

/**
 * Convert column letters to index
 * @param {string} col - Column letters like "A" or "AB"
 * @returns {number} Column index (0-based)
 */
function columnToIndex(col) {
  let index = 0;
  for (let i = 0; i < col.length; i++) {
    index = index * 26 + (col.charCodeAt(i) - 65 + 1);
  }
  return index - 1; // 0-indexed
}

/**
 * Sanitize workbook data to prevent prototype pollution
 * Note: This is a defense-in-depth measure. The main protection
 * is that we only export (not import) Excel files in production.
 *
 * @param {Object} data - Data object to sanitize
 * @returns {Object} Sanitized data
 */
export function sanitizeWorkbookData(data) {
  if (!data || typeof data !== 'object') {
    return data;
  }

  // Create new object without prototype chain
  const sanitized = Object.create(null);

  for (const key of Object.keys(data)) {
    // Skip dangerous keys
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
      console.warn(`Skipping dangerous key: ${key}`);
      continue;
    }

    // Recursively sanitize nested objects
    if (data[key] && typeof data[key] === 'object') {
      sanitized[key] = sanitizeWorkbookData(data[key]);
    } else {
      sanitized[key] = data[key];
    }
  }

  return sanitized;
}

/**
 * Create error message with security context
 * @param {Error} error - Original error
 * @param {string} context - Context of the error
 * @returns {string} User-friendly error message
 */
export function createSecureErrorMessage(error, context = 'Excel operation') {
  // Don't expose internal error details
  const message = error.message || 'Unknown error';

  // Check for known security-related errors
  if (message.includes('timeout')) {
    return 'File processing timed out. The file may be too complex or corrupted.';
  }

  if (message.includes('too large') || message.includes('size')) {
    return message; // Size errors are safe to show
  }

  if (message.includes('too many')) {
    return message; // Validation errors are safe to show
  }

  // Generic error for unknown cases
  return `${context} failed. Please ensure the file is valid and not corrupted.`;
}

/**
 * Log security event (for monitoring)
 * In production, this should send to monitoring service
 * @param {string} event - Event name
 * @param {Object} details - Event details
 */
export function logSecurityEvent(event, details = {}) {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    event,
    details,
    userAgent: navigator.userAgent,
  };

  // In development, log to console
  if (process.env.NODE_ENV === 'development') {
    console.warn('[Security Event]', logEntry);
  }

  // In production, send to monitoring service
  // Example: sendToMonitoring(logEntry);
}

/**
 * All-in-one validation for Excel import operations
 * @param {File} file - File to validate
 * @throws {Error} If validation fails
 */
export function validateExcelImport(file) {
  try {
    validateFileSize(file);
    validateFileType(file);

    logSecurityEvent('excel_import_validation_passed', {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
    });

    return true;
  } catch (error) {
    logSecurityEvent('excel_import_validation_failed', {
      fileName: file?.name,
      fileSize: file?.size,
      fileType: file?.type,
      error: error.message,
    });

    throw error;
  }
}

export default {
  EXCEL_SECURITY,
  validateFileSize,
  validateFileType,
  withTimeout,
  safeExcelParse,
  validateWorkbookStructure,
  sanitizeWorkbookData,
  createSecureErrorMessage,
  logSecurityEvent,
  validateExcelImport,
};
