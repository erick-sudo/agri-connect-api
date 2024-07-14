from django.core.mail import EmailMessage, send_mail, mail_admins
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
import logging
from django.utils import timezone
from dashboard.models import CustomUser as User
import time
import threading

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Define threading function
def threaded(fn):
    def wrapper(*args, **kwargs):
        logger.info(f"Starting thread for {fn.__name__} with args: {args} kwargs: {kwargs}")
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
    return wrapper

@threaded
def send_welcome_email(first_name, email):
    logger.info(f"send_welcome_email started for {email}")
    subject = 'Welcome to Our Platform'
    context = {
        'first_name': str.capitalize(first_name),
        'login_url': 'https://agriconnectke.com/login',
        'support_email': 'info@agriconnectke.com'
    }
    
    html_message = render_to_string('emails/welcome_email.html', context)
    plain_message = strip_tags(html_message)  # Create a plain-text version
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]

    for attempt in range(MAX_RETRIES):
        try:
            send_mail(subject, plain_message, from_email, recipient_list, fail_silently=False, html_message=html_message)
            logger.info(f"Welcome email sent successfully to {email}")
            send_admin_email("Welcome Email Sent", html_message, recipient_list)
            return
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                logger.critical(f"Welcome email sending failed for {email} after all retries")
            time.sleep(RETRY_DELAY)

    logger.info(f"send_welcome_email completed for {email}")

@threaded
def send_password_reset_email(user_id, token):
    logger.info(f"send_password_reset_email started for user_id: {user_id}")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} does not exist.")
        return

    subject = 'Password Reset Request'
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_url = f"{settings.FRONTEND_URL}/accounts/reset-password/{uid}/{token}/"
    
    context = {
        'reset_url': reset_url,
        'user': user,
    }
    
    html_message = render_to_string('emails/password_reset.html', context)
    plain_message = strip_tags(html_message)
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    for attempt in range(MAX_RETRIES):
        try:
            send_mail(subject, plain_message, from_email, recipient_list, fail_silently=False, html_message=html_message)
            logger.info(f"Password reset email sent successfully to {user.email}")
            send_admin_email("Password Reset Email Sent", html_message, recipient_list)
            return
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                logger.critical(f"Failed to send password reset email to {user.email} after all retries")
            time.sleep(RETRY_DELAY)

    logger.info(f"send_password_reset_email completed for user_id: {user_id}")

@threaded
def send_password_change_success_email(user_id):
    logger.info(f"send_password_change_success_email started for user_id: {user_id}")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} does not exist.")
        return

    subject = 'Your Password Has Been Changed'
    context = {
        'user': user,
    }
    
    html_message = render_to_string('emails/password_change_success.html', context)
    plain_message = strip_tags(html_message)
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    for attempt in range(MAX_RETRIES):
        try:
            send_mail(subject, plain_message, from_email, recipient_list, fail_silently=False, html_message=html_message)
            logger.info(f"Password change success email sent successfully to {user.email}")
            send_admin_email("Password Change Success Email Sent", html_message, recipient_list)
            return
        except Exception as e:
            logger.error(f"Failed to send password change success email to {user.email}: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                logger.critical(f"Failed to send password change success email to {user.email} after all retries")
            time.sleep(RETRY_DELAY)

    logger.info(f"send_password_change_success_email completed for user_id: {user_id}")

@threaded
def send_email(from_email, recipient, subject, message, attachment_paths=None, html_message=None):
    logger.info(f"send_email started for {recipient}")
    """
    Sends an email with optional HTML content and attachments.

    :param from_email: The sender's email address.
    :param recipient: The recipient's email address.
    :param subject: The subject of the email.
    :param message: The plain text message content of the email.
    :param attachment_paths: List of file paths for attachments.
    :param html_message: Optional HTML content for the email.
    """
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email,
        to=[recipient]
    )

    if html_message:
        email.content_subtype = 'html'  # Set the email content type to HTML

    if attachment_paths:
        for path in attachment_paths:
            try:
                email.attach_file(path)
            except Exception as e:
                logger.error(f"Failed to attach file {path}: {str(e)}")
                raise

    for attempt in range(MAX_RETRIES):
        try:
            email.send()
            logger.info(f"Email sent successfully to {recipient}")
            return
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                logger.critical(f"Email sending failed to {recipient} after all retries")
            time.sleep(RETRY_DELAY)

    logger.info(f"send_email completed for {recipient}")

def send_admin_email(event_type, message, recipient_list):
    logger.info(f"send_admin_email started for event_type: {event_type}")
    subject = f"Admin Notification: {event_type}"
    context = {
        "recipient": recipient_list,
        "subject": subject,
        "message": message,
        "event_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    html_message = render_to_string('emails/admin_notification.html', context)
    plain_message = strip_tags(html_message)

    for attempt in range(MAX_RETRIES):
        try:
            mail_admins(subject, plain_message, fail_silently=False, html_message=html_message)
            logger.info(f"Admin email notification sent successfully for event {event_type}")
            return
        except Exception as e:
            logger.error(f"Failed to send admin email: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                logger.critical(f"Admin email failed after all retries for event {event_type}")
            time.sleep(RETRY_DELAY)

    logger.info(f"send_admin_email completed for event_type: {event_type}")
