"""
AI service for receipt OCR and data extraction using Google Gemini Vision.
"""

import base64
import json
import logging
from typing import Dict, Optional, List
from pathlib import Path

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from ..config import settings

logger = logging.getLogger(__name__)


class ReceiptAIService:
    """Service for AI-powered receipt analysis and data extraction"""

    def __init__(self):
        self.model = None
        if GENAI_AVAILABLE and settings.google_api_key:
            try:
                genai.configure(api_key=settings.google_api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                logger.info("Gemini AI model initialized for receipt processing")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini AI: {e}")
                self.model = None

    async def extract_receipt_data(self, file_path: str) -> Dict:
        """
        Extract data from receipt image using Gemini Vision AI.

        Args:
            file_path: Path to receipt image file

        Returns:
            Dictionary with extracted data: vendor, amount, date, category, items
        """
        if not self.model:
            logger.warning("AI model not available, returning empty extraction")
            return self._fallback_extraction(file_path)

        try:
            # Read image file
            with open(file_path, 'rb') as f:
                image_data = f.read()

            # Encode to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Create prompt for receipt extraction
            prompt = """
            Analyze this receipt image and extract the following information in JSON format:

            {
                "vendor": "merchant/vendor name",
                "amount": total amount as float,
                "date": "date in YYYY-MM-DD format",
                "category": "one of: Travel, Meals, Software, Office Supplies, Other",
                "description": "brief description of purchase",
                "items": [
                    {"name": "item name", "amount": item amount as float}
                ],
                "currency": "currency code (USD, EUR, etc.)",
                "tax": tax amount as float or null,
                "confidence": "high/medium/low based on image quality"
            }

            Important:
            - Extract exact amounts from the receipt
            - Use the total amount including tax if visible
            - Categorize based on the vendor and items purchased
            - Return ONLY valid JSON, no markdown or explanation
            - If you cannot read something clearly, use null
            - For date, try to infer year if only month/day shown
            """

            # Get file extension to determine image type
            file_ext = Path(file_path).suffix.lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.bmp': 'image/bmp'
            }.get(file_ext, 'image/jpeg')

            # Generate content with vision
            response = self.model.generate_content([
                prompt,
                {
                    'mime_type': mime_type,
                    'data': image_base64
                }
            ])

            # Parse response
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                # Extract JSON from markdown code block
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            extracted_data = json.loads(response_text)

            # Validate and clean extracted data
            extracted_data = self._validate_extraction(extracted_data)

            logger.info(f"Successfully extracted data from receipt: {file_path}")
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response text: {response_text if 'response_text' in locals() else 'N/A'}")
            return self._fallback_extraction(file_path)
        except Exception as e:
            logger.error(f"Failed to extract receipt data: {e}", exc_info=True)
            return self._fallback_extraction(file_path)

    async def batch_extract_receipts(self, file_paths: List[str]) -> List[Dict]:
        """
        Extract data from multiple receipts in batch.

        Args:
            file_paths: List of paths to receipt image files

        Returns:
            List of dictionaries with extracted data
        """
        results = []
        for file_path in file_paths:
            try:
                extraction = await self.extract_receipt_data(file_path)
                extraction['file_path'] = file_path
                extraction['file_name'] = Path(file_path).name
                results.append(extraction)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                # Add failed result
                results.append({
                    'file_path': file_path,
                    'file_name': Path(file_path).name,
                    'error': str(e),
                    'confidence': 'failed'
                })

        return results

    def _validate_extraction(self, data: Dict) -> Dict:
        """
        Validate and clean extracted data.

        Args:
            data: Extracted data dictionary

        Returns:
            Validated and cleaned data
        """
        # Ensure required fields exist
        cleaned = {
            'vendor': data.get('vendor', 'Unknown Vendor'),
            'amount': self._parse_amount(data.get('amount')),
            'date': data.get('date'),
            'category': self._validate_category(data.get('category', 'Other')),
            'description': data.get('description', ''),
            'items': data.get('items', []),
            'currency': data.get('currency', 'USD'),
            'tax': self._parse_amount(data.get('tax')),
            'confidence': data.get('confidence', 'medium')
        }

        # Generate description if empty
        if not cleaned['description']:
            if cleaned['items']:
                item_names = [item.get('name', '') for item in cleaned['items'][:3]]
                cleaned['description'] = f"Purchase from {cleaned['vendor']}: {', '.join(filter(None, item_names))}"
            else:
                cleaned['description'] = f"Purchase from {cleaned['vendor']}"

        return cleaned

    def _parse_amount(self, amount) -> Optional[float]:
        """Parse amount to float"""
        if amount is None or amount == '':
            return None
        try:
            # Handle string amounts with currency symbols
            if isinstance(amount, str):
                amount = amount.replace('$', '').replace(',', '').strip()
            return float(amount)
        except (ValueError, TypeError):
            return None

    def _validate_category(self, category: str) -> str:
        """Validate category against allowed values"""
        valid_categories = ['Travel', 'Meals', 'Software', 'Office Supplies', 'Other']
        if category in valid_categories:
            return category

        # Try to match case-insensitively
        category_lower = category.lower()
        for valid_cat in valid_categories:
            if valid_cat.lower() == category_lower:
                return valid_cat

        # Default to Other
        return 'Other'

    def _fallback_extraction(self, file_path: str) -> Dict:
        """
        Fallback extraction when AI is not available.

        Returns:
            Basic extraction with defaults
        """
        return {
            'vendor': 'Unknown Vendor',
            'amount': None,
            'date': None,
            'category': 'Other',
            'description': 'Receipt upload - manual review required',
            'items': [],
            'currency': 'USD',
            'tax': None,
            'confidence': 'low',
            'ai_available': False
        }


# Global singleton instance
_receipt_ai_service: Optional[ReceiptAIService] = None


def get_receipt_ai_service() -> ReceiptAIService:
    """Get or create the global ReceiptAIService instance"""
    global _receipt_ai_service
    if _receipt_ai_service is None:
        _receipt_ai_service = ReceiptAIService()
    return _receipt_ai_service
