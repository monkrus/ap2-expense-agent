import React, { useEffect, useState } from "react";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

const GoogleCallback = () => {
  const [status, setStatus] = useState("processing"); // processing, success, error

  useEffect(() => {
    const processCallback = async () => {
      // Parse URL parameters manually
      const params = new URLSearchParams(window.location.search);
      const access_token = params.get("access_token");
      const refresh_token = params.get("refresh_token");
      const error = params.get("error");

      // Handle error from OAuth provider
      if (error) {
        console.error("OAuth error:", error);
        setStatus("error");
        setTimeout(() => {
          window.location.href = "/?error=oauth_failed";
        }, 2000);
        return;
      }

      // Handle successful OAuth
      if (access_token && refresh_token) {
        try {
          // Store tokens in localStorage
          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", refresh_token);

          // Fetch user info to update auth context
          const apiUrl =
            import.meta.env.VITE_API_BASE_URL || "";
          const response = await fetch(`${apiUrl}/api/v1/auth/me`, {
            headers: {
              Authorization: `Bearer ${access_token}`,
              "Content-Type": "application/json",
            },
          });

          if (response.ok) {
            const userData = await response.json().catch(() => ({}));
            console.log("User authenticated:", userData);
            setStatus("success");

            // Redirect to main app after brief success message
            setTimeout(() => {
              window.location.href = "/";
            }, 1500);
          } else {
            throw new Error("Failed to fetch user info");
          }
        } catch (err) {
          console.error("Error processing OAuth callback:", err);
          setStatus("error");
          setTimeout(() => {
            window.location.href = "/?error=auth_failed";
          }, 2000);
        }
      } else {
        // Missing required parameters
        console.error("Missing access_token or refresh_token");
        setStatus("error");
        setTimeout(() => {
          window.location.href = "/?error=invalid_callback";
        }, 2000);
      }
    };

    processCallback();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center">
          {status === "processing" && (
            <>
              <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-100 rounded-full mb-4">
                <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">
                Completing sign in...
              </h2>
              <p className="text-gray-600">
                Please wait while we authenticate your account.
              </p>
            </>
          )}

          {status === "success" && (
            <>
              <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">
                Success!
              </h2>
              <p className="text-gray-600">
                You've been successfully authenticated.
              </p>
              <p className="text-gray-600 mt-2">
                Redirecting to your dashboard...
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                <XCircle className="w-8 h-8 text-red-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">
                Authentication Failed
              </h2>
              <p className="text-gray-600">
                There was a problem completing your sign in.
              </p>
              <p className="text-gray-600 mt-2">Redirecting to login page...</p>
            </>
          )}

          <div className="mt-6">
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-1000 ${
                  status === "success"
                    ? "bg-green-500"
                    : status === "error"
                      ? "bg-red-500"
                      : "bg-indigo-500 animate-pulse"
                }`}
                style={{ width: status === "processing" ? "50%" : "100%" }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GoogleCallback;
