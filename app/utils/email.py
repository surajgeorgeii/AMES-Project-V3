from flask import current_app
from flask_mail import Message
from extensions import mail
from datetime import datetime
from jinja2 import Template

def send_reminder_email(recipient_email, modules_info):
    """
    Send a reminder email to module leads about pending module reviews
    
    Args:
        recipient_email (str): The email address of the module lead
        modules_info (list): List of dictionaries containing module details
                           [{'code': 'ABC123', 'name': 'Module Name'}, ...]
    """
    try:
        # Email template using Jinja2 for better formatting
        template = Template("""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f5f5f5; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h2 style="color: #1a73e8; margin: 0; padding-bottom: 15px; font-size: 24px; border-bottom: 2px solid #e0e0e0;">
                        Module Review Reminder
                    </h2>
                </div>
                
                <p style="color: #424242; font-size: 16px;">Dear Module Lead,</p>
                
                <p style="color: #424242; font-size: 16px;">This is a friendly reminder that the following module(s) are pending review:</p>
                
                <div style="margin: 25px 0;">
                    {% for module in modules %}
                    <div style="margin: 15px 0; padding: 15px; background-color: #f8f9fa; border-radius: 6px; border-left: 4px solid #1a73e8; transition: all 0.3s ease;">
                        <div style="font-size: 18px; font-weight: 600; color: #1a73e8;">{{ module.code }}</div>
                        <div style="color: #616161; margin-top: 5px;">{{ module.name }}</div>
                    </div>
                    {% endfor %}
                </div>
                
                <p style="color: #424242; font-size: 16px; background-color: #e3f2fd; padding: 15px; border-radius: 6px; margin: 20px 0;">
                    Please complete the module review(s) at your earliest convenience. 
                    The review process is essential for maintaining academic quality and planning improvements.
                </p>
                
                <div style="margin-top: 30px; padding: 20px; background-color: #f5f5f5; border-radius: 6px;">
                    <p style="color: #424242; font-size: 16px; margin-top: 0;">To complete the review(s), please:</p>
                    <ol style="color: #424242; font-size: 16px; padding-left: 20px;">
                        <li style="margin-bottom: 10px;">Log in to the Module Review System</li>
                        <li style="margin-bottom: 10px;">Navigate to your pending reviews</li>
                        <li style="margin-bottom: 10px;">Complete the review form for each module</li>
                    </ol>
                </div>
                
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{{ system_url }}" 
                       style="display: inline-block; background-color: #1a73e8; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 25px; font-weight: 500; font-size: 16px;
                              transition: background-color 0.3s ease;">
                        Access Module Review System
                    </a>
                </div>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                    <p style="color: #757575; font-size: 14px; text-align: center; margin: 0;">
                        This is an automated message. If you have any questions, please contact the system administrator.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """)

        # Render the template with the module data
        html_content = template.render(
            modules=modules_info,
            system_url=f"{current_app.config['SYSTEM_URL']}/auth/login",
            current_year=datetime.now().year
        )

        # Create the email message
        msg = Message(
            subject='Action Required: Pending Module Reviews',
            recipients=[recipient_email],
            html=html_content,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )

        # Send the email
        mail.send(msg)
        
        # Log the email sending
        current_app.logger.info(f"Reminder email sent to {recipient_email} for {len(modules_info)} modules")
        
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to send reminder email to {recipient_email}: {str(e)}")
        raise

def send_custom_email(recipient_email, subject, message, sender_email):
    """
    Send a custom email to a user
    
    Args:
        recipient_email (str): The email address of the recipient
        subject (str): Email subject
        message (str): Email message content
        sender_email (str): The email address of the sender
    """
    try:
        # Email template using Jinja2 for formatting
        template = Template("""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f5f5f5; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h2 style="color: #1a73e8; margin: 0; padding-bottom: 15px; font-size: 24px; border-bottom: 2px solid #e0e0e0;">
                        {{ subject }}
                    </h2>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 6px; border-left: 4px solid #1a73e8; margin: 25px 0;">
                    <div style="color: #424242; font-size: 16px;">
                        {{ message | safe }}
                    </div>
                </div>
                
                <div style="margin-top: 30px; padding: 20px; background-color: #f5f5f5; border-radius: 6px;">
                    <p style="color: #666; font-size: 14px; margin-top: 0;">
                        This email was sent by {{ sender_email }} via the Module Review System.
                    </p>
                </div>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                    <p style="color: #757575; font-size: 14px; text-align: center; margin: 0;">
                        © {{ current_year }} Module Review System. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """)

        # Render the template
        html_content = template.render(
            subject=subject,
            message=message,
            sender_email=sender_email,
            current_year=datetime.now().year
        )

        # Create the email message
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            html=html_content,
            sender=sender_email
        )

        # Send the email
        mail.send(msg)
        
        # Log the email sending
        current_app.logger.info(f"Custom email sent from {sender_email} to {recipient_email}")
        
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to send custom email to {recipient_email}: {str(e)}")
        raise
