import os
import csv
import pandas as pd
import logging
from io import TextIOWrapper
from django.utils import timezone
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from django.conf import settings

logger = logging.getLogger(__name__)

def send_sms(to_phone_number, message):
    """
    Send SMS using Twilio's API
    Returns: (success, message)
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.error("Twilio credentials not configured")
        return False, "Twilio credentials not configured"
    
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Sending the SMS message
        twilio_message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
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


def send_whatsapp(to_phone_number, message):
    """
    Send WhatsApp message using Twilio's WhatsApp API
    Returns: (success, message)
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.error("Twilio credentials not configured")
        return False, "Twilio credentials not configured"
    
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Format phone number for WhatsApp (WhatsApp requires "whatsapp:" prefix)
        if not to_phone_number.startswith('whatsapp:'):
            whatsapp_number = f"whatsapp:{to_phone_number}"
        else:
            whatsapp_number = to_phone_number
        
        # Sending WhatsApp message via Twilio
        whatsapp_message = client.messages.create(
            body=message,
            from_=f"whatsapp:{settings.TWILIO_PHONE_NUMBER.replace('+', '')}",
            to=whatsapp_number
        )
        
        logger.info(f"WhatsApp message sent with SID: {whatsapp_message.sid}")
        return True, f"Message sent with SID: {whatsapp_message.sid}"
    
    except TwilioRestException as e:
        error_message = f"Twilio error: {e.code} - {e.msg}"
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Error sending WhatsApp message: {str(e)}"
        logger.error(error_message)
        return False, error_message


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
                
                # Optional fields with defaults
                email = str(row.get('email', '')).strip()
                gender = str(row.get('gender', '')).strip().upper()[:1]  # Get first letter
                if gender not in ['M', 'F', 'O']:
                    gender = ''
                
                # Validate required fields
                if not first_name or not last_name or not phone_number:
                    continue
                
                # Get or create location
                location_name = str(row.get('location_name', '')).strip()
                city = str(row.get('city', '')).strip()
                state = str(row.get('state', '')).strip()
                country = str(row.get('country', 'Kenya')).strip()
                
                if location_name and city:
                    location, _ = Location.objects.get_or_create(
                        name=location_name,
                        city=city,
                        defaults={'state': state, 'country': country}
                    )
                else:
                    location = None
                
                # Get notification preference
                notification_pref = str(row.get('notification_preference', 'BOTH')).strip().upper()
                if notification_pref not in ['SMS', 'WA', 'BOTH', 'NONE']:
                    notification_pref = 'BOTH'
                
                # Parse date of birth if provided
                dob = row.get('date_of_birth', None)
                if pd.isna(dob):
                    dob = None
                
                # Try to find existing patient by phone number
                patient = Patient.objects.filter(phone_number=phone_number).first()
                
                if patient and update_existing:
                    # Update existing patient
                    patient.first_name = first_name
                    patient.last_name = last_name
                    patient.email = email
                    patient.gender = gender if gender else patient.gender
                    if dob:
                        patient.date_of_birth = dob
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
                        email=email,
                        gender=gender,
                        date_of_birth=dob,
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
