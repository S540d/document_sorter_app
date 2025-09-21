"""
Monitoring API Blueprint
Handles monitoring, logging, and performance tracking APIs
"""

import time
from datetime import datetime
from flask import Blueprint, request, jsonify

from ..monitoring import get_logger, ErrorReporter, LogAggregator
from ..monitoring.performance_tracker import get_performance_tracker

# Create blueprint
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api')

# Initialize components
logger = get_logger('monitoring_api')
error_reporter = ErrorReporter()
log_aggregator = LogAggregator()
performance_tracker = get_performance_tracker()


@monitoring_bp.route('/monitoring/logs')
def get_logs():
    """Gibt aggregierte Log-Daten zurück"""
    try:
        hours = request.args.get('hours', 24, type=int)
        # Note: In production würde dies async laufen
        # Für jetzt simulieren wir die Aggregation

        stats = {
            'time_range_hours': hours,
            'summary': {
                'total_entries': 150,
                'by_level': {'INFO': 100, 'WARNING': 30, 'ERROR': 15, 'DEBUG': 5},
                'by_logger': {'document_sorter': 80, 'performance': 40, 'security': 30}
            },
            'recent_errors': error_reporter.get_error_statistics()
        }

        logger.info("Log data requested", hours=hours)
        return jsonify(stats)
    except Exception as e:
        logger.error("Failed to get logs", exception=e)
        return jsonify({'error': 'Failed to retrieve logs'}), 500


@monitoring_bp.route('/monitoring/errors')
def get_error_stats():
    """Gibt Error-Statistiken zurück"""
    try:
        stats = error_reporter.get_error_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error("Failed to get error statistics", exception=e)
        return jsonify({'error': 'Failed to retrieve error statistics'}), 500


@monitoring_bp.route('/monitoring/logs/search')
def search_logs():
    """Durchsucht Logs nach Pattern"""
    try:
        pattern = request.args.get('pattern', '')
        hours = request.args.get('hours', 24, type=int)
        log_level = request.args.get('level')

        if not pattern:
            return jsonify({'error': 'Search pattern required'}), 400

        # Note: In production würde dies async laufen
        results = []  # Placeholder - echte Suche würde log_aggregator.search_logs verwenden

        logger.info("Log search performed", pattern=pattern, hours=hours, level=log_level)
        return jsonify({'results': results, 'pattern': pattern})
    except Exception as e:
        logger.error("Log search failed", exception=e)
        return jsonify({'error': 'Log search failed'}), 500


@monitoring_bp.route('/monitoring/logs/export', methods=['POST'])
def export_error_report():
    """Exportiert Error-Report"""
    try:
        data = request.get_json() or {}
        hours = data.get('hours', 24)
        filepath = f"logs/error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        success = error_reporter.export_error_report(filepath, hours)

        if success:
            logger.info("Error report exported", filepath=filepath, hours=hours)
            return jsonify({'success': True, 'filepath': filepath})
        else:
            return jsonify({'error': 'Export failed'}), 500
    except Exception as e:
        logger.error("Error report export failed", exception=e)
        return jsonify({'error': 'Export failed'}), 500


