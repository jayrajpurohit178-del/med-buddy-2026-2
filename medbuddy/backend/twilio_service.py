from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

def send_sms(to_number: str, message: str):
    try:
        msg = client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=to_number
        )
        return {"status": "sent", "sid": msg.sid}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def send_whatsapp(to_number: str, message: str):
    try:
        msg = client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
            to=f"whatsapp:{to_number}"
        )
        return {"status": "sent", "sid": msg.sid}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def send_medication_reminder(phone: str, whatsapp: str, medicine: str, dosage: str, timing: str):
    message = f"MedBuddy Reminder: Time to take {medicine} - {dosage} ({timing}). Stay healthy!"
    results = {}
    if phone:
        results["sms"] = send_sms(phone, message)
    if whatsapp:
        results["whatsapp"] = send_whatsapp(whatsapp, message)
    return results