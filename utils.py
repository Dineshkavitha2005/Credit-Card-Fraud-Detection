"""
Utility functions for security, email, and geolocation
"""

import smtplib
import os
import io
import csv
import requests
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session

logger = logging.getLogger(__name__)

# ─── Email Service ──────────────────────────────────────────────────

class EmailService:
    """Handle email notifications"""
    
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'noreply@fraudshield.com')
    SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
    
    @classmethod
    def send_email(cls, recipient_email, subject, html_content, text_content=None):
        """Send email via SMTP"""
        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = cls.SENDER_EMAIL
            message['To'] = recipient_email
            
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                message.attach(part1)
            
            part2 = MIMEText(html_content, 'html')
            message.attach(part2)
            
            with smtplib.SMTP(cls.SMTP_SERVER, cls.SMTP_PORT) as server:
                server.starttls()
                server.login(cls.SENDER_EMAIL, cls.SENDER_PASSWORD)
                server.send_message(message)
            
            logger.info(f"Email sent to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"Email send failed: {str(e)}")
            return False
    
    @classmethod
    def send_verification_email(cls, user_email, verification_token, user_name):
        """Send email verification link"""
        link = f"http://localhost:5000/verify-email/{verification_token}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Welcome to FraudShield, {user_name}!</h2>
                <p>Please verify your email address to activate your account.</p>
                <p><a href="{link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                    Verify Email Address
                </a></p>
                <p>Or copy this link: <code>{link}</code></p>
                <p>This link expires in 7 days.</p>
                <hr>
                <p style="color: #999; font-size: 12px;">
                    If you didn't create this account, please ignore this email.
                </p>
            </body>
        </html>
        """
        return cls.send_email(user_email, "Verify Your FraudShield Account", html_content)
    
    @classmethod
    def send_password_reset_email(cls, user_email, reset_token, user_name):
        """Send password reset link"""
        link = f"http://localhost:5000/reset-password/{reset_token}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Password Reset Request</h2>
                <p>Hi {user_name},</p>
                <p>We received a request to reset your password. Click the link below to proceed:</p>
                <p><a href="{link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                    Reset Password
                </a></p>
                <p>Or copy this link: <code>{link}</code></p>
                <p>This link expires in 24 hours.</p>
                <hr>
                <p style="color: #999; font-size: 12px;">
                    If you didn't request this, please ignore this email and your password will remain unchanged.
                </p>
            </body>
        </html>
        """
        return cls.send_email(user_email, "Reset Your FraudShield Password", html_content)
    
    @classmethod
    def send_fraud_alert(cls, user_email, user_name, transaction_data, fraud_score):
        """Send fraud alert notification"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #d32f2f;">⚠️ Suspicious Transaction Alert</h2>
                <p>Hi {user_name},</p>
                <p>We detected a suspicious transaction on your account. Here are the details:</p>
                
                <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
                    <p><strong>Merchant:</strong> {transaction_data.get('merchant', 'N/A')}</p>
                    <p><strong>Amount:</strong> ${transaction_data.get('amount', '0.00')}</p>
                    <p><strong>Location:</strong> {transaction_data.get('location', 'Unknown')}</p>
                    <p><strong>Risk Score:</strong> <span style="color: #d32f2f; font-weight: bold;">{fraud_score}%</span></p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <p><a href="http://localhost:5000/transactions" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                    Review Transaction
                </a></p>
                
                <p style="color: #999; font-size: 12px;">
                    If this was you, you can ignore this alert. If not, please contact our support team immediately.
                </p>
            </body>
        </html>
        """
        return cls.send_email(user_email, f"Suspicious Transaction Alert - Risk Score {fraud_score}%", html_content)
    
    @classmethod
    def send_login_alert(cls, user_email, user_name, ip_address, location, device):
        """Send login from new device/location alert"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>New Login Detected</h2>
                <p>Hi {user_name},</p>
                <p>Your account was accessed from a new device or location:</p>
                
                <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
                    <p><strong>IP Address:</strong> {ip_address}</p>
                    <p><strong>Location:</strong> {location}</p>
                    <p><strong>Device:</strong> {device}</p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <p>If this was you, no action is needed. If you don't recognize this login, please change your password immediately.</p>
                
                <p><a href="http://localhost:5000/settings" style="background-color: #FF9800; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                    Change Password
                </a></p>
            </body>
        </html>
        """
        return cls.send_email(user_email, "New Login Detected on Your Account", html_content)
    
    @classmethod
    def send_password_changed_email(cls, user_email, user_name):
        """Send password change confirmation"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Password Changed</h2>
                <p style="color: #4CAF50;">✓ Your password has been successfully changed.</p>
                <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>If you didn't make this change, please contact us immediately.</p>
            </body>
        </html>
        """
        return cls.send_email(user_email, "Your FraudShield Password Has Been Changed", html_content)


# ─── Geolocation Service ────────────────────────────────────────────

class GeolocationService:
    """Get geolocation data from IP address"""
    
    @staticmethod
    def get_geo_data(ip_address):
        """Get geolocation info for IP address"""
        if ip_address in ['127.0.0.1', 'localhost', '::1']:
            return {
                'ip': ip_address,
                'country': 'Local',
                'city': 'Local',
                'latitude': 0,
                'longitude': 0,
                'isp': 'Local'
            }
        
        try:
            # Using ip-api.com free service
            response = requests.get(f'http://ip-api.com/json/{ip_address}?fields=status,country,city,lat,lon,isp', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'ip': ip_address,
                        'country': data.get('country'),
                        'city': data.get('city'),
                        'latitude': data.get('lat'),
                        'longitude': data.get('lon'),
                        'isp': data.get('isp'),
                        'is_vpn': False,
                        'is_proxy': False,
                        'is_tor': False
                    }
        except Exception as e:
            logger.error(f"Geolocation lookup failed: {str(e)}")
        
        return {
            'ip': ip_address,
            'country': 'Unknown',
            'city': 'Unknown',
            'latitude': 0,
            'longitude': 0,
            'isp': 'Unknown'
        }


# ─── Security & Validation ────────────────────────────────────────

class SecurityHelper:
    """Security-related helper functions"""
    
    @staticmethod
    def is_suspicious_login(user, ip_address, current_location):
        """Check if login is suspicious based on location/IP"""
        from models import IPAddress, LoginAttempt
        
        # Check if IP is known to user
        known_ip = IPAddress.query.filter_by(user_id=user.id, ip_address=ip_address).first()
        
        # Check login history
        recent_logins = LoginAttempt.query.filter(
            LoginAttempt.username == user.username,
            LoginAttempt.success == True,
            LoginAttempt.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).all()
        
        # Determine suspicion score
        suspicion_score = 0
        reasons = []
        
        if not known_ip:
            suspicion_score += 30
            reasons.append("New IP address")
        
        if recent_logins:
            # Check distance between recent logins
            last_login = recent_logins[-1]
            if last_login.country and last_login.country != current_location.get('country'):
                suspicion_score += 40
                reasons.append("Geographic anomaly")
        
        is_suspicious = suspicion_score > 50
        
        return {
            'is_suspicious': is_suspicious,
            'suspicion_score': suspicion_score,
            'reasons': reasons
        }
    
    @staticmethod
    def check_password_strength(password):
        """Validate password strength"""
        score = 0
        feedback = []
        
        if len(password) >= 8:
            score += 1
        else:
            feedback.append("Password must be at least 8 characters")
        
        if len(password) >= 12:
            score += 1
        
        if any(c.isupper() for c in password):
            score += 1
        else:
            feedback.append("Include uppercase letters")
        
        if any(c.islower() for c in password):
            score += 1
        else:
            feedback.append("Include lowercase letters")
        
        if any(c.isdigit() for c in password):
            score += 1
        else:
            feedback.append("Include numbers")
        
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            score += 1
        else:
            feedback.append("Include special characters")
        
        strength = 'weak' if score < 3 else 'fair' if score < 4 else 'good' if score < 5 else 'strong'
        
        return {
            'strength': strength,
            'score': score,
            'feedback': feedback,
            'is_valid': score >= 3
        }
    
    @staticmethod
    def is_rate_limited(identifier, endpoint, limit=5, window=60):
        """Check if identifier exceeded rate limit"""
        from flask import current_app
        if current_app and current_app.testing:
            return False

        from models import RateLimitRecord, db
        
        now = datetime.utcnow()
        record = RateLimitRecord.query.filter_by(
            identifier=identifier,
            endpoint=endpoint
        ).first()
        
        if not record:
            record = RateLimitRecord(identifier=identifier, endpoint=endpoint, request_count=1)
            db.session.add(record)
            db.session.commit()
            return False
        
        # Check if window expired
        if (now - record.first_request).seconds > window:
            record.request_count = 1
            record.first_request = now
            record.last_request = now
            record.is_limited = False
            db.session.commit()
            return False
        
        record.request_count += 1
        record.last_request = now
        record.is_limited = record.request_count > limit
        db.session.commit()
        
        return record.is_limited

    @staticmethod
    def reset_rate_limit(identifier, endpoint):
        """Reset rate limit record for identifier and endpoint"""
        from models import RateLimitRecord, db
        try:
            record = RateLimitRecord.query.filter_by(
                identifier=identifier,
                endpoint=endpoint
            ).first()
            if record:
                record.request_count = 0
                record.is_limited = False
                db.session.commit()
        except Exception:
            pass


# ─── Decorators ────────────────────────────────────────────────────

def require_email_verified(f):
    """Decorator to require email verification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        if not current_user.is_verified:
            return jsonify({'error': 'Email verification required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(limit=5, window=60):
    """Decorator for rate limiting API endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = request.remote_addr
            endpoint = request.endpoint
            
            if SecurityHelper.is_rate_limited(identifier, endpoint, limit, window):
                return jsonify({'error': 'Too many requests. Please try again later.'}), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_activity(activity_type, resource_type=None, resource_id=None):
    """Decorator to log user activities"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            from models import UserActivity, db
            
            try:
                result = f(*args, **kwargs)
                
                if current_user.is_authenticated:
                    activity = UserActivity(
                        user_id=current_user.id,
                        activity_type=activity_type,
                        action_description=f.__name__,
                        ip_address=request.remote_addr,
                        user_agent=request.user_agent.string,
                        resource_type=resource_type,
                        resource_id=str(resource_id),
                        status='success'
                    )
                    db.session.add(activity)
                    db.session.commit()
                
                return result
            except Exception as e:
                if current_user.is_authenticated:
                    activity = UserActivity(
                        user_id=current_user.id,
                        activity_type=activity_type,
                        action_description=f.__name__,
                        ip_address=request.remote_addr,
                        user_agent=request.user_agent.string,
                        resource_type=resource_type,
                        resource_id=str(resource_id),
                        status='failure',
                        error_message=str(e)
                    )
                    db.session.add(activity)
                    db.session.commit()
                raise
        
        return decorated_function
    return decorator


# ─── Report Generator ─────────────────────────────────────────────

class ReportGenerator:
    """Generate PDF and CSV reports with strict data safety and formatting"""

    @staticmethod
    def _get_field(obj, key, default=None):
        """Safely retrieve field value from dict or model object"""
        if isinstance(obj, dict):
            val = obj.get(key, default)
        else:
            val = getattr(obj, key, default)
        return default if val is None else val

    @classmethod
    def calculate_metrics(cls, transactions):
        """Calculate summary metrics for a list of transaction dicts or model objects"""
        total_txns = len(transactions)
        
        def is_t_fraud(t):
            is_f = cls._get_field(t, 'is_fraud', False)
            score = float(cls._get_field(t, 'fraud_score', 0) or 0)
            return bool(is_f) or score >= 0.7 or score >= 50.0

        fraud_txns = [t for t in transactions if is_t_fraud(t)]
        genuine_txns = [t for t in transactions if not is_t_fraud(t)]
        
        fraud_count = len(fraud_txns)
        genuine_count = len(genuine_txns)
        fraud_pct = (fraud_count / total_txns * 100.0) if total_txns > 0 else 0.0
        
        total_amount = sum(float(cls._get_field(t, 'amount', 0) or 0) for t in transactions)
        fraud_amount = sum(float(cls._get_field(t, 'amount', 0) or 0) for t in fraud_txns)
        genuine_amount = sum(float(cls._get_field(t, 'amount', 0) or 0) for t in genuine_txns)
        
        high_risk_txns = [t for t in transactions if float(cls._get_field(t, 'fraud_score', 0) or 0) >= 0.7]
        high_risk_count = len(high_risk_txns)
        
        return {
            'total_transactions': total_txns,
            'genuine_transactions': genuine_count,
            'fraudulent_transactions': fraud_count,
            'fraud_percentage': round(fraud_pct, 2),
            'total_amount': round(total_amount, 2),
            'fraud_amount': round(fraud_amount, 2),
            'genuine_amount': round(genuine_amount, 2),
            'high_risk_transactions': high_risk_count,
            'high_risk_list': high_risk_txns
        }

    @classmethod
    def generate_csv(cls, transactions, output_path=None):
        """Generate safe CSV transaction report with masked card numbers"""
        import io
        import csv
        from app.models.encryption import mask_card_number

        headers = [
            'Transaction ID', 'Timestamp', 'User ID', 'Card Number', 'Card Holder',
            'Amount ($)', 'Merchant', 'Category', 'Location', 'Status',
            'Fraud Score', 'Is Fraud', 'IP Address', 'Device Type'
        ]

        rows = []
        for t in transactions:
            ts = cls._get_field(t, 'timestamp')
            if isinstance(ts, datetime):
                ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
            else:
                ts_str = str(ts or '')

            rows.append([
                cls._get_field(t, 'transaction_id', ''),
                ts_str,
                cls._get_field(t, 'user_id', ''),
                mask_card_number(cls._get_field(t, 'card_number', '')),
                cls._get_field(t, 'card_holder', ''),
                f"{float(cls._get_field(t, 'amount', 0) or 0):.2f}",
                cls._get_field(t, 'merchant', ''),
                cls._get_field(t, 'category', ''),
                cls._get_field(t, 'location', ''),
                cls._get_field(t, 'status', ''),
                f"{float(cls._get_field(t, 'fraud_score', 0) or 0):.4f}",
                'Yes' if cls._get_field(t, 'is_fraud') else 'No',
                cls._get_field(t, 'ip_address', ''),
                cls._get_field(t, 'device_type', '')
            ])

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            return output_path
        else:
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(headers)
            writer.writerows(rows)
            return buffer.getvalue().encode('utf-8')

    @classmethod
    def generate_pdf(cls, report_type, title, transactions, filters=None, output_path=None):
        """Generate PDF report using ReportLab"""
        import io
        from app.models.encryption import mask_card_number
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfgen import canvas

        metrics = cls.calculate_metrics(transactions)

        class NumberedCanvas(canvas.Canvas):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._saved_page_states = []

            def showPage(self):
                self._saved_page_states.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                num_pages = len(self._saved_page_states)
                for state in self._saved_page_states:
                    self.__dict__.update(state)
                    self.draw_page_number(num_pages)
                    canvas.Canvas.showPage(self)
                canvas.Canvas.save(self)

            def draw_page_number(self, page_count):
                self.saveState()
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#64748b"))
                
                # Header bar on page 2+
                if self._pageNumber > 1:
                    self.setStrokeColor(colors.HexColor("#e2e8f0"))
                    self.setLineWidth(0.5)
                    self.line(36, 11 * inch - 36, 8.5 * inch - 36, 11 * inch - 36)
                    self.drawString(36, 11 * inch - 30, "FraudShield Security & Transaction Report")
                
                # Footer bar
                self.setStrokeColor(colors.HexColor("#cbd5e1"))
                self.setLineWidth(0.5)
                self.line(36, 40, 8.5 * inch - 36, 40)
                
                page_str = f"Page {self._pageNumber} of {page_count}"
                self.drawRightString(8.5 * inch - 36, 26, page_str)
                self.drawString(36, 26, f"FraudShield Systems • Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} • Strictly Confidential")
                self.restoreState()

        buffer = io.BytesIO() if not output_path else None
        doc = SimpleDocTemplate(
            output_path if output_path else buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=45,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=12
        )
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=14,
            spaceAfter=8
        )
        cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#334155')
        )
        cell_bold = ParagraphStyle(
            'TableCellBold',
            parent=cell_style,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0f172a')
        )
        header_cell = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.white
        )
        badge_fraud = ParagraphStyle(
            'BadgeFraud',
            parent=cell_style,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#dc2626')
        )
        badge_safe = ParagraphStyle(
            'BadgeSafe',
            parent=cell_style,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#16a34a')
        )

        story = []

        # 1. Header Banner
        banner_data = [
            [
                Paragraph("<b>FRAUDSHIELD REPORTING SYSTEM</b>", ParagraphStyle('B1', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#6366f1'))),
                Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ParagraphStyle('B2', fontName='Helvetica', fontSize=9, alignment=2, textColor=colors.HexColor('#475569')))
            ]
        ]
        banner_table = Table(banner_data, colWidths=[3.5*inch, 4.0*inch])
        banner_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 6))

        # 2. Main Title
        story.append(Paragraph(title, title_style))

        # Filter info line
        filter_str = "Filters Applied: "
        if filters:
            f_parts = []
            if filters.get('date_from') or filters.get('date_to'):
                f_parts.append(f"Date: {filters.get('date_from', 'Start')} to {filters.get('date_to', 'End')}")
            if filters.get('fraud_status') and filters.get('fraud_status') != 'all':
                f_parts.append(f"Status: {filters.get('fraud_status')}")
            if filters.get('risk_level') and filters.get('risk_level') != 'all':
                f_parts.append(f"Risk: {filters.get('risk_level')}")
            if filters.get('min_amount') or filters.get('max_amount'):
                f_parts.append(f"Amount: ${filters.get('min_amount', '0')} - ${filters.get('max_amount', 'Max')}")
            if filters.get('user_id'):
                f_parts.append(f"User ID: {filters.get('user_id')}")
            filter_str += ", ".join(f_parts) if f_parts else "All Records (No Filters)"
        else:
            filter_str += "All Records (No Filters)"

        story.append(Paragraph(filter_str, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=0, spaceAfter=12))

        # 3. KPI Summary Table / Metric Cards
        story.append(Paragraph("Executive Metrics Summary", section_style))

        kpi_data = [
            [
                Paragraph("<b>Total Transactions</b>", cell_style),
                Paragraph("<b>Genuine Transactions</b>", cell_style),
                Paragraph("<b>Fraudulent Transactions</b>", cell_style),
                Paragraph("<b>Fraud Rate</b>", cell_style)
            ],
            [
                Paragraph(f"<font size=12><b>{metrics['total_transactions']}</b></font>", cell_bold),
                Paragraph(f"<font size=12 color='#16a34a'><b>{metrics['genuine_transactions']}</b></font>", cell_bold),
                Paragraph(f"<font size=12 color='#dc2626'><b>{metrics['fraudulent_transactions']}</b></font>", cell_bold),
                Paragraph(f"<font size=12 color='#d97706'><b>{metrics['fraud_percentage']}%</b></font>", cell_bold)
            ],
            [
                Paragraph("<b>Total Volume</b>", cell_style),
                Paragraph("<b>Genuine Volume</b>", cell_style),
                Paragraph("<b>Fraud Volume</b>", cell_style),
                Paragraph("<b>High-Risk Transactions</b>", cell_style)
            ],
            [
                Paragraph(f"<font size=12><b>${metrics['total_amount']:,.2f}</b></font>", cell_bold),
                Paragraph(f"<font size=12 color='#16a34a'><b>${metrics['genuine_amount']:,.2f}</b></font>", cell_bold),
                Paragraph(f"<font size=12 color='#dc2626'><b>${metrics['fraud_amount']:,.2f}</b></font>", cell_bold),
                Paragraph(f"<font size=12 color='#dc2626'><b>{metrics['high_risk_transactions']}</b></font>", cell_bold)
            ]
        ]

        kpi_table = Table(kpi_data, colWidths=[1.875*inch, 1.875*inch, 1.875*inch, 1.875*inch])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 14))

        # 4. Report Specific Content
        if report_type == 'fraud_analysis_report':
            story.append(Paragraph("Fraud Analysis & High-Risk Transaction Breakdown", section_style))
            
            # High risk breakdown summary table
            hr_rows = [
                [Paragraph("Transaction ID", header_cell), Paragraph("Card Number", header_cell), Paragraph("Amount", header_cell), Paragraph("Merchant", header_cell), Paragraph("Risk Score", header_cell), Paragraph("Status", header_cell)]
            ]
            for t in metrics['high_risk_list'][:15]: # Top 15 high risk
                score = float(cls._get_field(t, 'fraud_score', 0) or 0)
                hr_rows.append([
                    Paragraph(str(cls._get_field(t, 'transaction_id', '')), cell_style),
                    Paragraph(mask_card_number(cls._get_field(t, 'card_number', '')), cell_style),
                    Paragraph(f"${float(cls._get_field(t, 'amount', 0) or 0):,.2f}", cell_bold),
                    Paragraph(str(cls._get_field(t, 'merchant', '')), cell_style),
                    Paragraph(f"<b>{score:.2f}</b>", badge_fraud),
                    Paragraph(str(cls._get_field(t, 'status', 'Flagged')).title(), badge_fraud if cls._get_field(t, 'is_fraud') else cell_style)
                ])

            if len(hr_rows) > 1:
                hr_table = Table(hr_rows, colWidths=[1.4*inch, 1.4*inch, 1.0*inch, 1.5*inch, 1.0*inch, 1.2*inch])
                hr_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7f1d1d')),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#fca5a5')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fef2f2')]),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ]))
                story.append(hr_table)
            else:
                story.append(Paragraph("<i>No high-risk fraudulent transactions found for the selected filters.</i>", cell_style))

            story.append(Spacer(1, 14))

        # 5. Transactions Table
        story.append(Paragraph("Transaction Detail Table", section_style))

        txn_rows = [
            [
                Paragraph("Txn ID", header_cell),
                Paragraph("Date/Time", header_cell),
                Paragraph("Card Number", header_cell),
                Paragraph("Amount", header_cell),
                Paragraph("Merchant", header_cell),
                Paragraph("Risk Score", header_cell),
                Paragraph("Fraud?", header_cell)
            ]
        ]

        # Display max 100 rows in PDF to keep page count reasonable
        display_txns = transactions[:100]
        for t in display_txns:
            ts = cls._get_field(t, 'timestamp')
            ts_str = ts.strftime('%m-%d %H:%M') if isinstance(ts, datetime) else str(ts or '')[:11]
            is_f = cls._get_field(t, 'is_fraud') or float(cls._get_field(t, 'fraud_score', 0) or 0) >= 0.7
            
            txn_rows.append([
                Paragraph(str(cls._get_field(t, 'transaction_id', '')), cell_style),
                Paragraph(ts_str, cell_style),
                Paragraph(mask_card_number(cls._get_field(t, 'card_number', '')), cell_style),
                Paragraph(f"${float(cls._get_field(t, 'amount', 0) or 0):,.2f}", cell_bold),
                Paragraph(str(cls._get_field(t, 'merchant', ''))[:20], cell_style),
                Paragraph(f"{float(cls._get_field(t, 'fraud_score', 0) or 0):.2f}", badge_fraud if is_f else cell_style),
                Paragraph("<b>FRAUD</b>" if is_f else "Safe", badge_fraud if is_f else badge_safe)
            ])

        if len(txn_rows) > 1:
            txn_table = Table(txn_rows, colWidths=[1.3*inch, 1.0*inch, 1.5*inch, 0.9*inch, 1.4*inch, 0.7*inch, 0.7*inch])
            txn_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(txn_table)
            
            if len(transactions) > 100:
                story.append(Spacer(1, 6))
                story.append(Paragraph(f"<i>Showing first 100 transactions of {len(transactions)} total records. Export CSV report for complete dataset.</i>", subtitle_style))
        else:
            story.append(Paragraph("<i>No transaction records match the specified filters.</i>", cell_style))

        # Build document
        doc.build(story, canvasmaker=NumberedCanvas)

        if output_path:
            return output_path
        else:
            return buffer.getvalue()

