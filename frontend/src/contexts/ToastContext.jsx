import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

const ToastContext = createContext(null);
let toastCounter = 0;

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback((message, type = "info") => {
    const id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${toastCounter++}`;
    const toast = { id, message, type };

    setToasts((prev) => [...prev, toast]);

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const value = useMemo(
    () => ({
      toasts,
      showToast,
      removeToast,
      success: (message) => showToast(message, "success"),
      error: (message) => showToast(message, "error"),
      info: (message) => showToast(message, "info"),
      warning: (message) => showToast(message, "warning"),
    }),
    [toasts, showToast, removeToast],
  );

  return (
    <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
};
