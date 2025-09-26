"""
Batch Processing API Blueprint
Handles batch operations for document processing
"""

from flask import Blueprint, request, jsonify
from pathlib import Path

from ..settings import CONFIG
from ..monitoring import get_logger
from ..services.batch_processor import batch_processor, JobStatus

# Create blueprint
batch_bp = Blueprint('batch', __name__, url_prefix='/api/batch')

# Initialize logger
logger = get_logger('batch_api')


@batch_bp.route('/operations', methods=['GET'])
def list_operations():
    """Liste alle Batch-Operationen auf"""
    try:
        status_filter = request.args.get('status')
        status_enum = None
        if status_filter:
            try:
                status_enum = JobStatus(status_filter)
            except ValueError:
                return jsonify({'error': f'Invalid status: {status_filter}'}), 400

        operations = batch_processor.list_operations(status_filter=status_enum)
        return jsonify({'operations': operations})

    except Exception as e:
        logger.error("Failed to list batch operations", exception=e)
        return jsonify({'error': 'Failed to list operations'}), 500


@batch_bp.route('/operations', methods=['POST'])
def create_operation():
    """Erstelle eine neue Batch-Operation"""
    try:
        data = request.get_json()
        name = data.get('name', 'Unnamed Batch Operation')
        file_paths = data.get('file_paths', [])
        auto_process = data.get('auto_process', False)
        target_category = data.get('target_category')

        if not file_paths:
            return jsonify({'error': 'No file paths provided'}), 400

        # Validate file paths
        scan_dir = Path(CONFIG['SCAN_DIR'])
        valid_paths = []
        invalid_paths = []

        for file_path in file_paths:
            path_obj = Path(file_path)
            if path_obj.exists() and path_obj.suffix.lower() == '.pdf':
                valid_paths.append(str(path_obj))
            else:
                invalid_paths.append(file_path)

        if not valid_paths:
            return jsonify({
                'error': 'No valid PDF files found',
                'invalid_paths': invalid_paths
            }), 400

        # Create batch operation
        operation_id = batch_processor.create_batch_operation(
            name=name,
            file_paths=valid_paths,
            auto_process=auto_process,
            target_category=target_category
        )

        logger.info("Batch operation created",
                   operation_id=operation_id,
                   name=name,
                   total_files=len(valid_paths),
                   auto_process=auto_process)

        result = {
            'operation_id': operation_id,
            'valid_paths': valid_paths,
            'auto_started': auto_process
        }

        if invalid_paths:
            result['invalid_paths'] = invalid_paths

        return jsonify(result)

    except Exception as e:
        logger.error("Failed to create batch operation", exception=e)
        return jsonify({'error': 'Failed to create operation'}), 500


@batch_bp.route('/operations/<operation_id>', methods=['GET'])
def get_operation_status(operation_id):
    """Hole den Status einer Batch-Operation"""
    try:
        status = batch_processor.get_operation_status(operation_id)
        if status is None:
            return jsonify({'error': 'Operation not found'}), 404

        return jsonify(status)

    except Exception as e:
        logger.error("Failed to get operation status",
                    operation_id=operation_id,
                    exception=e)
        return jsonify({'error': 'Failed to get operation status'}), 500


@batch_bp.route('/operations/<operation_id>/start', methods=['POST'])
def start_operation(operation_id):
    """Starte eine Batch-Operation"""
    try:
        success = batch_processor.start_batch_operation(operation_id)
        if not success:
            return jsonify({'error': 'Failed to start operation'}), 400

        logger.info("Batch operation started", operation_id=operation_id)
        return jsonify({'success': True, 'message': 'Operation started'})

    except Exception as e:
        logger.error("Failed to start batch operation",
                    operation_id=operation_id,
                    exception=e)
        return jsonify({'error': 'Failed to start operation'}), 500


@batch_bp.route('/operations/<operation_id>/cancel', methods=['POST'])
def cancel_operation(operation_id):
    """Brich eine Batch-Operation ab"""
    try:
        success = batch_processor.cancel_batch_operation(operation_id)
        if not success:
            return jsonify({'error': 'Failed to cancel operation'}), 400

        logger.info("Batch operation cancelled", operation_id=operation_id)
        return jsonify({'success': True, 'message': 'Operation cancelled'})

    except Exception as e:
        logger.error("Failed to cancel batch operation",
                    operation_id=operation_id,
                    exception=e)
        return jsonify({'error': 'Failed to cancel operation'}), 500


