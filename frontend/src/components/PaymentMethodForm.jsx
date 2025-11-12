import React, { useState } from 'react';
import { CreditCard, Lock, AlertCircle } from 'lucide-react';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  CardElement,
  useStripe,
  useElements
} from '@stripe/react-stripe-js';
import { useToast } from '../hooks/useToast';
import paymentAPI from '../services/paymentAPI';

// Load Stripe publishable key from environment
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || 'pk_test_placeholder');

/**
 * Card Input Component
 *
 * Collects payment method using Stripe Elements
 */
const CardInputForm = ({ onSuccess, tierName, isLoading: parentLoading }) => {
  const stripe = useStripe();
  const elements = useElements();
  const { success, error: showError } = useToast();

  const [loading, setLoading] = useState(false);
  const [cardComplete, setCardComplete] = useState(false);
  const [cardError, setCardError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!stripe || !elements || !cardComplete) {
      return;
    }

    setLoading(true);
    setCardError(null);

    try {
      // Create setup intent
      const { client_secret } = await paymentAPI.createSetupIntent();

      // Confirm card setup
      const { setupIntent, error: stripeError } = await stripe.confirmCardSetup(
        client_secret,
        {
          payment_method: {
            card: elements.getElement(CardElement),
          },
        }
      );

      if (stripeError) {
        setCardError(stripeError.message);
        showError(stripeError.message);
        setLoading(false);
        return;
      }

      // Create subscription with payment method
      await paymentAPI.createSubscription(tierName, setupIntent.payment_method);
      success('Payment method added and subscription created!');

      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      console.error('Payment error:', err);
      setCardError(err.response?.data?.detail || 'Failed to process payment');
      showError(err.response?.data?.detail || 'Failed to process payment');
    } finally {
      setLoading(false);
    }
  };

  const cardStyle = {
    style: {
      base: {
        fontSize: '16px',
        color: '#1f2937',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        '::placeholder': {
          color: '#9ca3af',
        },
      },
      invalid: {
        color: '#ef4444',
      },
    },
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Card Information
        </label>
        <div className="border border-gray-300 rounded-md p-3 bg-white">
          <CardElement
            options={cardStyle}
            onChange={(e) => {
              setCardComplete(e.complete);
              setCardError(e.error?.message || null);
            }}
          />
        </div>
        {cardError && (
          <div className="mt-2 flex items-center text-sm text-red-600">
            <AlertCircle className="w-4 h-4 mr-1" />
            {cardError}
          </div>
        )}
      </div>

      <div className="flex items-center text-sm text-gray-600 bg-gray-50 p-3 rounded-md">
        <Lock className="w-4 h-4 mr-2" />
        <span>Your payment information is encrypted and secure</span>
      </div>

      <button
        type="submit"
        disabled={!stripe || !cardComplete || loading || parentLoading}
        className="w-full bg-blue-600 text-white px-4 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
      >
        {loading ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
            Processing...
          </>
        ) : (
          <>
            <CreditCard className="w-5 h-5 mr-2" />
            Subscribe to {tierName}
          </>
        )}
      </button>
    </form>
  );
};

/**
 * Payment Method Form Component
 *
 * Main wrapper that provides Stripe Elements context
 */
const PaymentMethodForm = ({ onSuccess, tierName, isLoading }) => {
  return (
    <Elements stripe={stripePromise}>
      <CardInputForm
        onSuccess={onSuccess}
        tierName={tierName}
        isLoading={isLoading}
      />
    </Elements>
  );
};

export default PaymentMethodForm;
