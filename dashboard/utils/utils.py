import re
from rest_framework.exceptions import ValidationError

class CustomValidators:
    def validate_phone_number(self, phone_number):
        """Validate phone number is of required format."""
        if not phone_number:
            raise ValidationError("Phone number cannot be empty.")
        
        # Remove any whitespace
        phone_number = phone_number.strip()
        
        # Define the patterns
        patterns = [
            r'^\d{9}$',           # Format: XXXXXXXXX (Kenyan number without prefix)
            r'^0\d{9}$',           # Format: 0XXXXXXXXX (Kenyan number with 0 as prefix)
            r'^\+\d{1,4}\d{9}$',   # Format: +CCXXXXXXXXX (1-4 digit country code)
            r'^\d{1,4}\d{9}$'      # Format: CCXXXXXXXXX (1-4 digit country code without +)
        ]
        
        # Check if the number matches any of the patterns
        if not any(re.match(pattern, phone_number) for pattern in patterns):
            raise ValidationError("Invalid phone number format. Use 0XXXXXXXXX, +CCXXXXXXXXX, or CCXXXXXXXXX, where CC is the country code.")
        
        # Check if number starts with 0 but is not exactly 10 digits
        if phone_number.startswith('0') and len(phone_number) != 10:
            raise ValidationError("Invalid phone number format. Local phone numbers starting with 0 should be exactly 10 digits.")
        
        # Additional check for reasonable total length
        if len(phone_number) > 15:  # Maximum length for international numbers according to ITU-T recommendation E.164
            raise ValidationError("Phone number is too long. Maximum allowed length is 15 digits.")
        
        return phone_number  # Return the cleaned phone number

class NormalizeData():
    def normalize_phone_number(self, phone_number):
        """Normalize phone number to match the international format with a '+' sign"""
        if not phone_number:
            return phone_number
        
        # Remove any whitespace
        phone_number = phone_number.strip()
        
        # Validate the phone number first
        validator = CustomValidators()
        try:
            validator.validate_phone_number(phone_number)
        except ValidationError:
            return phone_number  # Return unchanged if validation fails
        
        # Pattern for Kenyan numbers (assuming 0 or 254 prefix)
        kenyan_pattern = r'^(?:0|\+?254)?(\d{9})$'
        
        # Apply Kenyan normalization
        match = re.match(kenyan_pattern, phone_number)
        if match:
            return f'+254{match.group(1)}'
        
        # For other numbers, ensure they start with a '+'
        if not phone_number.startswith('+'):
            phone_number = f'+{phone_number}'
        
        return phone_number
