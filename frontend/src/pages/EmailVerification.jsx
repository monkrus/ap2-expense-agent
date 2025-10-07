import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Loader2, Mail } from 'lucide-react';

const EmailVerification = () => {
  const [status, setStatus] = useState('processing'); // processing, success, error
  const [message, setMessage] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      // Get token from URL
      const params = new URLSearchParams(window.location.search);
      const token = params.get('token');

      if (!token) {
        setStatus('error');
        setMessage('Invalid verification link');
        return;
      }

      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/v1/auth/verify-email?token=${token}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        const data = await response.json();

        if (response.ok) {
          setStatus('success');
          setMessage('Your email has been verified successfully!');

          // Redirect to login after 3 seconds
          setTimeout(() => {
            window.location.href = '/?verified=true';
          }, 3000);
        } else {
          setStatus('error');
          setMessage(data.detail || 'Email verification failed');

          // Redirect to home after 5 seconds
          setTimeout(() => {
            window.location.href = '/';
          }, 5000);
        }
      } catch (error) {
        setStatus('error');
        setMessage('An error occurred during email verification');

        // Redirect to home after 5 seconds
        setTimeout(() => {
          window.location.href = '/';
        }, 5000);
      }
    };

    verifyEmail();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center">
          {status === 'processing' && (
            <>
              <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-100 rounded-full mb-4">
                <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Verifying your email...</h2>
              <p className="text-gray-600">Please wait while we verify your email address.</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Email Verified!</h2>
              <p className="text-gray-600">{message}</p>
              <p className="text-gray-600 mt-2">Redirecting to login page...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                <XCircle className="w-8 h-8 text-red-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Verification Failed</h2>
              <p className="text-gray-600">{message}</p>
              <p className="text-gray-600 mt-4">The verification link may have expired or is invalid.</p>
              <p className="text-gray-600">Redirecting to home page...</p>
            </>
          )}

          <div className="mt-6">
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-1000 ${
                  status === 'success' ? 'bg-green-500' :
                  status === 'error' ? 'bg-red-500' :
                  'bg-indigo-500 animate-pulse'
                }`}
                style={{ width: status === 'processing' ? '50%' : '100%' }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailVerification;
