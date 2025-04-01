import os
import csv
import pandas as pd
import requests
import logging
from io import TextIOWrapper
from django.utils import timezone
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from django.conf import settings
from well_patient.settings import WHATSAPP_API_KEY,TWILIO_PHONE_NUMBER,WHATSAPP_PHONE_NUMBER_ID,TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN
from heyoo import WhatsApp
logger = logging.getLogger(__name__)

messenger = WhatsApp(WHATSAPP_API_KEY,  phone_number_id=WHATSAPP_PHONE_NUMBER_ID)
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_sms(to_phone_number, message):
    """
    Send SMS using Twilio's API
    Returns: (success, message)
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.error("Twilio credentials not configured")
        return False, "Twilio credentials not configured"
    
    try:
        
        
        # Sending the SMS message
        twilio_message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone_number
        )
        
        logger.info(f"SMS sent with SID: {twilio_message.sid}")
        return True, f"Message sent with SID: {twilio_message.sid}"
    
    except TwilioRestException as e:
        error_message = f"Twilio error: {e.code} - {e.msg}"
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Error sending SMS: {str(e)}"
        logger.error(error_message)
        return False, error_message


from whatsapp import WhatsApp
import logging

logger = logging.getLogger(__name__)

def format_phone_number(phone_number):
    """
    Format phone number to ensure it has the correct Zimbabwe country code (263).
    Args:
        phone_number (str): The phone number to format
    Returns:
        str: Formatted phone number with country code (without +)
    Raises:
        ValueError: If phone number is invalid
    """
    if not phone_number:
        raise ValueError("Phone number cannot be empty")
    
    # Remove all non-digit characters
    cleaned_number = ''.join(c for c in phone_number if c.isdigit())
    
    if not cleaned_number:
        raise ValueError("Invalid phone number format")
    
    # Check if number already has country code
    if cleaned_number.startswith("263"):
        if len(cleaned_number) == 12:  # 263 + 9 digits
            return cleaned_number
        raise ValueError("Invalid Zimbabwean phone number length")
    
    # Handle local numbers starting with 0
    if cleaned_number.startswith("0"):
        if len(cleaned_number) == 10:  # 0 + 9 digits
            return "263" + cleaned_number[1:]
        raise ValueError("Invalid local phone number length")
    
    # Handle numbers missing both 0 and country code
    if len(cleaned_number) == 9:  # Just the 9 digits
        return "263" + cleaned_number
    
    raise ValueError("Unrecognized phone number format")

def get_whatsapp_headers():
    """
    Build and return headers for WhatsApp API requests.
    Returns:
        dict: Headers for API requests
    """
    return {
        "Authorization": f"Bearer {WHATSAPP_API_KEY}",
        "Content-Type": "application/json",
    }

def send_whatsapp(recipient_id, message_text):
    """
    Send a text message to the specified recipient using the WhatsApp API.
    Args:
        recipient_id (str): The recipient's phone number
        message_text (str): The message content to send
    Returns:
        dict: API response or error information
    """
    try:
        # Format the recipient's phone number
        formatted_number = format_phone_number(recipient_id)
        
        url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = get_whatsapp_headers()
        
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": formatted_number,
            "type": "text",
            "text": {
                "preview_url": False,  # Disable link previews by default
                "body": message_text
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()  # Will raise HTTPError for 4XX/5XX responses
        
        logger.info(f"Successfully sent message to {recipient_id}")
        print(f"Successfully sent message to {recipient_id}")
        return response.json()
        
    except requests.exceptions.Timeout:
        error_msg = f"Timeout error sending message to {recipient_id}"
        logger.error(error_msg)
        print(error_msg)
        return {"error": error_msg}
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed for {recipient_id}: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return {"error": error_msg}
    except ValueError as e:
        error_msg = f"Invalid phone number {recipient_id}: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error sending to {recipient_id}: {str(e)}"
        logger.exception(error_msg)
        print(error_msg)
        return {"error": error_msg}

def process_import_file(file, update_existing=True):
    """
    Process an imported CSV or Excel file with patient data
    """
    from .models import Patient, Location
    
    extension = file.name.split('.')[-1].lower()
    result = {'created': 0, 'updated': 0, 'errors': 0}
    
    try:
        # Read file based on extension
        if extension == 'csv':
            # Wrap the file with TextIOWrapper to handle text encoding
            csv_file = TextIOWrapper(file, encoding='utf-8')
            df = pd.read_csv(csv_file)
        elif extension in ['xls', 'xlsx']:
            df = pd.read_excel(file)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
        
        # Process each row
        for _, row in df.iterrows():
            try:
                # Required fields
                first_name = str(row.get('first_name', '')).strip()
                last_name = str(row.get('last_name', '')).strip()
                phone_number = str(row.get('phone_number', '')).strip()
                
                
                # Validate required fields
                if not first_name or not last_name or not phone_number:
                    continue
                
                # Get or create location
                location_name = str(row.get('location_name', '')).strip()
                city = str(row.get('city', '')).strip()
                
                if location_name and city:
                    location, _ = Location.objects.get_or_create(
                        name=location_name,
                        city=city
                    )
                else:
                    location = None
                
                # Get notification preference
                notification_pref = str(row.get('notification_preference', 'BOTH')).strip().upper()
                if notification_pref not in ['SMS', 'WA', 'BOTH', 'NONE']:
                    notification_pref = 'BOTH'
                
                # Try to find existing patient by phone number
                patient = Patient.objects.filter(phone_number=phone_number).first()
                
                if patient and update_existing:
                    # Update existing patient
                    patient.first_name = first_name
                    patient.last_name = last_name
                    if location:
                        patient.location = location
                    patient.notification_preference = notification_pref
                    patient.save()
                    result['updated'] += 1
                elif not patient:
                    # Create new patient
                    Patient.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        phone_number=phone_number,
                        location=location,
                        notification_preference=notification_pref
                    )
                    result['created'] += 1
            
            except Exception as e:
                logger.error(f"Error processing row: {str(e)}")
                result['errors'] += 1
        
        return result
    
    except Exception as e:
        logger.error(f"Error processing import file: {str(e)}")
        raise
