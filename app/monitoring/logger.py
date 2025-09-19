"""
Strukturiertes Logging System
"""
import json
import logging
import time
from typing import Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
from functools import wraps
import traceback
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

class StructuredLogger:
    """Strukturierter Logger mit JSON-Format und Context-Support"""

    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Verhindere doppelte Handler
        if not self.logger.handlers:
            self._setup_handlers()

        self.context = {}

    def _setup_handlers(self):
        """Konfiguriert verschiedene Log-Handler"""

        # Console Handler für Development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File Handler für strukturierte Logs
        log_file = self.log_dir / f"{self.name}.log"
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB per file, 5 backups
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = StructuredFormatter()
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Error Handler für separate Error-Logs
        error_file = self.log_dir / f"{self.name}_errors.log"
        error_handler = RotatingFileHandler(
            error_file, maxBytes=5*1024*1024, backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        self.logger.addHandler(error_handler)

        # Daily rotating handler für archivierung
        daily_file = self.log_dir / f"{self.name}_daily.log"
        daily_handler = TimedRotatingFileHandler(
            daily_file, when='midnight', interval=1, backupCount=30
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(file_formatter)
        self.logger.addHandler(daily_handler)

    def set_context(self, **kwargs):
        """Setzt globalen Kontext für alle Log-Nachrichten"""
        self.context.update(kwargs)

    def clear_context(self):
        """Löscht globalen Kontext"""
        self.context.clear()

    def _create_log_entry(self, level: str, message: str, **kwargs) -> Dict[str, Any]:
        """Erstellt strukturierten Log-Eintrag"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'logger': self.name,
            'message': message,
            'process_id': os.getpid(),
        }

        # Füge globalen Kontext hinzu
        entry.update(self.context)

        # Füge spezifische Daten hinzu
        entry.update(kwargs)

        return entry

    def info(self, message: str, **kwargs):
        """Info-Level Logging"""
        entry = self._create_log_entry('INFO', message, **kwargs)
        self.logger.info(json.dumps(entry))

    def debug(self, message: str, **kwargs):
        """Debug-Level Logging"""
        entry = self._create_log_entry('DEBUG', message, **kwargs)
        self.logger.debug(json.dumps(entry))

    def warning(self, message: str, **kwargs):
        """Warning-Level Logging"""
        entry = self._create_log_entry('WARNING', message, **kwargs)
        self.logger.warning(json.dumps(entry))

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Error-Level Logging mit Exception-Support"""
        entry = self._create_log_entry('ERROR', message, **kwargs)

        if exception:
            entry['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': traceback.format_exc()
            }

        self.logger.error(json.dumps(entry))

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Critical-Level Logging"""
        entry = self._create_log_entry('CRITICAL', message, **kwargs)

        if exception:
            entry['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': traceback.format_exc()
            }

        self.logger.critical(json.dumps(entry))

class StructuredFormatter(logging.Formatter):
    """Custom Formatter für strukturierte Logs"""

    def format(self, record):
        # Wenn die Nachricht bereits JSON ist, gib sie direkt zurück
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            # Fallback für normale Log-Nachrichten
            entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'process_id': os.getpid()
            }
            return json.dumps(entry)

# Global Logger Instanzen
_loggers = {}

def get_logger(name: str = 'document_sorter') -> StructuredLogger:
    """Holt oder erstellt Logger-Instanz"""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]

def log_performance(operation: str):
    """Decorator für Performance-Logging"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger('performance')
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(f"Operation completed: {operation}",
                           operation=operation,
                           duration=duration,
                           status='success')
                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Operation failed: {operation}",
                           operation=operation,
                           duration=duration,
                           status='error',
                           exception=e)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger('performance')
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(f"Operation completed: {operation}",
                           operation=operation,
                           duration=duration,
                           status='success')
                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Operation failed: {operation}",
                           operation=operation,
                           duration=duration,
                           status='error',
                           exception=e)
                raise

        # Wähle den passenden Wrapper basierend auf Funktion
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

def log_security_event(event_type: str, severity: str = 'INFO'):
    """Decorator für Security Event Logging"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger('security')

            # Request-Info extrahieren (wenn verfügbar)
            request_info = {}
            try:
                from quart import request
                request_info = {
                    'client_ip': request.environ.get('REMOTE_ADDR'),
                    'user_agent': request.headers.get('User-Agent'),
                    'endpoint': request.endpoint,
                    'method': request.method
                }
            except:
                pass

            try:
                result = await func(*args, **kwargs)

                logger.info(f"Security event: {event_type}",
                           event_type=event_type,
                           severity=severity,
                           status='success',
                           **request_info)
                return result

            except Exception as e:
                logger.error(f"Security event failed: {event_type}",
                           event_type=event_type,
                           severity='ERROR',
                           status='failed',
                           exception=e,
                           **request_info)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger('security')

            request_info = {}
            try:
                from quart import request
                request_info = {
                    'client_ip': request.environ.get('REMOTE_ADDR'),
                    'user_agent': request.headers.get('User-Agent'),
                    'endpoint': request.endpoint,
                    'method': request.method
                }
            except:
                pass

            try:
                result = func(*args, **kwargs)

                logger.info(f"Security event: {event_type}",
                           event_type=event_type,
                           severity=severity,
                           status='success',
                           **request_info)
                return result

            except Exception as e:
                logger.error(f"Security event failed: {event_type}",
                           event_type=event_type,
                           severity='ERROR',
                           status='failed',
                           exception=e,
                           **request_info)
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

class RequestLogger:
    """Middleware für Request/Response Logging"""

    def __init__(self, app, logger_name='requests'):
        self.app = app
        self.logger = get_logger(logger_name)

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            start_time = time.time()

            # Request Info sammeln
            method = scope['method']
            path = scope['path']
            client = scope.get('client', ['unknown', 0])
            client_ip = client[0]

            # Headers sammeln (ohne sensitive Daten)
            headers = dict(scope.get('headers', []))
            safe_headers = {}
            for key, value in headers.items():
                key_str = key.decode() if isinstance(key, bytes) else key
                if key_str.lower() not in ['authorization', 'cookie', 'x-api-key']:
                    safe_headers[key_str] = value.decode() if isinstance(value, bytes) else value

            request_info = {
                'method': method,
                'path': path,
                'client_ip': client_ip,
                'headers': safe_headers
            }

            # Response abfangen
            response_info = {}
            original_send = send

            async def logging_send(message):
                if message['type'] == 'http.response.start':
                    response_info['status_code'] = message['status']
                    response_info['headers'] = dict(message.get('headers', []))

                await original_send(message)

            try:
                await self.app(scope, receive, logging_send)
                duration = time.time() - start_time

                self.logger.info("HTTP Request",
                               request=request_info,
                               response=response_info,
                               duration=duration,
                               status='completed')

            except Exception as e:
                duration = time.time() - start_time

                self.logger.error("HTTP Request failed",
                                request=request_info,
                                duration=duration,
                                status='failed',
                                exception=e)
                raise
        else:
            await self.app(scope, receive, send)