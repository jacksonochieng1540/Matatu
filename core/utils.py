# core/utils.py

import requests
import base64
import json
from datetime import datetime
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import qrcode
from io import BytesIO
from django.core.files import File
import logging

logger = logging.getLogger(__name__)

# ============================================
# M-Pesa Integration
# ============================================

def get_mpesa_access_token():
    """Get M-Pesa access token"""
    try:
        api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        if settings.MPESA_CONFIG['ENVIRONMENT'] == 'production':
            api_url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        
        consumer_key = settings.MPESA_CONFIG['CONSUMER_KEY']
        consumer_secret = settings.MPESA_CONFIG['CONSUMER_SECRET']
        
        response = requests.get(
            api_url,
            auth=(consumer_key, consumer_secret),
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            logger.error(f"M-Pesa token error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"M-Pesa token exception: {str(e)}")
        return None


def initiate_mpesa_payment(booking, phone_number):
    """Initiate M-Pesa STK Push"""
    try:
        access_token = get_mpesa_access_token()
        if not access_token:
            return {'success': False, 'message': 'Failed to get access token'}
        
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        if settings.MPESA_CONFIG['ENVIRONMENT'] == 'production':
            api_url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        business_short_code = settings.MPESA_CONFIG['SHORTCODE']
        passkey = settings.MPESA_CONFIG['PASSKEY']
        
        # Generate password
        data_to_encode = business_short_code + passkey + timestamp
        password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
        
        # Ensure phone number is in correct format
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+254'):
            phone_number = phone_number[1:]
        elif not phone_number.startswith('254'):
            phone_number = '254' + phone_number
        
        payload = {
            'BusinessShortCode': business_short_code,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(booking.total_fare),
            'PartyA': phone_number,
            'PartyB': business_short_code,
            'PhoneNumber': phone_number,
            'CallBackURL': settings.MPESA_CONFIG['CALLBACK_URL'],
            'AccountReference': booking.booking_reference,
            'TransactionDesc': f'Booking {booking.booking_reference}'
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ResponseCode') == '0':
            return {
                'success': True,
                'message': 'STK Push sent successfully',
                'transaction_id': response_data.get('CheckoutRequestID'),
                'checkout_request_id': response_data.get('CheckoutRequestID')
            }
        else:
            return {
                'success': False,
                'message': response_data.get('errorMessage', 'Payment initiation failed')
            }
    
    except Exception as e:
        logger.error(f"M-Pesa STK Push error: {str(e)}")
        return {'success': False, 'message': str(e)}


def query_mpesa_transaction(checkout_request_id):
    """Query M-Pesa transaction status"""
    try:
        access_token = get_mpesa_access_token()
        if not access_token:
            return None
        
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"
        if settings.MPESA_CONFIG['ENVIRONMENT'] == 'production':
            api_url = "https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        business_short_code = settings.MPESA_CONFIG['SHORTCODE']
        passkey = settings.MPESA_CONFIG['PASSKEY']
        
        data_to_encode = business_short_code + passkey + timestamp
        password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
        
        payload = {
            'BusinessShortCode': business_short_code,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        return response.json()
    
    except Exception as e:
        logger.error(f"M-Pesa query error: {str(e)}")
        return None


def process_mpesa_callback(callback_data):
    """Process M-Pesa callback data"""
    try:
        result_code = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
        checkout_request_id = callback_data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
        
        from .models import Payment
        
        try:
            payment = Payment.objects.get(checkout_request_id=checkout_request_id)
            
            if result_code == 0:
                # Payment successful
                callback_metadata = callback_data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [])
                
                mpesa_receipt = None
                phone_number = None
                amount = None
                
                for item in callback_metadata:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        mpesa_receipt = item.get('Value')
                    elif item.get('Name') == 'PhoneNumber':
                        phone_number = item.get('Value')
                    elif item.get('Name') == 'Amount':
                        amount = item.get('Value')
                
                payment.status = 'completed'
                payment.mpesa_receipt = mpesa_receipt
                payment.response_code = str(result_code)
                payment.paid_at = datetime.now()
                payment.save()
                
                # Update booking status
                booking = payment.booking
                booking.status = 'confirmed'
                booking.payment_method = 'mpesa'
                booking.save()
                
                # Update seat bookings
                booking.seat_bookings.update(status='booked')
                
                # Generate QR code
                generate_booking_qr_code(booking)
                
                # Send confirmation SMS and email
                send_booking_confirmation(booking)
                
                return {'success': True, 'message': 'Payment processed successfully'}
            else:
                # Payment failed
                payment.status = 'failed'
                payment.response_code = str(result_code)
                payment.response_message = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultDesc', '')
                payment.save()
                
                # Release seats and update booking
                booking = payment.booking
                booking.status = 'cancelled'
                booking.save()
                booking.seat_bookings.update(status='available')
                booking.trip.available_seats += booking.number_of_seats
                booking.trip.save()
                
                return {'success': False, 'message': 'Payment failed'}
        
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for checkout request: {checkout_request_id}")
            return {'success': False, 'message': 'Payment not found'}
    
    except Exception as e:
        logger.error(f"Callback processing error: {str(e)}")
        return {'success': False, 'message': str(e)}


# ============================================
# SMS Functions (Africa's Talking)
# ============================================

def send_sms(phone_number, message):
    """Send SMS via Africa's Talking"""
    try:
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '+254' + phone_number[1:]
        elif not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        api_url = "https://api.sandbox.africastalking.com/version1/messaging"
        if settings.AT_CONFIG['USERNAME'] != 'sandbox':
            api_url = "https://api.africastalking.com/version1/messaging"
        
        headers = {
            'apiKey': settings.AT_CONFIG['API_KEY'],
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'username': settings.AT_CONFIG['USERNAME'],
            'to': phone_number,
            'message': message,
            'from': settings.AT_CONFIG.get('SENDER_ID', '')
        }
        
        response = requests.post(api_url, data=data, headers=headers, timeout=30)
        
        # Log SMS
        from .models import SMSLog
        SMSLog.objects.create(
            recipient=phone_number,
            message=message,
            status='sent' if response.status_code == 200 else 'failed',
            response=response.text
        )
        
        return response.status_code == 200
    
    except Exception as e:
        logger.error(f"SMS sending error: {str(e)}")
        return False


# ============================================
# Email Functions
# ============================================

def send_email_notification(subject, recipient, template_name, context):
    """Send email notification"""
    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False
        )
        
        # Log email
        from .models import EmailLog
        EmailLog.objects.create(
            recipient=recipient,
            subject=subject,
            message=plain_message,
            status='sent'
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Email sending error: {str(e)}")
        from .models import EmailLog
        EmailLog.objects.create(
            recipient=recipient,
            subject=subject,
            message=plain_message,
            status='failed',
            error=str(e)
        )
        return False


# ============================================
# QR Code Generation
# ============================================

def generate_booking_qr_code(booking):
    """Generate QR code for booking"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # QR code data
        qr_data = f"BOOKING:{booking.booking_reference}|TRIP:{booking.trip.id}|SEATS:{booking.number_of_seats}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Save to booking
        filename = f'qr_{booking.booking_reference}.png'
        booking.qr_code.save(filename, File(buffer), save=True)
        
        return True
    
    except Exception as e:
        logger.error(f"QR code generation error: {str(e)}")
        return False


# ============================================
# Notification Functions
# ============================================

def send_booking_confirmation(booking):
    """Send booking confirmation via SMS and email"""
    try:
        # SMS
        sms_message = (
            f"Booking confirmed! Ref: {booking.booking_reference}\n"
            f"Trip: {booking.trip.route.name}\n"
            f"Date: {booking.trip.departure_date} at {booking.trip.departure_time}\n"
            f"Seats: {booking.number_of_seats}\n"
            f"Total: KES {booking.total_fare}\n"
            f"Show this reference at the terminal."
        )
        send_sms(booking.passenger_phone, sms_message)
        
        # Email
        if booking.passenger_email:
            context = {
                'booking': booking,
                'trip': booking.trip,
            }
            send_email_notification(
                subject=f'Booking Confirmation - {booking.booking_reference}',
                recipient=booking.passenger_email,
                template_name='emails/booking_confirmation.html',
                context=context
            )
        
        # Create in-app notification
        from .models import Notification
        Notification.objects.create(
            user=booking.customer,
            type='booking',
            title='Booking Confirmed',
            message=f'Your booking {booking.booking_reference} has been confirmed.',
            link=f'/bookings/{booking.pk}/'
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Booking confirmation error: {str(e)}")
        return False


def send_trip_reminder(booking):
    """Send trip reminder 24 hours before departure"""
    try:
        sms_message = (
            f"Trip Reminder!\n"
            f"Ref: {booking.booking_reference}\n"
            f"Route: {booking.trip.route.name}\n"
            f"Tomorrow at {booking.trip.departure_time}\n"
            f"Boarding: {booking.boarding_point.name}\n"
            f"Have a safe journey!"
        )
        send_sms(booking.passenger_phone, sms_message)
        
        return True
    
    except Exception as e:
        logger.error(f"Trip reminder error: {str(e)}")
        return False


# ============================================
# Utility Functions
# ============================================

def generate_verification_code():
    """Generate 6-digit verification code"""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def format_phone_number(phone):
    """Format phone number to Kenya standard"""
    phone = str(phone).strip()
    if phone.startswith('0'):
        return '+254' + phone[1:]
    elif phone.startswith('254'):
        return '+' + phone
    elif phone.startswith('+254'):
        return phone
    else:
        return '+254' + phone


def calculate_refund_amount(booking):
    """Calculate refund amount based on cancellation time"""
    from django.utils import timezone
    
    now = timezone.now()
    departure = timezone.make_aware(
        timezone.datetime.combine(booking.trip.departure_date, booking.trip.departure_time)
    )
    
    hours_remaining = (departure - now).total_seconds() / 3600
    
    if hours_remaining >= 24:
        return booking.total_fare * 0.9  # 90% refund
    elif hours_remaining >= 12:
        return booking.total_fare * 0.7  # 70% refund
    elif hours_remaining >= 2:
        return booking.total_fare * 0.5  # 50% refund
    else:
        return 0  # No refund


def get_available_seats(trip):
    """Get list of available seats for a trip"""
    from .models import SeatBooking
    
    occupied = SeatBooking.objects.filter(
        trip=trip,
        status__in=['held', 'booked']
    ).values_list('seat_id', flat=True)
    
    available = trip.vehicle.seats.exclude(id__in=occupied)
    return available

# ============================================
# QR Code Generation
# ============================================

def generate_qr_code(data, filename=None):
    """Generate QR code from data and return BytesIO object"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer
    
    except Exception as e:
        logger.error(f"QR code generation error: {str(e)}")
        return None

def generate_booking_qr_code(booking):
    """Generate QR code for booking and save to model"""
    try:
        qr_data = f"BOOKING:{booking.booking_reference}|TRIP:{booking.trip.id}|SEATS:{booking.number_of_seats}"
        buffer = generate_qr_code(qr_data)
        
        if buffer:
            filename = f'qr_{booking.booking_reference}.png'
            booking.qr_code.save(filename, File(buffer), save=True)
            return True
        return False
    
    except Exception as e:
        logger.error(f"Booking QR code generation error: {str(e)}")
        return False