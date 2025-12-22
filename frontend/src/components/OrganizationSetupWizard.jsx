import React, { useState, useEffect } from "react";
import {
  Building2,
  Users,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  Upload,
  Settings,
  Mail,
  FileText,
  Sparkles,
  CreditCard,
  Zap,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../hooks/useToast";
import organizationAPI from "../services/organizationAPI";
import billingAPI from "../services/billingAPI";

/**
 * Organization Setup Wizard
 *
 * Shown to new GCP Marketplace customers on first login.
 * Guides them through:
 * 1. Welcome & Overview
 * 2. Company Profile
 * 3. Invite Team Members (CSV upload)
 * 4. Configure Settings
 * 5. Completion
 */
const OrganizationSetupWizard = ({ onComplete }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { success, error: showError } = useToast();

  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [organization, setOrganization] = useState(null);
  const [subscription, setSubscription] = useState(null);

  // Form data
  const [companyData, setCompanyData] = useState({
    description: "",
    currency: "USD",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  });

  const [inviteData, setInviteData] = useState({
    emails: "",
    role: "member",
  });

  const [csvFile, setCsvFile] = useState(null);
  const [parsedEmails, setParsedEmails] = useState([]);

  const totalSteps = 5;

  // Load organization on mount
  useEffect(() => {
    loadOrganization();
  }, []);

  const loadOrganization = async () => {
    try {
      const orgs = await organizationAPI.listOrganizations();
      if (orgs && orgs.length > 0) {
        const org = orgs[0];
        setOrganization(org);
        organizationAPI.setCurrentOrganizationId(org.id);

        // Load subscription info
        try {
          const sub = await billingAPI.getSubscription();
          setSubscription(sub);
        } catch (err) {
          console.log("No subscription found");
        }
      }
    } catch (err) {
      showError("Failed to load organization");
    }
  };

  const handleNextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    } else {
      completeSetup();
    }
  };

  const handlePrevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const completeSetup = async () => {
    try {
      setLoading(true);

      // Mark setup as complete
      if (organization) {
        await organizationAPI.updateOrganization(organization.id, {
          metadata: {
            setup_completed: true,
            completed_at: new Date().toISOString(),
          },
        });
      }

      success("Setup complete! Welcome to AP2 Expense Agent 🎉");

      // Call onComplete callback
      if (onComplete) {
        onComplete();
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      showError("Failed to complete setup");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateCompanyProfile = async () => {
    if (!organization) return;

    try {
      setLoading(true);
      await organizationAPI.updateOrganization(organization.id, companyData);
      success("Company profile updated!");
      handleNextStep();
    } catch (err) {
      showError(err.message || "Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  const handleInviteTeam = async () => {
    if (!organization) return;

    try {
      setLoading(true);

      let emailList = [];

      // Parse CSV or manual emails
      if (parsedEmails.length > 0) {
        emailList = parsedEmails;
      } else if (inviteData.emails.trim()) {
        emailList = inviteData.emails
          .split(/[,\n]/)
          .map((e) => e.trim())
          .filter((e) => e.length > 0);
      }

      if (emailList.length === 0) {
        // Skip if no emails
        handleNextStep();
        return;
      }

      // Bulk invite
      const results = await organizationAPI.bulkInviteMembers(
        organization.id,
        emailList,
        inviteData.role,
      );

      success(`Invited ${results.successful.length} team members!`);
      if (results.failed.length > 0) {
        showError(`Failed to invite ${results.failed.length} members`);
      }

      handleNextStep();
    } catch (err) {
      showError(err.message || "Failed to invite team");
    } finally {
      setLoading(false);
    }
  };

  const handleCSVUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setCsvFile(file);

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const lines = text.split("\n").filter((line) => line.trim());

      // Skip header if present
      const startIndex = lines[0].toLowerCase().includes("email") ? 1 : 0;

      const emails = lines
        .slice(startIndex)
        .map((line) => {
          const parts = line.split(",");
          return parts[0].trim();
        })
        .filter((email) => email.includes("@"));

      setParsedEmails(emails);
      success(`Parsed ${emails.length} emails from CSV`);
    };

    reader.readAsText(file);
  };

  // Step components
  const WelcomeStep = () => (
    <div className="text-center py-12">
      <div className="flex justify-center mb-6">
        <div className="w-20 h-20 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
          <Sparkles className="w-10 h-10 text-white" />
        </div>
      </div>

      <h1 className="text-4xl font-bold mb-4">
        Welcome to AP2 Expense Agent! 🎉
      </h1>

      {organization && (
        <p className="text-xl text-gray-600 mb-8">{organization.name}</p>
      )}

      {subscription && subscription.gcp_entitlement_id && (
        <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 px-4 py-2 rounded-full mb-8">
          <img
            src="https://www.gstatic.com/images/branding/product/2x/gcp_48dp.png"
            alt="GCP"
            className="w-5 h-5"
          />
          <span className="font-medium">
            Powered by Google Cloud Marketplace
          </span>
        </div>
      )}

      <p className="text-lg text-gray-700 mb-6 max-w-2xl mx-auto">
        Your organization has been successfully provisioned! Let's get you set
        up in just a few minutes.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto mt-12">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
            <Users className="w-6 h-6 text-indigo-600" />
          </div>
          <h3 className="font-semibold mb-2">Invite Your Team</h3>
          <p className="text-sm text-gray-600">
            Add team members via CSV or email
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
            <Zap className="w-6 h-6 text-green-600" />
          </div>
          <h3 className="font-semibold mb-2">AI-Powered</h3>
          <p className="text-sm text-gray-600">
            Automatic expense categorization
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
            <CreditCard className="w-6 h-6 text-purple-600" />
          </div>
          <h3 className="font-semibold mb-2">AP2 Payments</h3>
          <p className="text-sm text-gray-600">Automated payment processing</p>
        </div>
      </div>

      {subscription && (
        <div className="mt-12 p-6 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg max-w-2xl mx-auto">
          <h3 className="font-semibold mb-2">
            Your Plan: {subscription.tier?.toUpperCase() || "Professional"}
          </h3>
          <p className="text-sm text-gray-600">
            You have access to all {subscription.tier || "professional"} tier
            features
          </p>
        </div>
      )}
    </div>
  );

  const CompanyProfileStep = () => (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Building2 className="w-8 h-8 text-indigo-600" />
        </div>
        <h2 className="text-2xl font-bold mb-2">
          Complete Your Company Profile
        </h2>
        <p className="text-gray-600">
          Add some details about your organization
        </p>
      </div>

      <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Company Name
          </label>
          <input
            type="text"
            value={organization?.name || ""}
            disabled
            className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50"
          />
          <p className="text-xs text-gray-500 mt-1">
            Cannot be changed (set by GCP Marketplace)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description (Optional)
          </label>
          <textarea
            value={companyData.description}
            onChange={(e) =>
              setCompanyData({ ...companyData, description: e.target.value })
            }
            placeholder="Brief description of your company..."
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Currency
            </label>
            <select
              value={companyData.currency}
              onChange={(e) =>
                setCompanyData({ ...companyData, currency: e.target.value })
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="USD">USD - US Dollar</option>
              <option value="EUR">EUR - Euro</option>
              <option value="GBP">GBP - British Pound</option>
              <option value="CAD">CAD - Canadian Dollar</option>
              <option value="AUD">AUD - Australian Dollar</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Timezone
            </label>
            <select
              value={companyData.timezone}
              onChange={(e) =>
                setCompanyData({ ...companyData, timezone: e.target.value })
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <optgroup label="Universal">
                <option value="UTC">UTC (Coordinated Universal Time)</option>
              </optgroup>
              <optgroup label="North America">
                <option value="America/New_York">
                  Eastern Time (New York)
                </option>
                <option value="America/Chicago">Central Time (Chicago)</option>
                <option value="America/Denver">Mountain Time (Denver)</option>
                <option value="America/Los_Angeles">
                  Pacific Time (Los Angeles)
                </option>
                <option value="America/Phoenix">Arizona (Phoenix)</option>
                <option value="America/Anchorage">Alaska (Anchorage)</option>
                <option value="Pacific/Honolulu">Hawaii (Honolulu)</option>
                <option value="America/Toronto">
                  Canada Eastern (Toronto)
                </option>
                <option value="America/Vancouver">
                  Canada Pacific (Vancouver)
                </option>
              </optgroup>
              <optgroup label="Europe">
                <option value="Europe/London">UK (London)</option>
                <option value="Europe/Paris">France (Paris)</option>
                <option value="Europe/Berlin">Germany (Berlin)</option>
                <option value="Europe/Rome">Italy (Rome)</option>
                <option value="Europe/Madrid">Spain (Madrid)</option>
                <option value="Europe/Amsterdam">
                  Netherlands (Amsterdam)
                </option>
                <option value="Europe/Brussels">Belgium (Brussels)</option>
                <option value="Europe/Zurich">Switzerland (Zurich)</option>
                <option value="Europe/Stockholm">Sweden (Stockholm)</option>
                <option value="Europe/Oslo">Norway (Oslo)</option>
                <option value="Europe/Moscow">Russia (Moscow)</option>
              </optgroup>
              <optgroup label="Asia">
                <option value="Asia/Dubai">UAE (Dubai)</option>
                <option value="Asia/Kolkata">India (Kolkata)</option>
                <option value="Asia/Singapore">Singapore</option>
                <option value="Asia/Hong_Kong">Hong Kong</option>
                <option value="Asia/Shanghai">China (Shanghai)</option>
                <option value="Asia/Tokyo">Japan (Tokyo)</option>
                <option value="Asia/Seoul">South Korea (Seoul)</option>
                <option value="Asia/Bangkok">Thailand (Bangkok)</option>
                <option value="Asia/Jakarta">Indonesia (Jakarta)</option>
              </optgroup>
              <optgroup label="Australia & Pacific">
                <option value="Australia/Sydney">
                  Australia East (Sydney)
                </option>
                <option value="Australia/Melbourne">
                  Australia (Melbourne)
                </option>
                <option value="Australia/Brisbane">Australia (Brisbane)</option>
                <option value="Australia/Perth">Australia West (Perth)</option>
                <option value="Pacific/Auckland">New Zealand (Auckland)</option>
              </optgroup>
              <optgroup label="Africa">
                <option value="Africa/Cairo">Egypt (Cairo)</option>
                <option value="Africa/Johannesburg">
                  South Africa (Johannesburg)
                </option>
                <option value="Africa/Lagos">Nigeria (Lagos)</option>
                <option value="Africa/Nairobi">Kenya (Nairobi)</option>
              </optgroup>
              <optgroup label="South America">
                <option value="America/Sao_Paulo">Brazil (São Paulo)</option>
                <option value="America/Argentina/Buenos_Aires">
                  Argentina (Buenos Aires)
                </option>
                <option value="America/Santiago">Chile (Santiago)</option>
                <option value="America/Bogota">Colombia (Bogota)</option>
                <option value="America/Lima">Peru (Lima)</option>
              </optgroup>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              <strong>Why UTC?</strong> UTC ensures consistent timestamps across
              global teams and prevents daylight saving confusion.
            </p>
          </div>
        </div>
      </div>
    </div>
  );

  const InviteTeamStep = () => (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Users className="w-8 h-8 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Invite Your Team</h2>
        <p className="text-gray-600">
          Add team members via CSV upload or manual entry
        </p>
      </div>

      <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 space-y-6">
        {/* CSV Upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Upload CSV File
          </label>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-indigo-400 transition-colors">
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-sm text-gray-600 mb-2">
              Drag and drop your CSV file here, or click to browse
            </p>
            <p className="text-xs text-gray-500 mb-4">
              CSV Format: email,role,department (header optional)
            </p>
            <input
              type="file"
              accept=".csv"
              onChange={handleCSVUpload}
              className="hidden"
              id="csv-upload"
            />
            <label
              htmlFor="csv-upload"
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer"
            >
              <Upload className="w-4 h-4" />
              Choose File
            </label>
          </div>

          {csvFile && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-700">
                ✓ Loaded {csvFile.name} - {parsedEmails.length} emails found
              </p>
            </div>
          )}
        </div>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">OR</span>
          </div>
        </div>

        {/* Manual Entry */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Enter Emails Manually
          </label>
          <textarea
            value={inviteData.emails}
            onChange={(e) =>
              setInviteData({ ...inviteData, emails: e.target.value })
            }
            placeholder="Enter email addresses (one per line or comma-separated)&#10;john@company.com&#10;sarah@company.com&#10;mike@company.com"
            rows={6}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Default Role
          </label>
          <select
            value={inviteData.role}
            onChange={(e) =>
              setInviteData({ ...inviteData, role: e.target.value })
            }
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          >
            <option value="member">Member</option>
            <option value="manager">Manager</option>
            <option value="admin">Admin</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            All invited users will be assigned this role
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex gap-3">
            <Mail className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-900 mb-1">
                Invitation Emails Will Be Sent
              </p>
              <p className="text-xs text-blue-700">
                Each team member will receive an email invitation to join{" "}
                {organization?.name || "your organization"}
              </p>
            </div>
          </div>
        </div>

        <div className="text-center text-sm text-gray-500">
          <p>
            You can skip this step and invite team members later from the
            settings page
          </p>
        </div>
      </div>
    </div>
  );

  const SettingsStep = () => (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Settings className="w-8 h-8 text-purple-600" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Almost Done!</h2>
        <p className="text-gray-600">
          Review your setup and configure additional settings
        </p>
      </div>

      <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 space-y-6">
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Quick Start Guide</h3>

          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Organization Created</p>
                <p className="text-sm text-gray-600">{organization?.name}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Subscription Active</p>
                <p className="text-sm text-gray-600">
                  {subscription?.tier?.toUpperCase() || "Professional"} Plan
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Team Invited</p>
                <p className="text-sm text-gray-600">
                  {parsedEmails.length > 0
                    ? `${parsedEmails.length} members invited`
                    : "You can invite team members anytime"}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t pt-6">
          <h3 className="font-semibold text-lg mb-4">Next Steps After Setup</h3>

          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-bold text-indigo-600">1</span>
              </div>
              <p className="text-sm">
                Submit your first expense and see AI categorization in action
              </p>
            </div>

            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-bold text-indigo-600">2</span>
              </div>
              <p className="text-sm">
                Configure approval workflows in Settings
              </p>
            </div>

            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-bold text-indigo-600">3</span>
              </div>
              <p className="text-sm">
                Set up payment methods for AP2 automated payments
              </p>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 p-6 rounded-lg">
          <div className="flex items-start gap-3">
            <FileText className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-indigo-900 mb-1">Need Help?</p>
              <p className="text-sm text-indigo-700 mb-2">
                Check out our documentation and video tutorials
              </p>
              <a
                href="https://docs.ap2expense.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                View Documentation →
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const CompletionStep = () => (
    <div className="text-center py-12">
      <div className="flex justify-center mb-6">
        <div className="w-24 h-24 bg-gradient-to-br from-green-400 to-emerald-600 rounded-full flex items-center justify-center animate-bounce">
          <CheckCircle className="w-12 h-12 text-white" />
        </div>
      </div>

      <h1 className="text-4xl font-bold mb-4">You're All Set! 🎉</h1>

      <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
        Your organization is ready to start managing expenses with AI-powered
        automation
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl mx-auto mb-12">
        <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 p-6 rounded-lg">
          <p className="text-3xl font-bold text-indigo-600 mb-2">
            {subscription?.tier || "Professional"}
          </p>
          <p className="text-sm text-gray-600">Your Plan</p>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-lg">
          <p className="text-3xl font-bold text-green-600 mb-2">
            {parsedEmails.length || "0"}
          </p>
          <p className="text-sm text-gray-600">Team Members Invited</p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-6 rounded-lg">
          <p className="text-3xl font-bold text-purple-600 mb-2">∞</p>
          <p className="text-sm text-gray-600">Expenses Ready</p>
        </div>
      </div>

      <button
        onClick={completeSetup}
        disabled={loading}
        className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:from-indigo-700 hover:to-purple-700 font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105"
      >
        {loading ? "Loading..." : "Go to Dashboard"}
        <ArrowRight className="w-5 h-5" />
      </button>
    </div>
  );

  // Render current step
  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return <WelcomeStep />;
      case 2:
        return <CompanyProfileStep />;
      case 3:
        return <InviteTeamStep />;
      case 4:
        return <SettingsStep />;
      case 5:
        return <CompletionStep />;
      default:
        return <WelcomeStep />;
    }
  };

  // Get step action button
  const getStepAction = () => {
    switch (currentStep) {
      case 2:
        return handleUpdateCompanyProfile;
      case 3:
        return handleInviteTeam;
      default:
        return handleNextStep;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Progress Bar */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-700">
              Setup Progress
            </h3>
            <span className="text-sm text-gray-500">
              Step {currentStep} of {totalSteps}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-gradient-to-r from-indigo-600 to-purple-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${(currentStep / totalSteps) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {renderStep()}

        {/* Navigation Buttons */}
        {currentStep < 5 && (
          <div className="flex justify-between items-center max-w-3xl mx-auto mt-12">
            <button
              onClick={handlePrevStep}
              disabled={currentStep === 1}
              className="inline-flex items-center gap-2 px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ArrowLeft className="w-4 h-4" />
              Previous
            </button>

            <button
              onClick={getStepAction()}
              disabled={loading}
              className="inline-flex items-center gap-2 px-8 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading
                ? "Processing..."
                : currentStep === totalSteps - 1
                  ? "Complete Setup"
                  : "Next"}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrganizationSetupWizard;
