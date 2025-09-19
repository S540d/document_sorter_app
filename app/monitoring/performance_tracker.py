"""
Performance Tracking und Monitoring System
"""
import time
import psutil
import threading
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
from .logger import get_logger

class PerformanceTracker:
    """System für Performance-Monitoring und Metriken"""

    def __init__(self, sample_interval: int = 60):
        self.sample_interval = sample_interval  # Sekunden
        self.logger = get_logger('performance_tracker')

        # Metriken Storage
        self.metrics = {
            'system': {
                'cpu_percent': deque(maxlen=1440),  # 24h bei 1min Intervall
                'memory_percent': deque(maxlen=1440),
                'disk_usage': deque(maxlen=1440),
                'network_io': deque(maxlen=1440)
            },
            'application': {
                'response_times': defaultdict(lambda: deque(maxlen=1000)),
                'request_counts': defaultdict(int),
                'error_rates': defaultdict(lambda: deque(maxlen=100)),
                'active_connections': deque(maxlen=1440)
            },
            'custom': defaultdict(lambda: deque(maxlen=1000))
        }

        # Monitoring Thread
        self.monitoring_thread = None
        self.monitoring_active = False
        self.lock = threading.Lock()

    def start_monitoring(self):
        """Startet kontinuierliches Performance Monitoring"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        self.logger.info("Performance monitoring started",
                        sample_interval=self.sample_interval)

    def stop_monitoring(self):
        """Stoppt Performance Monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()

        self.logger.info("Performance monitoring stopped")

    def _monitoring_loop(self):
        """Haupt-Monitoring-Loop"""
        while self.monitoring_active:
            try:
                self._collect_system_metrics()
                time.sleep(self.sample_interval)
            except Exception as e:
                self.logger.error("Error in monitoring loop", exception=e)
                time.sleep(5)  # Kurze Pause bei Fehler

    def _collect_system_metrics(self):
        """Sammelt System-Performance-Metriken"""
        try:
            timestamp = time.time()

            with self.lock:
                # CPU Usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics['system']['cpu_percent'].append({
                    'timestamp': timestamp,
                    'value': cpu_percent
                })

                # Memory Usage
                memory = psutil.virtual_memory()
                self.metrics['system']['memory_percent'].append({
                    'timestamp': timestamp,
                    'value': memory.percent,
                    'available_gb': round(memory.available / (1024**3), 2)
                })

                # Disk Usage
                disk = psutil.disk_usage('/')
                self.metrics['system']['disk_usage'].append({
                    'timestamp': timestamp,
                    'value': (disk.used / disk.total) * 100,
                    'free_gb': round(disk.free / (1024**3), 2)
                })

                # Network I/O
                network = psutil.net_io_counters()
                self.metrics['system']['network_io'].append({
                    'timestamp': timestamp,
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv
                })

                # Process-spezifische Metriken
                process = psutil.Process()
                self.metrics['application']['active_connections'].append({
                    'timestamp': timestamp,
                    'value': len(process.connections()),
                    'memory_mb': round(process.memory_info().rss / (1024**2), 2)
                })

        except Exception as e:
            self.logger.error("Error collecting system metrics", exception=e)

    def record_response_time(self, endpoint: str, duration: float):
        """Zeichnet Response-Zeit für Endpoint auf"""
        with self.lock:
            self.metrics['application']['response_times'][endpoint].append({
                'timestamp': time.time(),
                'duration': duration
            })
            self.metrics['application']['request_counts'][endpoint] += 1

    def record_error_rate(self, endpoint: str, error_occurred: bool):
        """Zeichnet Error-Rate für Endpoint auf"""
        with self.lock:
            self.metrics['application']['error_rates'][endpoint].append({
                'timestamp': time.time(),
                'error': error_occurred
            })

    def record_custom_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Zeichnet benutzerdefinierte Metrik auf"""
        with self.lock:
            self.metrics['custom'][name].append({
                'timestamp': time.time(),
                'value': value,
                'tags': tags or {}
            })

    def get_current_metrics(self) -> Dict[str, Any]:
        """Gibt aktuelle Performance-Metriken zurück"""
        with self.lock:
            current_time = time.time()

            # Letzte System-Metriken
            latest_metrics = {}
            for category, metric_types in self.metrics['system'].items():
                if metric_types:
                    latest_metrics[category] = metric_types[-1]['value']
                else:
                    latest_metrics[category] = 0

            # Response Time Statistiken
            response_stats = {}
            for endpoint, times in self.metrics['application']['response_times'].items():
                if times:
                    durations = [t['duration'] for t in times]
                    response_stats[endpoint] = {
                        'avg': sum(durations) / len(durations),
                        'min': min(durations),
                        'max': max(durations),
                        'count': len(durations)
                    }

            # Error Rate Statistiken
            error_stats = {}
            for endpoint, errors in self.metrics['application']['error_rates'].items():
                if errors:
                    total_requests = len(errors)
                    error_count = sum(1 for e in errors if e['error'])
                    error_stats[endpoint] = {
                        'error_rate': (error_count / total_requests) * 100,
                        'total_requests': total_requests,
                        'error_count': error_count
                    }

            return {
                'timestamp': current_time,
                'system': latest_metrics,
                'response_times': response_stats,
                'error_rates': error_stats,
                'request_counts': dict(self.metrics['application']['request_counts']),
                'monitoring_active': self.monitoring_active
            }

    def get_historical_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Gibt historische Metriken zurück"""
        cutoff_time = time.time() - (hours * 3600)

        with self.lock:
            historical = {
                'time_range_hours': hours,
                'system': {},
                'application': {},
                'custom': {}
            }

            # System-Metriken filtern
            for metric_name, metric_data in self.metrics['system'].items():
                historical['system'][metric_name] = [
                    m for m in metric_data if m['timestamp'] > cutoff_time
                ]

            # Application-Metriken filtern
            for metric_name, metric_data in self.metrics['application'].items():
                if isinstance(metric_data, deque):
                    historical['application'][metric_name] = [
                        m for m in metric_data if m['timestamp'] > cutoff_time
                    ]
                elif isinstance(metric_data, defaultdict):
                    historical['application'][metric_name] = {}
                    for endpoint, data in metric_data.items():
                        historical['application'][metric_name][endpoint] = [
                            m for m in data if m['timestamp'] > cutoff_time
                        ]

            # Custom-Metriken filtern
            for metric_name, metric_data in self.metrics['custom'].items():
                historical['custom'][metric_name] = [
                    m for m in metric_data if m['timestamp'] > cutoff_time
                ]

            return historical

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Gibt Performance-Zusammenfassung zurück"""
        historical = self.get_historical_metrics(hours)

        summary = {
            'time_range_hours': hours,
            'system_health': self._analyze_system_health(historical),
            'application_performance': self._analyze_application_performance(historical),
            'alerts': self._generate_performance_alerts(historical)
        }

        return summary

    def _analyze_system_health(self, historical: Dict[str, Any]) -> Dict[str, Any]:
        """Analysiert System-Gesundheit"""
        system_data = historical['system']
        health = {
            'overall_status': 'healthy',
            'cpu': {'status': 'ok', 'avg': 0, 'max': 0},
            'memory': {'status': 'ok', 'avg': 0, 'max': 0},
            'disk': {'status': 'ok', 'avg': 0, 'max': 0}
        }

        # CPU-Analyse
        if system_data.get('cpu_percent'):
            cpu_values = [m['value'] for m in system_data['cpu_percent']]
            health['cpu']['avg'] = sum(cpu_values) / len(cpu_values)
            health['cpu']['max'] = max(cpu_values)

            if health['cpu']['avg'] > 80:
                health['cpu']['status'] = 'warning'
            if health['cpu']['max'] > 95:
                health['cpu']['status'] = 'critical'

        # Memory-Analyse
        if system_data.get('memory_percent'):
            mem_values = [m['value'] for m in system_data['memory_percent']]
            health['memory']['avg'] = sum(mem_values) / len(mem_values)
            health['memory']['max'] = max(mem_values)

            if health['memory']['avg'] > 85:
                health['memory']['status'] = 'warning'
            if health['memory']['max'] > 95:
                health['memory']['status'] = 'critical'

        # Disk-Analyse
        if system_data.get('disk_usage'):
            disk_values = [m['value'] for m in system_data['disk_usage']]
            health['disk']['avg'] = sum(disk_values) / len(disk_values)
            health['disk']['max'] = max(disk_values)

            if health['disk']['avg'] > 90:
                health['disk']['status'] = 'warning'
            if health['disk']['max'] > 98:
                health['disk']['status'] = 'critical'

        # Overall Status
        if any(h['status'] == 'critical' for h in [health['cpu'], health['memory'], health['disk']]):
            health['overall_status'] = 'critical'
        elif any(h['status'] == 'warning' for h in [health['cpu'], health['memory'], health['disk']]):
            health['overall_status'] = 'warning'

        return health

    def _analyze_application_performance(self, historical: Dict[str, Any]) -> Dict[str, Any]:
        """Analysiert Application-Performance"""
        app_data = historical['application']

        performance = {
            'response_times': {},
            'throughput': {},
            'reliability': {}
        }

        # Response Times analysieren
        if 'response_times' in app_data:
            for endpoint, times in app_data['response_times'].items():
                if times:
                    durations = [t['duration'] for t in times]
                    performance['response_times'][endpoint] = {
                        'avg': sum(durations) / len(durations),
                        'p95': sorted(durations)[int(len(durations) * 0.95)],
                        'p99': sorted(durations)[int(len(durations) * 0.99)]
                    }

        return performance

    def _generate_performance_alerts(self, historical: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generiert Performance-Alerts"""
        alerts = []
        current_time = time.time()

        # System-Alerts
        system_health = self._analyze_system_health(historical)

        for component, health in system_health.items():
            if isinstance(health, dict) and health.get('status') in ['warning', 'critical']:
                alerts.append({
                    'type': 'system_performance',
                    'component': component,
                    'severity': health['status'],
                    'message': f"{component.upper()} usage is {health['status']}: {health.get('avg', 0):.1f}% average",
                    'timestamp': current_time
                })

        # Response Time Alerts
        app_performance = self._analyze_application_performance(historical)
        for endpoint, metrics in app_performance['response_times'].items():
            if metrics['avg'] > 5.0:  # Langsamer als 5 Sekunden
                alerts.append({
                    'type': 'response_time',
                    'endpoint': endpoint,
                    'severity': 'warning',
                    'message': f"Slow response time for {endpoint}: {metrics['avg']:.2f}s average",
                    'timestamp': current_time
                })

        return alerts

    def export_metrics(self, filepath: str, hours: int = 24) -> bool:
        """Exportiert Metriken in JSON-Datei"""
        try:
            metrics_data = {
                'export_timestamp': datetime.now().isoformat(),
                'time_range_hours': hours,
                'current_metrics': self.get_current_metrics(),
                'historical_metrics': self.get_historical_metrics(hours),
                'performance_summary': self.get_performance_summary(hours)
            }

            with open(filepath, 'w') as f:
                json.dump(metrics_data, f, indent=2, default=str)

            self.logger.info(f"Performance metrics exported to {filepath}")
            return True

        except Exception as e:
            self.logger.error("Failed to export performance metrics", exception=e)
            return False

# Global Performance Tracker Instance
_performance_tracker = None

def get_performance_tracker() -> PerformanceTracker:
    """Holt oder erstellt Performance Tracker Instanz"""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
        _performance_tracker.start_monitoring()
    return _performance_tracker