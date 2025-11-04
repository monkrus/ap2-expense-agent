import React, { useState, useEffect } from 'react';
import { Mail, CheckCircle, XCircle, AlertCircle, Loader, Building2, ArrowRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import organizationAPI from '../services/organizationAPI';

const AcceptInvitation = ({ token }) => {
  const { user } = useAuth();
  const { success, error: showError } = useToast();

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('idle'); // idle, accepting, success, error
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    // If user is not logged in, show message
    if (!user) {
      // Will show loading state
    }
  }, [user]);

  const handleAccept = async () => {
    setLoading(true);
    setStatus('accepting');

    try {
      await organizationAPI.acceptInvitation(token);
      setStatus('success');
      success('Invitation accepted! Redirecting to organization...');

      // Redirect to organizations page after 2 seconds
      setTimeout(() => {
        navigate('/organizations');
      }, 2000);
    } catch (err) {
      setStatus('error');
      setErrorMessage(err.message || 'Failed to accept invitation');
      showError(err.message || 'Failed to accept invitation');
    } finally {
      setLoading(false);
    }
  };

  const handleDecline = () => {
    navigate('/');
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-gray-600">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-6">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-8">
        {status === 'idle' && (
          <>
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Mail className="w-8 h-8 text-indigo-600" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Organization Invitation
              </h1>
              <p className="text-gray-600">
                You've been invited to join an organization
              </p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <div className="flex items-center gap-3 mb-3">
                <Building2 className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Logged in as</p>
                  <p className="font-medium text-gray-900">{user.email}</p>
                </div>
              </div>
              <div className="text-sm text-gray-600">
                <p>By accepting this invitation, you will be added to the organization as a team member.</p>
              </div>
            </div>

            <div className="space-y-3">
              <button
                onClick={handleAccept}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {loading ? (
                  <>
                    <Loader className="w-5 h-5 animate-spin" />
                    Accepting...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    Accept Invitation
                  </>
                )}
              </button>

              <button
                onClick={handleDecline}
                disabled={loading}
                className="w-full px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Decline
              </button>
            </div>
          </>
        )}

        {status === 'accepting' && (
          <div className="text-center py-8">
            <Loader className="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Accepting Invitation...
            </h2>
            <p className="text-gray-600">
              Please wait while we add you to the organization
            </p>
          </div>
        )}

        {status === 'success' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Invitation Accepted!
            </h2>
            <p className="text-gray-600 mb-6">
              You've successfully joined the organization
            </p>
            <div className="flex items-center justify-center gap-2 text-indigo-600">
              <span className="text-sm">Redirecting to organization</span>
              <ArrowRight className="w-4 h-4 animate-pulse" />
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <XCircle className="w-8 h-8 text-red-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Unable to Accept Invitation
            </h2>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="text-left">
                  <p className="text-sm font-medium text-red-900 mb-1">Error</p>
                  <p className="text-sm text-red-700">{errorMessage}</p>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <button
                onClick={handleAccept}
                className="w-full px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => navigate('/')}
                className="w-full px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AcceptInvitation;
