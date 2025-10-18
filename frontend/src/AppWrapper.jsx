import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './components/Login';
import Register from './components/Register';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import App from './App';
import GoogleCallback from './pages/GoogleCallback';

const AppContent = () => {
  const [showAuth, setShowAuth] = useState('login');
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const { isAuthenticated, loading } = useAuth();

  // Simple client-side routing
  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Check if we're on Google OAuth callback page
  if (currentPath === '/auth/google/success' || window.location.pathname === '/auth/google/success') {
    return <GoogleCallback />;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500">
        <div className="bg-white p-8 rounded-2xl shadow-2xl">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (showAuth === 'login') {
      return (
        <Login
          onSuccess={() => setShowAuth('app')}
          onSwitchToRegister={() => setShowAuth('register')}
        />
      );
    } else {
      return (
        <Register
          onSuccess={() => setShowAuth('login')}
          onSwitchToLogin={() => setShowAuth('login')}
        />
      );
    }
  }

  return (
    <ProtectedRoute>
      <App />
    </ProtectedRoute>
  );
};

const AppWrapper = () => {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default AppWrapper;
