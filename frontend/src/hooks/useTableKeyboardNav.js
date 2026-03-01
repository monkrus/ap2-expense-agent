/**
 * useTableKeyboardNav Hook
 *
 * Provides keyboard navigation for HTML tables
 *
 * Features:
 * - Arrow Up/Down: Navigate between rows
 * - Enter/Space: Activate selected row
 * - Home/End: Jump to first/last row
 * - ARIA attributes for accessibility
 *
 * Usage:
 * ```jsx
 * const { getRowProps, selectedIndex } = useTableKeyboardNav({
 *   rowCount: expenses.length,
 *   onRowActivate: (index) => handleExpenseClick(expenses[index])
 * });
 *
 * {expenses.map((expense, index) => (
 *   <tr {...getRowProps(index)}>
 *     ...
 *   </tr>
 * ))}
 * ```
 */

import { useState, useCallback } from "react";

export const useTableKeyboardNav = ({
  rowCount = 0,
  onRowActivate = () => {},
  initialIndex = -1,
  enableArrowKeys = true,
  enableHomeEnd = true,
  enableEnterSpace = true,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(initialIndex);

  const handleKeyDown = useCallback(
    (index, event) => {
      const { key } = event;

      // Arrow navigation
      if (enableArrowKeys) {
        if (key === "ArrowDown") {
          event.preventDefault();
          const nextIndex = Math.min(index + 1, rowCount - 1);
          setSelectedIndex(nextIndex);
          // Focus next row
          const nextRow = event.currentTarget.parentElement.children[nextIndex + 1]; // +1 for header
          if (nextRow) nextRow.focus();
        } else if (key === "ArrowUp") {
          event.preventDefault();
          const prevIndex = Math.max(index - 1, 0);
          setSelectedIndex(prevIndex);
          // Focus previous row
          const prevRow = event.currentTarget.parentElement.children[prevIndex + 1]; // +1 for header
          if (prevRow) prevRow.focus();
        }
      }

      // Home/End navigation
      if (enableHomeEnd) {
        if (key === "Home") {
          event.preventDefault();
          setSelectedIndex(0);
          const firstRow = event.currentTarget.parentElement.children[1]; // After header
          if (firstRow) firstRow.focus();
        } else if (key === "End") {
          event.preventDefault();
          setSelectedIndex(rowCount - 1);
          const lastRow = event.currentTarget.parentElement.children[rowCount]; // Header + rows
          if (lastRow) lastRow.focus();
        }
      }

      // Enter/Space activation
      if (enableEnterSpace) {
        if (key === "Enter" || key === " ") {
          event.preventDefault();
          setSelectedIndex(index);
          onRowActivate(index);
        }
      }
    },
    [rowCount, onRowActivate, enableArrowKeys, enableHomeEnd, enableEnterSpace]
  );

  const getRowProps = useCallback(
    (index, ariaLabel = "") => ({
      tabIndex: index === 0 ? 0 : -1, // Only first row in tab order
      role: "row",
      "aria-rowindex": index + 2, // +2 for 1-based and header row
      "aria-label": ariaLabel,
      "aria-selected": selectedIndex === index,
      onKeyDown: (e) => handleKeyDown(index, e),
      onFocus: () => setSelectedIndex(index),
      className: selectedIndex === index ? "bg-blue-50" : "",
      style: {
        cursor: "pointer",
      },
    }),
    [selectedIndex, handleKeyDown]
  );

  return {
    selectedIndex,
    setSelectedIndex,
    getRowProps,
  };
};

export default useTableKeyboardNav;
