import unittest
from rest_framework.exceptions import ValidationError
from dashboard.utils.utils import CustomValidators, NormalizeData

class CustomValidatorsTests(unittest.TestCase):

    def setUp(self):
        self.validator = CustomValidators()

    def test_validate_phone_number(self):
        valid_numbers = [
            '0712345678',         # Local Kenyan number
            '+254712345678',      # International format with +
            '254712345678',       # International format without +
            '1234567890',         # Generic number
            '+1234567890',        # Generic number with +
            '44712345678',        # UK number without +
            '+44712345678',       # UK number with +
        ]
        
        for number in valid_numbers:
            try:
                result = self.validator.validate_phone_number(number)
                expected = number.strip()
                self.assertEqual(result, expected,
                                 f"Validator didn't return the expected number for {number}")
            except ValidationError:
                self.fail(f"ValidationError raised for valid number: {number}")

    def test_validate_phone_number_none(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_phone_number(None)

class NormalizeDataTests(unittest.TestCase):

    def setUp(self):
        self.normalizer = NormalizeData()

    def test_normalize_phone_number(self):
        test_cases = {
            '0712345678': '+254712345678',    # Kenyan number with 0 prefix
            '712345678': '+254712345678',     # Kenyan number without prefix
            '254712345678': '+254712345678',  # Kenyan number with 254 prefix
            '+254712345678': '+254712345678', # Kenyan number with +254 prefix
            '1234567890': '+1234567890',      # US number without + (should add +)
            '+1234567890': '+1234567890',     # US number with + (should remain unchanged)
            '44712345678': '+44712345678',    # UK number without + (should add +)
            '+44712345678': '+44712345678',   # UK number with + (should remain unchanged)
            '91987654321': '+91987654321',    # Indian number without + (should add +)
            '+91987654321': '+91987654321',   # Indian number with + (should remain unchanged)
            '12345': '12345'                  # Invalid number (should remain unchanged)
        }
        for input_number, expected_output in test_cases.items():
            self.assertEqual(self.normalizer.normalize_phone_number(input_number), expected_output,
                             f"Failed for input: {input_number}")

if __name__ == '__main__':
    unittest.main()
