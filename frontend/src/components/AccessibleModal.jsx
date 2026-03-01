/**
 * AccessibleModal Component
 *
 * A fully accessible modal dialog component with:
 * - Focus trap (keeps focus within modal)
 * - ESC key handler
 * - ARIA attributes (role="dialog", aria-modal="true")
 * - Automatic focus management
 * - Screen reader announcements
 * - Backdrop click to close
 *
 * WCAG 2.1 AA Compliant
 *
 * Usage:
 * ```jsx
 * <AccessibleModal
 *   isOpen={isOpen}
 *   onClose={handleClose}
 *   title="Modal Title"
 *   description="Optional description"
 * >
 *   <p>Modal content</p>
 * </AccessibleModal>
 * ```
 */

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";

const AccessibleModal = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  size = "medium", // 'small', 'medium', 'large', 'full'
  showCloseButton = true,
  closeOnBackdropClick = true,
  closeOnEscape = true,
  className = "",
}) => {
  const modalRef = useRef(null);
  const closeButtonRef = useRef(null);
  const previousFocusRef = useRef(null);

  // Store the element that had focus before modal opened
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement;
    }
  }, [isOpen]);

  // Focus trap and keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const modal = modalRef.current;
    if (!modal) return;

    // Get all focusable elements
    const focusableElements = modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus first element (close button or first focusable)
    if (closeButtonRef.current) {
      closeButtonRef.current.focus();
    } else if (firstElement) {
      firstElement.focus();
    }

    // Handle tab key for focus trap
    const handleTab = (e) => {
      if (e.key !== "Tab") return;

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    // Handle escape key
    const handleEscape = (e) => {
      if (e.key === "Escape" && closeOnEscape) {
        onClose();
      }
    };

    modal.addEventListener("keydown", handleTab);
    modal.addEventListener("keydown", handleEscape);

    // Cleanup
    return () => {
      modal.removeEventListener("keydown", handleTab);
      modal.removeEventListener("keydown", handleEscape);

      // Restore focus to previous element
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [isOpen, onClose, closeOnEscape]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }

    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  // Handle backdrop click
  const handleBackdropClick = (e) => {
    if (closeOnBackdropClick && e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  // Size classes
  const sizeClasses = {
    small: "max-w-md",
    medium: "max-w-2xl",
    large: "max-w-4xl",
    full: "max-w-full mx-4",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
      onClick={handleBackdropClick}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "modal-title" : undefined}
        aria-describedby={description ? "modal-description" : undefined}
        onClick={(e) => e.stopPropagation()}
        className={`bg-white rounded-lg shadow-xl w-full ${sizeClasses[size]} max-h-[90vh] overflow-y-auto ${className}`}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-gray-200">
          <div className="flex-1">
            {title && (
              <h2
                id="modal-title"
                className="text-xl font-bold text-gray-900"
              >
                {title}
              </h2>
            )}
            {description && (
              <p
                id="modal-description"
                className="mt-1 text-sm text-gray-600"
              >
                {description}
              </p>
            )}
          </div>
          {showCloseButton && (
            <button
              ref={closeButtonRef}
              onClick={onClose}
              className="ml-4 p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
              aria-label="Close dialog"
            >
              <X className="w-6 h-6" aria-hidden="true" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
};

export default AccessibleModal;
