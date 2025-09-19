"""
Log Aggregation und Retention Management
"""
import json
import gzip
import shutil
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import re
import asyncio
from .logger import get_logger

class LogAggregator:
    """Log Aggregation und Analyse System"""

    def __init__(self, log_dir: str = "logs", retention_days: int = 30):
        self.log_dir = Path(log_dir)
        self.retention_days = retention_days
        self.logger = get_logger('log_aggregator')

    async def aggregate_logs(self, hours: int = 24) -> Dict[str, Any]:
        """Aggregiert Logs der letzten X Stunden"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        aggregation = {
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            },
            'summary': {
                'total_entries': 0,
                'by_level': defaultdict(int),
                'by_logger': defaultdict(int),
                'by_hour': defaultdict(int),
                'errors': []
            },
            'performance': {
                'operations': [],
                'slow_operations': [],
                'avg_response_times': {}
            },
            'security': {
                'events': [],
                'failed_logins': 0,
                'rate_limit_hits': 0,
                'suspicious_activities': []
            }
        }

        # Durchsuche alle Log-Dateien
        for log_file in self.log_dir.glob("*.log"):
            if log_file.name.endswith('_daily.log'):
                continue  # Skip daily rotated files for now

            await self._process_log_file(log_file, start_time, end_time, aggregation)

        # Berechne Durchschnittswerte
        self._calculate_averages(aggregation)

        self.logger.info("Log aggregation completed",
                        time_range_hours=hours,
                        total_entries=aggregation['summary']['total_entries'])

        return aggregation

    async def _process_log_file(self, log_file: Path, start_time: datetime,
                               end_time: datetime, aggregation: Dict[str, Any]):
        """Verarbeitet eine einzelne Log-Datei"""
        try:
            with open(log_file, 'r') as f:
                async for line_num, line in self._async_file_reader(f):
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(
                            entry.get('timestamp', '').replace('Z', '+00:00')
                        )

                        # Prüfe Zeitrahmen
                        if start_time <= entry_time <= end_time:
                            await self._process_log_entry(entry, aggregation)

                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        # Skip malformed entries
                        continue

        except Exception as e:
            self.logger.error(f"Error processing log file {log_file}",
                            exception=e)

    async def _async_file_reader(self, file_obj):
        """Async generator für Datei-Zeilen"""
        line_num = 0
        for line in file_obj:
            line_num += 1
            yield line_num, line
            if line_num % 1000 == 0:  # Yield control every 1000 lines
                await asyncio.sleep(0)

    async def _process_log_entry(self, entry: Dict[str, Any], aggregation: Dict[str, Any]):
        """Verarbeitet einen einzelnen Log-Eintrag"""
        summary = aggregation['summary']
        summary['total_entries'] += 1

        # Level-Statistiken
        level = entry.get('level', 'UNKNOWN')
        summary['by_level'][level] += 1

        # Logger-Statistiken
        logger_name = entry.get('logger', 'unknown')
        summary['by_logger'][logger_name] += 1

        # Stunden-Statistiken
        timestamp = entry.get('timestamp', '')
        if timestamp:
            try:
                hour = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).hour
                summary['by_hour'][hour] += 1
            except:
                pass

        # Error-Sammlung
        if level in ['ERROR', 'CRITICAL']:
            error_info = {
                'timestamp': timestamp,
                'message': entry.get('message', ''),
                'logger': logger_name,
                'level': level
            }
            if 'exception' in entry:
                error_info['exception'] = entry['exception']

            summary['errors'].append(error_info)

        # Performance-Daten
        if logger_name == 'performance' and 'operation' in entry:
            operation = entry['operation']
            duration = entry.get('duration', 0)

            perf_entry = {
                'timestamp': timestamp,
                'operation': operation,
                'duration': duration,
                'status': entry.get('status', 'unknown')
            }
            aggregation['performance']['operations'].append(perf_entry)

            # Langsame Operationen (> 5 Sekunden)
            if duration > 5.0:
                aggregation['performance']['slow_operations'].append(perf_entry)

        # Security-Events
        if logger_name == 'security':
            event_type = entry.get('event_type', 'unknown')
            security_event = {
                'timestamp': timestamp,
                'event_type': event_type,
                'severity': entry.get('severity', 'INFO'),
                'status': entry.get('status', 'unknown'),
                'client_ip': entry.get('client_ip')
            }
            aggregation['security']['events'].append(security_event)

            # Spezielle Security-Metriken
            if 'login' in event_type.lower() and entry.get('status') == 'failed':
                aggregation['security']['failed_logins'] += 1

            if 'rate_limit' in entry.get('message', '').lower():
                aggregation['security']['rate_limit_hits'] += 1

    def _calculate_averages(self, aggregation: Dict[str, Any]):
        """Berechnet Durchschnittswerte und zusätzliche Metriken"""
        # Performance-Durchschnitte
        operations = aggregation['performance']['operations']
        operation_times = defaultdict(list)

        for op in operations:
            operation_times[op['operation']].append(op['duration'])

        for operation, times in operation_times.items():
            if times:
                aggregation['performance']['avg_response_times'][operation] = {
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'count': len(times)
                }

        # Security-Analyse
        security_events = aggregation['security']['events']
        ip_counts = defaultdict(int)

        for event in security_events:
            if event['client_ip']:
                ip_counts[event['client_ip']] += 1

        # Verdächtige IPs (viele Anfragen)
        suspicious_threshold = 50
        for ip, count in ip_counts.items():
            if count > suspicious_threshold:
                aggregation['security']['suspicious_activities'].append({
                    'type': 'high_request_volume',
                    'client_ip': ip,
                    'request_count': count
                })

    def compress_old_logs(self):
        """Komprimiert alte Log-Dateien"""
        compressed_count = 0
        cutoff_date = datetime.now() - timedelta(days=7)

        for log_file in self.log_dir.glob("*.log"):
            if log_file.suffix == '.gz':
                continue

            # Prüfe Dateialter
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff_date:
                compressed_file = log_file.with_suffix(log_file.suffix + '.gz')

                with open(log_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                log_file.unlink()  # Lösche Original
                compressed_count += 1

                self.logger.info(f"Compressed log file: {log_file}")

        return compressed_count

    def cleanup_old_logs(self):
        """Entfernt alte Log-Dateien basierend auf Retention Policy"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        freed_space = 0

        for log_file in self.log_dir.rglob("*"):
            if not log_file.is_file():
                continue

            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff_date:
                file_size = log_file.stat().st_size
                log_file.unlink()
                removed_count += 1
                freed_space += file_size

                self.logger.info(f"Removed old log file: {log_file}")

        freed_mb = freed_space / (1024 * 1024)
        self.logger.info(f"Log cleanup completed",
                        removed_files=removed_count,
                        freed_space_mb=round(freed_mb, 2))

        return removed_count, freed_space

    async def search_logs(self, pattern: str, hours: int = 24,
                         log_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Durchsucht Logs nach Pattern"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        results = []
        regex_pattern = re.compile(pattern, re.IGNORECASE)

        for log_file in self.log_dir.glob("*.log"):
            try:
                with open(log_file, 'r') as f:
                    async for line_num, line in self._async_file_reader(f):
                        try:
                            entry = json.loads(line.strip())
                            entry_time = datetime.fromisoformat(
                                entry.get('timestamp', '').replace('Z', '+00:00')
                            )

                            # Prüfe Zeitrahmen
                            if not (start_time <= entry_time <= end_time):
                                continue

                            # Prüfe Log-Level Filter
                            if log_level and entry.get('level') != log_level:
                                continue

                            # Prüfe Pattern
                            message = entry.get('message', '')
                            if regex_pattern.search(message):
                                results.append({
                                    'file': str(log_file),
                                    'line': line_num,
                                    'entry': entry
                                })

                        except (json.JSONDecodeError, ValueError):
                            continue

            except Exception as e:
                self.logger.error(f"Error searching log file {log_file}",
                                exception=e)

        return results

    def get_log_statistics(self) -> Dict[str, Any]:
        """Gibt allgemeine Log-Statistiken zurück"""
        stats = {
            'log_files': [],
            'total_size_mb': 0,
            'oldest_log': None,
            'newest_log': None
        }

        total_size = 0
        oldest_time = None
        newest_time = None

        for log_file in self.log_dir.rglob("*"):
            if not log_file.is_file():
                continue

            file_size = log_file.stat().st_size
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)

            stats['log_files'].append({
                'name': str(log_file.relative_to(self.log_dir)),
                'size_mb': round(file_size / (1024 * 1024), 2),
                'modified': file_time.isoformat(),
                'compressed': log_file.suffix == '.gz'
            })

            total_size += file_size

            if oldest_time is None or file_time < oldest_time:
                oldest_time = file_time
                stats['oldest_log'] = str(log_file.relative_to(self.log_dir))

            if newest_time is None or file_time > newest_time:
                newest_time = file_time
                stats['newest_log'] = str(log_file.relative_to(self.log_dir))

        stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
        stats['file_count'] = len(stats['log_files'])

        return stats