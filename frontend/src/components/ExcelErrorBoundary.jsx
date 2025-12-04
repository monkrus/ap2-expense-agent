import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { logSecurityEvent } from '../utils/excelSecurity';

/**
 * Error Boundary for Excel/File Operations
 *
 * Catches errors during Excel export/import operations to prevent
 * application crashes and provide a safe fallback UI during file handling.
 */
class ExcelErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render shows fallback UI
    return {
      hasError: true,
      error: error,
    };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details
    console.error('Excel Error Boundary caught error:', error, errorInfo);

    // Log security event
    logSecurityEvent('excel_error_boundary_triggered', {
      error: error?.message || 'Unknown error',
      errorStack: error?.stack,
      componentStack: errorInfo?.componentStack,
      errorCount: this.state.errorCount + 1,
    });

    // Update state with error info
    this.setState(prevState => ({
      errorInfo: errorInfo,
      errorCount: prevState.errorCount + 1,
    }));

    // Call optional error handler from props
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });

    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback({
          error: this.state.error,
          errorInfo: this.state.errorInfo,
          reset: this.handleReset,
        });
      }

      // Default fallback UI
      return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-red-100 rounded-full">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">
                Export Error
              </h2>
            </div>

            <div className="mb-6">
              <p className="text-gray-600 mb-3">
                An error occurred while processing your file export.
              </p>

              {this.state.error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                  <p className="text-sm font-medium text-red-800 mb-1">
                    Error Details:
                  </p>
                  <p className="text-sm text-red-700 font-mono break-words">
                    {this.state.error.message || 'Unknown error'}
                  </p>
                </div>
              )}

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-sm font-medium text-blue-800 mb-2">
                  Suggestions:
                </p>
                <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
                  <li>Try exporting fewer expenses</li>
                  <li>Use CSV format instead of Excel</li>
                  <li>Refresh the page and try again</li>
                  <li>Contact support if the issue persists</li>
                </ul>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Try Again
              </button>
              {this.props.onClose && (
                <button
                  onClick={() => {
                    this.handleReset();
                    this.props.onClose();
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Close
                </button>
              )}
            </div>

            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="mt-4">
                <summary className="text-sm text-gray-600 cursor-pointer hover:text-gray-800">
                  Developer Info (Dev Only)
                </summary>
                <pre className="mt-2 text-xs bg-gray-100 p-3 rounded overflow-auto max-h-40">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    // No error, render children normally
    return this.props.children;
  }
}

export default ExcelErrorBoundary;