@monitoring_bp.route('/monitoring/logs/cleanup', methods=['POST'])
def cleanup_logs():
    """Führt Log-Cleanup durch"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)

        # Komprimiere alte Logs
        compressed_count = log_aggregator.compress_old_logs()

        # Entferne sehr alte Logs
        removed_count, freed_space = log_aggregator.cleanup_old_logs()

        # Cleanup alte Errors
        cleaned_errors = error_reporter.cleanup_old_errors(days)

        result = {
            'compressed_logs': compressed_count,
            'removed_logs': removed_count,
            'freed_space_mb': round(freed_space / (1024 * 1024), 2),
            'cleaned_errors': cleaned_errors
        }

        logger.info("Log cleanup completed", **result)
        return jsonify(result)
    except Exception as e:
        logger.error("Log cleanup failed", exception=e)
        return jsonify({'error': 'Cleanup failed'}), 500


@monitoring_bp.route('/monitoring/status')
def monitoring_status():
    """Gibt Monitoring-System Status zurück"""
    try:
        log_stats = log_aggregator.get_log_statistics()
        error_stats = error_reporter.get_error_statistics()

        status = {
            'logging': {
                'enabled': True,
                'log_files': log_stats['file_count'],
                'total_size_mb': log_stats['total_size_mb']
            },
            'error_reporting': {
                'enabled': True,
                'total_error_types': len(error_stats['error_types']),
                'total_errors': sum(error_stats['total_errors'].values())
            },
            'log_aggregation': {
                'enabled': True,
                'retention_days': log_aggregator.retention_days
            }
        }

        return jsonify(status)
    except Exception as e:
        logger.error("Failed to get monitoring status", exception=e)
        return jsonify({'error': 'Failed to retrieve status'}), 500


# Performance Monitoring Endpoints
@monitoring_bp.route('/performance/current')
def get_current_performance():
    """Gibt aktuelle Performance-Metriken zurück"""
    try:
        metrics = performance_tracker.get_current_metrics()
        logger.info("Current performance metrics requested")
        return jsonify(metrics)
    except Exception as e:
        logger.error("Failed to get current performance metrics", exception=e)
        return jsonify({'error': 'Failed to retrieve performance metrics'}), 500


@monitoring_bp.route('/performance/historical')
def get_historical_performance():
    """Gibt historische Performance-Metriken zurück"""
    try:
        hours = request.args.get('hours', 24, type=int)
        metrics = performance_tracker.get_historical_metrics(hours)
        logger.info("Historical performance metrics requested", hours=hours)
        return jsonify(metrics)
    except Exception as e:
        logger.error("Failed to get historical performance metrics", exception=e)
        return jsonify({'error': 'Failed to retrieve historical metrics'}), 500


@monitoring_bp.route('/performance/summary')
def get_performance_summary():
    """Gibt Performance-Zusammenfassung zurück"""
    try:
        hours = request.args.get('hours', 24, type=int)
        summary = performance_tracker.get_performance_summary(hours)
        logger.info("Performance summary requested", hours=hours)
        return jsonify(summary)
    except Exception as e:
        logger.error("Failed to get performance summary", exception=e)
        return jsonify({'error': 'Failed to retrieve performance summary'}), 500


@monitoring_bp.route('/performance/alerts')
def get_performance_alerts():
    """Gibt Performance-Alerts zurück"""
    try:
        hours = request.args.get('hours', 24, type=int)
        summary = performance_tracker.get_performance_summary(hours)
        alerts = summary.get('alerts', [])

        logger.info("Performance alerts requested", hours=hours, alert_count=len(alerts))
        return jsonify({'alerts': alerts, 'count': len(alerts)})
    except Exception as e:
        logger.error("Failed to get performance alerts", exception=e)
        return jsonify({'error': 'Failed to retrieve performance alerts'}), 500


@monitoring_bp.route('/performance/export', methods=['POST'])
def export_performance_metrics():
    """Exportiert Performance-Metriken"""
    try:
        data = request.get_json() or {}
        hours = data.get('hours', 24)
        filepath = f"logs/performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        success = performance_tracker.export_metrics(filepath, hours)

        if success:
            logger.info("Performance metrics exported", filepath=filepath, hours=hours)
            return jsonify({'success': True, 'filepath': filepath})
        else:
            return jsonify({'error': 'Export failed'}), 500
    except Exception as e:
        logger.error("Performance metrics export failed", exception=e)
        return jsonify({'error': 'Export failed'}), 500


@monitoring_bp.route('/performance/custom-metric', methods=['POST'])
def record_custom_metric():
    """Zeichnet benutzerdefinierte Metrik auf"""
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'value' not in data:
            return jsonify({'error': 'Missing name or value'}), 400

        name = data['name']
        value = data['value']
        tags = data.get('tags', {})

        performance_tracker.record_custom_metric(name, value, tags)

        logger.info("Custom metric recorded", name=name, value=value, tags=tags)
        return jsonify({'success': True, 'message': f'Metric {name} recorded'})
    except Exception as e:
        logger.error("Failed to record custom metric", exception=e)
        return jsonify({'error': 'Failed to record metric'}), 500


# Dashboard Endpoint
@monitoring_bp.route('/dashboard/overview')
def dashboard_overview():
    """Gibt Dashboard-Übersicht zurück"""
    try:
        # Sammle verschiedene Metriken für Dashboard
        current_perf = performance_tracker.get_current_metrics()
        error_stats = error_reporter.get_error_statistics()
        log_stats = log_aggregator.get_log_statistics()
        perf_summary = performance_tracker.get_performance_summary(24)

        overview = {
            'timestamp': time.time(),
            'system_health': {
                'cpu_percent': current_perf['system'].get('cpu_percent', 0),
                'memory_percent': current_perf['system'].get('memory_percent', 0),
                'disk_usage': current_perf['system'].get('disk_usage', 0),
                'status': perf_summary['system_health']['overall_status']
            },
            'application_stats': {
                'total_requests': sum(current_perf.get('request_counts', {}).values()),
                'average_response_time': _calculate_overall_avg_response_time(current_perf),
                'error_count': sum(error_stats.get('total_errors', {}).values()),
                'monitoring_active': current_perf.get('monitoring_active', False)
            },
            'log_stats': {
                'total_log_files': log_stats.get('file_count', 0),
                'total_size_mb': log_stats.get('total_size_mb', 0)
            },
            'alerts': perf_summary.get('alerts', [])[:5]  # Top 5 alerts
        }

        logger.info("Dashboard overview requested")
        return jsonify(overview)
    except Exception as e:
        logger.error("Failed to get dashboard overview", exception=e)
        return jsonify({'error': 'Failed to retrieve dashboard overview'}), 500


def _calculate_overall_avg_response_time(current_perf):
    """Berechnet durchschnittliche Response Time über alle Endpoints"""
    response_times = current_perf.get('response_times', {})
    if not response_times:
        return 0

    total_time = 0
    total_requests = 0

    for endpoint, stats in response_times.items():
        total_time += stats['avg'] * stats['count']
        total_requests += stats['count']

    return total_time / total_requests if total_requests > 0 else 0