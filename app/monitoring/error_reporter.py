"""
Error Reporting System mit Notifications
"""
import json
import smtplib
import time
from typing import Dict, List, Optional, Any
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from collections import defaultdict, deque
from threading import Lock
from pathlib import Path
from .logger import get_logger

class ErrorReporter:
    """Error Reporting mit Rate Limiting und Notifications"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = get_logger('error_reporter')

        # Error Tracking
        self.error_counts = defaultdict(int)
        self.error_history = defaultdict(lambda: deque(maxlen=100))
        self.last_notification = {}
        self.lock = Lock()

        # Rate Limiting für Notifications
        self.notification_cooldown = self.config.get('notification_cooldown', 300)  # 5 min
        self.max_errors_per_hour = self.config.get('max_errors_per_hour', 10)

        # Email-Konfiguration
        self.smtp_config = self.config.get('smtp', {})
        self.notification_emails = self.config.get('notification_emails', [])

    def report_error(self, error_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Meldet einen Fehler und entscheidet über Notification"""
        current_time = time.time()

        with self.lock:
            # Aktualisiere Error-Statistiken
            self.error_counts[error_type] += 1
            self.error_history[error_type].append({
                'timestamp': current_time,
                'message': message,
                'context': context or {}
            })

            # Prüfe ob Notification gesendet werden soll
            if self._should_notify(error_type, current_time):
                self._send_notification(error_type, message, context)
                self.last_notification[error_type] = current_time

        # Logge den Fehler
        self.logger.error(f"Error reported: {error_type}",
                         error_type=error_type,
                         message=message,
                         context=context,
                         total_count=self.error_counts[error_type])

    def _should_notify(self, error_type: str, current_time: float) -> bool:
        """Entscheidet ob eine Notification gesendet werden soll"""
        # Prüfe Cooldown
        last_notification = self.last_notification.get(error_type, 0)
        if current_time - last_notification < self.notification_cooldown:
            return False

        # Prüfe Error-Rate
        hour_ago = current_time - 3600
        recent_errors = [
            error for error in self.error_history[error_type]
            if error['timestamp'] > hour_ago
        ]

        if len(recent_errors) >= self.max_errors_per_hour:
            return True

        # Kritische Errors sofort melden
        critical_types = ['authentication_failure', 'data_corruption', 'service_unavailable']
        if error_type in critical_types:
            return True

        return False

    def _send_notification(self, error_type: str, message: str, context: Optional[Dict[str, Any]]):
        """Sendet Notification per Email oder andere Channels"""
        if not self.notification_emails or not self.smtp_config:
            self.logger.warning("Notification requested but no email config available")
            return

        try:
            # Email-Inhalt erstellen
            subject = f"[ERROR] Document Sorter: {error_type}"
            body = self._create_email_body(error_type, message, context)

            # Email senden
            self._send_email(subject, body)

            self.logger.info("Error notification sent",
                           error_type=error_type,
                           notification_method='email')

        except Exception as e:
            self.logger.error("Failed to send error notification",
                            error_type=error_type,
                            exception=e)

    def _create_email_body(self, error_type: str, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Erstellt Email-Body für Error-Notification"""
        recent_count = len(self.error_history[error_type])
        total_count = self.error_counts[error_type]

        body = f"""
Error Alert - Document Sorter Application

Error Type: {error_type}
Message: {message}
Total Occurrences: {total_count}
Recent Occurrences (last 100): {recent_count}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}

Context:
{json.dumps(context or {}, indent=2)}

Recent Error History:
"""
        # Zeige letzte 5 Errors
        for error in list(self.error_history[error_type])[-5:]:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S UTC',
                                    time.gmtime(error['timestamp']))
            body += f"\n- {timestamp}: {error['message']}"

        body += f"""

System Information:
- Application: Document Sorter
- Environment: {self.config.get('environment', 'production')}
- Version: {self.config.get('version', 'unknown')}

Please investigate this issue promptly.
"""
        return body

    def _send_email(self, subject: str, body: str):
        """Sendet Email über SMTP"""
        smtp_host = self.smtp_config.get('host')
        smtp_port = self.smtp_config.get('port', 587)
        smtp_user = self.smtp_config.get('username')
        smtp_pass = self.smtp_config.get('password')
        from_email = self.smtp_config.get('from_email', smtp_user)

        if not all([smtp_host, smtp_user, smtp_pass]):
            raise ValueError("Incomplete SMTP configuration")

        # Email erstellen
        msg = MimeMultipart()
        msg['From'] = from_email
        msg['To'] = ', '.join(self.notification_emails)
        msg['Subject'] = subject
        msg.attach(MimeText(body, 'plain'))

        # Email senden
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

    def get_error_statistics(self) -> Dict[str, Any]:
        """Gibt Error-Statistiken zurück"""
        current_time = time.time()
        hour_ago = current_time - 3600
        day_ago = current_time - 86400

        stats = {
            'total_errors': dict(self.error_counts),
            'error_types': list(self.error_counts.keys()),
            'recent_errors': {},
            'top_errors': []
        }

        # Berechne Recent Errors
        for error_type, history in self.error_history.items():
            hour_errors = len([e for e in history if e['timestamp'] > hour_ago])
            day_errors = len([e for e in history if e['timestamp'] > day_ago])

            stats['recent_errors'][error_type] = {
                'last_hour': hour_errors,
                'last_day': day_errors,
                'total': len(history)
            }

        # Top Errors (nach Häufigkeit)
        sorted_errors = sorted(self.error_counts.items(),
                             key=lambda x: x[1], reverse=True)
        stats['top_errors'] = sorted_errors[:10]

        return stats

    def export_error_report(self, filepath: str, hours: int = 24) -> bool:
        """Exportiert Error-Report in JSON-Datei"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)

            report = {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                'time_range_hours': hours,
                'error_summary': {},
                'detailed_errors': {}
            }

            # Sammle Error-Daten im Zeitrahmen
            for error_type, history in self.error_history.items():
                relevant_errors = [e for e in history if e['timestamp'] > cutoff_time]

                if relevant_errors:
                    report['error_summary'][error_type] = len(relevant_errors)
                    report['detailed_errors'][error_type] = [
                        {
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC',
                                                     time.gmtime(e['timestamp'])),
                            'message': e['message'],
                            'context': e['context']
                        }
                        for e in relevant_errors
                    ]

            # Schreibe Report
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)

            self.logger.info(f"Error report exported to {filepath}")
            return True

        except Exception as e:
            self.logger.error("Failed to export error report", exception=e)
            return False

    def cleanup_old_errors(self, days: int = 7):
        """Entfernt alte Error-Records"""
        cutoff_time = time.time() - (days * 86400)
        cleaned_count = 0

        with self.lock:
            for error_type in list(self.error_history.keys()):
                history = self.error_history[error_type]
                original_length = len(history)

                # Filtere alte Errors
                self.error_history[error_type] = deque(
                    [e for e in history if e['timestamp'] > cutoff_time],
                    maxlen=history.maxlen
                )

                cleaned_count += original_length - len(self.error_history[error_type])

        self.logger.info(f"Cleaned up {cleaned_count} old error records")
        return cleaned_count

# Global Error Reporter Instance
_error_reporter = None

def get_error_reporter(config: Optional[Dict[str, Any]] = None) -> ErrorReporter:
    """Holt oder erstellt Error Reporter Instanz"""
    global _error_reporter
    if _error_reporter is None:
        _error_reporter = ErrorReporter(config)
    return _error_reporter