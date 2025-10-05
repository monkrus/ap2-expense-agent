"""
Stripe Setup Script
Automates creation of Stripe products and prices for AP2 Expense Agent

Run this script ONCE after creating your Stripe account to set up subscription tiers.

Usage:
    python scripts/setup_stripe.py
"""
import stripe
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe.api_key or stripe.api_key == "sk_test_your_stripe_secret_key_here":
    print("❌ Error: Please set STRIPE_SECRET_KEY in your .env file")
    print("   Get your API key from: https://dashboard.stripe.com/apikeys")
    sys.exit(1)


def create_product_and_price(name, description, price_monthly, features):
    """Create a Stripe product and recurring price"""
    try:
        print(f"\n📦 Creating product: {name}")

        # Create product
        product = stripe.Product.create(
            name=name,
            description=description,
            metadata={
                "features": ", ".join(features[:5])  # First 5 features
            }
        )

        print(f"   ✅ Product created: {product.id}")

        # Create price
        price = stripe.Price.create(
            product=product.id,
            currency="usd",
            unit_amount=int(price_monthly * 100),  # Convert to cents
            recurring={"interval": "month"}
        )

        print(f"   ✅ Price created: {price.id}")
        print(f"   💰 Amount: ${price_monthly}/month")

        return {
            "product_id": product.id,
            "price_id": price.id,
            "amount": price_monthly
        }

    except stripe.error.StripeError as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def main():
    print("=" * 70)
    print("🚀 AP2 Expense Agent - Stripe Setup")
    print("=" * 70)
    print("\nThis script will create 3 subscription products in your Stripe account:")
    print("  1. Starter Plan - $29/month")
    print("  2. Professional Plan - $99/month")
    print("  3. Enterprise Plan - $399/month")
    print("\nMake sure you're using TEST mode for testing!")
    print("=" * 70)

    response = input("\n⚠️  Continue? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Cancelled.")
        sys.exit(0)

    # Define subscription tiers
    tiers = [
        {
            "name": "AP2 Expense Agent - Starter",
            "description": "Perfect for small teams (10-25 users)",
            "price": 29.00,
            "features": [
                "Up to 25 users",
                "100 expense submissions/month",
                "Basic receipt OCR",
                "AI categorization (500/month)",
                "30-day data retention",
                "Standard support"
            ]
        },
        {
            "name": "AP2 Expense Agent - Professional",
            "description": "Best for growing companies (25-100 users)",
            "price": 99.00,
            "features": [
                "Up to 100 users",
                "Unlimited expense submissions",
                "Advanced receipt OCR",
                "AI categorization (5,000/month)",
                "AP2 automated payments (100/month)",
                "Custom approval workflows",
                "90-day data retention",
                "Priority support"
            ]
        },
        {
            "name": "AP2 Expense Agent - Enterprise",
            "description": "For large organizations (100-500 users)",
            "price": 399.00,
            "features": [
                "Up to 500 users",
                "Unlimited everything",
                "Unlimited AI categorization",
                "Unlimited AP2 transactions",
                "Custom integrations",
                "SSO/SAML authentication",
                "365-day data retention",
                "Dedicated support",
                "SLA guarantee (99.9%)"
            ]
        }
    ]

    results = {}

    # Create products and prices
    for idx, tier in enumerate(tiers):
        result = create_product_and_price(
            name=tier["name"],
            description=tier["description"],
            price_monthly=tier["price"],
            features=tier["features"]
        )

        if result:
            tier_name = ["starter", "professional", "enterprise"][idx]
            results[tier_name] = result

    # Print summary
    print("\n" + "=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)

    if results:
        print("\n📝 Add these to your .env file:")
        print("-" * 70)

        if "starter" in results:
            print(f"STRIPE_PRICE_ID_STARTER={results['starter']['price_id']}")

        if "professional" in results:
            print(f"STRIPE_PRICE_ID_PROFESSIONAL={results['professional']['price_id']}")

        if "enterprise" in results:
            print(f"STRIPE_PRICE_ID_ENTERPRISE={results['enterprise']['price_id']}")

        print("-" * 70)

        print("\n🔗 View in Stripe Dashboard:")
        print("   https://dashboard.stripe.com/products")

        print("\n📋 Next Steps:")
        print("   1. Copy the STRIPE_PRICE_ID values above to your .env file")
        print("   2. Create a webhook endpoint in Stripe Dashboard:")
        print("      https://dashboard.stripe.com/webhooks")
        print("   3. Add webhook URL: https://your-domain.com/webhooks/stripe")
        print("   4. Select these events:")
        print("      - payment_intent.succeeded")
        print("      - payment_intent.payment_failed")
        print("      - customer.subscription.created")
        print("      - customer.subscription.updated")
        print("      - customer.subscription.deleted")
        print("      - invoice.paid")
        print("      - invoice.payment_failed")
        print("   5. Copy the webhook signing secret to STRIPE_WEBHOOK_SECRET in .env")
        print("   6. Set ENABLE_BILLING=true in .env")
        print("   7. Restart your application")

        print("\n💡 Tip: Test payments using Stripe test cards:")
        print("   Success: 4242 4242 4242 4242")
        print("   Decline: 4000 0000 0000 0002")
        print("   https://stripe.com/docs/testing")

    else:
        print("\n❌ No products were created. Check the errors above.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
