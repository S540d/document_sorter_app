"""
Tests for monitoring and logging functionality
"""
import pytest
import json
import time
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Import monitoring modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.monitoring.logger import StructuredLogger, get_logger
from app.monitoring.performance_tracker import PerformanceTracker
from app.monitoring.error_reporter import ErrorReporter

class TestStructuredLogger:
    """Test cases for StructuredLogger"""

    @pytest.fixture
    def logger(self):
        """Create logger instance for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = StructuredLogger('test_logger', temp_dir)
            yield logger

    def test_logger_initialization(self, logger):
        """Test logger initialization"""
        assert logger.name == 'test_logger'
        assert logger.logger is not None
        assert len(logger.logger.handlers) > 0

    def test_info_logging(self, logger):
        """Test info level logging"""
        with patch.object(logger.logger, 'info') as mock_info:
            logger.info("Test message", extra_field="test_value")

            mock_info.assert_called_once()
            # Verify the logged message is JSON
            logged_data = json.loads(mock_info.call_args[0][0])
            assert logged_data['level'] == 'INFO'
            assert logged_data['message'] == "Test message"
            assert logged_data['extra_field'] == "test_value"

    def test_error_logging_with_exception(self, logger):
        """Test error logging with exception"""
        test_exception = ValueError("Test error")

        with patch.object(logger.logger, 'error') as mock_error:
            logger.error("Error occurred", exception=test_exception)

            mock_error.assert_called_once()
            logged_data = json.loads(mock_error.call_args[0][0])
            assert logged_data['level'] == 'ERROR'
            assert logged_data['message'] == "Error occurred"
            assert 'exception' in logged_data
            assert logged_data['exception']['type'] == 'ValueError'

    def test_context_setting(self, logger):
        """Test setting and using context"""
        logger.set_context(request_id="123", user_id="456")

        with patch.object(logger.logger, 'info') as mock_info:
            logger.info("Test with context")

            logged_data = json.loads(mock_info.call_args[0][0])
            assert logged_data['request_id'] == "123"
            assert logged_data['user_id'] == "456"

    def test_clear_context(self, logger):
        """Test clearing context"""
        logger.set_context(test_key="test_value")
        logger.clear_context()

        with patch.object(logger.logger, 'info') as mock_info:
            logger.info("Test after clear")

            logged_data = json.loads(mock_info.call_args[0][0])
            assert 'test_key' not in logged_data

class TestPerformanceTracker:
    """Test cases for PerformanceTracker"""

    @pytest.fixture
    def tracker(self):
        """Create performance tracker for testing"""
        return PerformanceTracker(sample_interval=1)

    def test_tracker_initialization(self, tracker):
        """Test tracker initialization"""
        assert tracker.sample_interval == 1
        assert not tracker.monitoring_active
        assert 'system' in tracker.metrics
        assert 'application' in tracker.metrics

    def test_start_stop_monitoring(self, tracker):
        """Test starting and stopping monitoring"""
        assert not tracker.monitoring_active

        tracker.start_monitoring()
        assert tracker.monitoring_active
        assert tracker.monitoring_thread is not None

        tracker.stop_monitoring()
        assert not tracker.monitoring_active

    def test_record_response_time(self, tracker):
        """Test recording response times"""
        tracker.record_response_time('/api/test', 1.5)
        tracker.record_response_time('/api/test', 2.0)

        current_metrics = tracker.get_current_metrics()
        assert '/api/test' in current_metrics['response_times']
        assert current_metrics['response_times']['/api/test']['count'] == 2
        assert current_metrics['request_counts']['/api/test'] == 2

    def test_record_error_rate(self, tracker):
        """Test recording error rates"""
        tracker.record_error_rate('/api/test', False)
        tracker.record_error_rate('/api/test', True)
        tracker.record_error_rate('/api/test', False)

        current_metrics = tracker.get_current_metrics()
        assert '/api/test' in current_metrics['error_rates']
        # 1 error out of 3 requests = 33.33%
        assert abs(current_metrics['error_rates']['/api/test']['error_rate'] - 33.33) < 0.1

    def test_record_custom_metric(self, tracker):
        """Test recording custom metrics"""
        tracker.record_custom_metric('custom_metric', 42.0, {'tag1': 'value1'})

        # Custom metrics aren't directly exposed in current_metrics,
        # but we can check if it was stored
        assert 'custom_metric' in tracker.metrics['custom']
        assert len(tracker.metrics['custom']['custom_metric']) == 1

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    @patch('psutil.Process')
    def test_collect_system_metrics(self, mock_process, mock_net, mock_disk, mock_memory, mock_cpu, tracker):
        """Test system metrics collection"""
        # Mock system metrics
        mock_cpu.return_value = 50.0

        mock_memory_obj = MagicMock()
        mock_memory_obj.percent = 60.0
        mock_memory_obj.available = 4 * 1024**3  # 4GB
        mock_memory.return_value = mock_memory_obj

        mock_disk_obj = MagicMock()
        mock_disk_obj.used = 100 * 1024**3  # 100GB
        mock_disk_obj.total = 500 * 1024**3  # 500GB
        mock_disk_obj.free = 400 * 1024**3  # 400GB
        mock_disk.return_value = mock_disk_obj

        mock_net_obj = MagicMock()
        mock_net_obj.bytes_sent = 1000000
        mock_net_obj.bytes_recv = 2000000
        mock_net.return_value = mock_net_obj

        mock_process_obj = MagicMock()
        mock_process_obj.connections.return_value = [1, 2, 3]  # 3 connections
        mock_process_memory = MagicMock()
        mock_process_memory.rss = 128 * 1024**2  # 128MB
        mock_process_obj.memory_info.return_value = mock_process_memory
        mock_process.return_value = mock_process_obj

        # Call the method
        tracker._collect_system_metrics()

        # Verify metrics were collected
        assert len(tracker.metrics['system']['cpu_percent']) > 0
        assert len(tracker.metrics['system']['memory_percent']) > 0
        assert len(tracker.metrics['system']['disk_usage']) > 0

    def test_get_performance_summary(self, tracker):
        """Test getting performance summary"""
        # Add some test data
        tracker.record_response_time('/test', 2.0)
        tracker.record_error_rate('/test', True)

        summary = tracker.get_performance_summary(1)

        assert 'time_range_hours' in summary
        assert 'system_health' in summary
        assert 'application_performance' in summary
        assert 'alerts' in summary

class TestErrorReporter:
    """Test cases for ErrorReporter"""

    @pytest.fixture
    def error_reporter(self):
        """Create error reporter for testing"""
        config = {
            'notification_cooldown': 60,
            'max_errors_per_hour': 5,
            'notification_emails': ['test@example.com'],
            'smtp': {
                'host': 'smtp.test.com',
                'port': 587,
                'username': 'test_user',
                'password': 'test_pass',
                'from_email': 'noreply@test.com'
            }
        }
        return ErrorReporter(config)

    def test_error_reporter_initialization(self, error_reporter):
        """Test error reporter initialization"""
        assert error_reporter.notification_cooldown == 60
        assert error_reporter.max_errors_per_hour == 5
        assert 'test@example.com' in error_reporter.notification_emails

    def test_report_error(self, error_reporter):
        """Test reporting an error"""
        with patch.object(error_reporter, '_send_notification') as mock_send:
            error_reporter.report_error(
                'test_error',
                'Test error message',
                {'context': 'test'}
            )

            # First error shouldn't trigger notification (no history)
            assert 'test_error' in error_reporter.error_counts
            assert error_reporter.error_counts['test_error'] == 1

    def test_critical_error_triggers_notification(self, error_reporter):
        """Test that critical errors trigger immediate notification"""
        with patch.object(error_reporter, '_send_notification') as mock_send:
            error_reporter.report_error(
                'authentication_failure',  # Critical error type
                'Authentication failed',
                {'user': 'test_user'}
            )

            # Should trigger notification for critical error
            mock_send.assert_called_once()

    def test_error_rate_triggering(self, error_reporter):
        """Test that high error rates trigger notifications"""
        with patch.object(error_reporter, '_send_notification') as mock_send:
            # Report many errors quickly to trigger rate limit
            for i in range(6):  # More than max_errors_per_hour (5)
                error_reporter.report_error('frequent_error', f'Error {i}')

            # Should have triggered notification due to high error rate
            assert mock_send.called

    def test_get_error_statistics(self, error_reporter):
        """Test getting error statistics"""
        # Add some test errors
        error_reporter.report_error('error1', 'Message 1')
        error_reporter.report_error('error2', 'Message 2')
        error_reporter.report_error('error1', 'Message 3')

        stats = error_reporter.get_error_statistics()

        assert 'total_errors' in stats
        assert 'error_types' in stats
        assert 'recent_errors' in stats
        assert 'top_errors' in stats

        assert stats['total_errors']['error1'] == 2
        assert stats['total_errors']['error2'] == 1

    def test_export_error_report(self, error_reporter):
        """Test exporting error report"""
        # Add test error
        error_reporter.report_error('test_error', 'Test message')

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_file:
            try:
                success = error_reporter.export_error_report(tmp_file.name, hours=1)
                assert success

                # Verify file was created and contains data
                assert os.path.exists(tmp_file.name)

                with open(tmp_file.name, 'r') as f:
                    data = json.load(f)
                    assert 'generated_at' in data
                    assert 'error_summary' in data

            finally:
                os.unlink(tmp_file.name)

    def test_cleanup_old_errors(self, error_reporter):
        """Test cleaning up old error records"""
        # Add test error
        error_reporter.report_error('old_error', 'Old message')

        # Mock old timestamp
        old_time = time.time() - (8 * 86400)  # 8 days ago
        error_reporter.error_history['old_error'][0]['timestamp'] = old_time

        cleaned_count = error_reporter.cleanup_old_errors(days=7)

        assert cleaned_count > 0
        # Should have removed the old error
        assert len(error_reporter.error_history['old_error']) == 0