@batch_bp.route('/operations/<operation_id>', methods=['DELETE'])
def delete_operation(operation_id):
    """Lösche eine abgeschlossene Batch-Operation"""
    try:
        success = batch_processor.delete_operation(operation_id)
        if not success:
            return jsonify({'error': 'Failed to delete operation'}), 400

        logger.info("Batch operation deleted", operation_id=operation_id)
        return jsonify({'success': True, 'message': 'Operation deleted'})

    except Exception as e:
        logger.error("Failed to delete batch operation",
                    operation_id=operation_id,
                    exception=e)
        return jsonify({'error': 'Failed to delete operation'}), 500


@batch_bp.route('/quick-batch', methods=['POST'])
def create_quick_batch():
    """Erstelle und starte eine Batch-Operation für alle PDFs im Scan-Verzeichnis"""
    try:
        data = request.get_json() or {}
        target_category = data.get('target_category')
        name = data.get('name', f'Quick Batch - {Path(CONFIG["SCAN_DIR"]).name}')

        # Scan for all PDFs in scan directory
        scan_dir = Path(CONFIG['SCAN_DIR'])
        if not scan_dir.exists():
            return jsonify({'error': 'Scan directory not found'}), 404

        pdf_files = list(scan_dir.glob('*.pdf'))
        if not pdf_files:
            return jsonify({'error': 'No PDF files found in scan directory'}), 404

        file_paths = [str(pdf) for pdf in pdf_files]

        # Create and auto-start batch operation
        operation_id = batch_processor.create_batch_operation(
            name=name,
            file_paths=file_paths,
            auto_process=True,
            target_category=target_category
        )

        logger.info("Quick batch operation created and started",
                   operation_id=operation_id,
                   total_files=len(file_paths),
                   scan_dir=str(scan_dir))

        return jsonify({
            'operation_id': operation_id,
            'total_files': len(file_paths),
            'file_paths': file_paths,
            'auto_started': True
        })

    except Exception as e:
        logger.error("Failed to create quick batch", exception=e)
        return jsonify({'error': 'Failed to create quick batch'}), 500


@batch_bp.route('/status', methods=['GET'])
def batch_status():
    """Hole den aktuellen Status des Batch-Processors"""
    try:
        # Get worker status
        is_running = batch_processor.is_running
        worker_count = len(batch_processor.workers)
        queue_size = batch_processor.job_queue.qsize()

        # Get operation summaries
        operations = batch_processor.list_operations()

        running_operations = [op for op in operations if op['status'] == 'running']
        pending_operations = [op for op in operations if op['status'] == 'pending']
        completed_operations = [op for op in operations if op['status'] == 'completed']

        return jsonify({
            'processor_running': is_running,
            'worker_count': worker_count,
            'queue_size': queue_size,
            'operations_summary': {
                'total': len(operations),
                'running': len(running_operations),
                'pending': len(pending_operations),
                'completed': len(completed_operations)
            },
            'recent_operations': operations[:5]  # Last 5 operations
        })

    except Exception as e:
        logger.error("Failed to get batch status", exception=e)
        return jsonify({'error': 'Failed to get batch status'}), 500


@batch_bp.route('/workers/start', methods=['POST'])
def start_workers():
    """Starte die Batch-Worker"""
    try:
        if batch_processor.is_running:
            return jsonify({'message': 'Workers already running'}), 200

        batch_processor.start_workers()
        logger.info("Batch workers started manually")

        return jsonify({
            'success': True,
            'message': 'Workers started',
            'worker_count': len(batch_processor.workers)
        })

    except Exception as e:
        logger.error("Failed to start batch workers", exception=e)
        return jsonify({'error': 'Failed to start workers'}), 500


@batch_bp.route('/workers/stop', methods=['POST'])
def stop_workers():
    """Stoppe die Batch-Worker"""
    try:
        if not batch_processor.is_running:
            return jsonify({'message': 'Workers not running'}), 200

        batch_processor.stop_workers()
        logger.info("Batch workers stopped manually")

        return jsonify({
            'success': True,
            'message': 'Workers stopped'
        })

    except Exception as e:
        logger.error("Failed to stop batch workers", exception=e)
        return jsonify({'error': 'Failed to stop workers'}), 500