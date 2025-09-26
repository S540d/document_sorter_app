"""
Batch Processing Service für Document Sorter
Implementiert Queue-basierte Batch-Verarbeitung mit Progress-Tracking
"""

import json
import time
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue
from threading import Thread, Lock
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict

from ..monitoring import get_logger
from ..pdf import PDFProcessor, PDFPreviewGenerator
from ..ai import DocumentClassifier
from ..directory import CategoryManager, DirectoryManager
from ..services.file_renaming import file_renaming_service
from ..services.workflow_engine import workflow_engine


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Einzelner Job in der Batch-Verarbeitung"""
    id: str
    file_path: str
    target_category: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    progress: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class BatchOperation:
    """Batch-Operation mit mehreren Jobs"""
    id: str
    name: str
    jobs: List[BatchJob]
    status: JobStatus = JobStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    progress: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.total_jobs = len(self.jobs)


class BatchProcessor:
    """Service für Batch-Verarbeitung von Dokumenten"""

    def __init__(self, max_workers: int = 3):
        self.logger = get_logger('batch_processor')
        self.max_workers = max_workers
        self.workers = []
        self.job_queue = Queue()
        self.operations: Dict[str, BatchOperation] = {}
        self.operations_lock = Lock()
        self.is_running = False

        # Initialize processors
        self.pdf_processor = PDFProcessor(max_pages=3)
        self.preview_generator = PDFPreviewGenerator(dpi=1.5)
        self.document_classifier = DocumentClassifier()
        self.category_manager = CategoryManager()
        self.directory_manager = DirectoryManager()

        # Storage for persistent state
        self.state_file = Path("batch_operations.json")
        self._load_state()

    def start_workers(self):
        """Startet die Worker-Threads"""
        if self.is_running:
            return

        self.is_running = True
        for i in range(self.max_workers):
            worker = Thread(target=self._worker_loop, name=f"BatchWorker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)

        self.logger.info("Batch processor started", workers=self.max_workers)

    def stop_workers(self):
        """Stoppt die Worker-Threads"""
        self.is_running = False

        # Add sentinel values to wake up workers
        for _ in range(self.max_workers):
            self.job_queue.put(None)

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5.0)

        self.workers.clear()
        self.logger.info("Batch processor stopped")

    def create_batch_operation(self,
                             name: str,
                             file_paths: List[str],
                             auto_process: bool = False,
                             target_category: Optional[str] = None) -> str:
        """Erstellt eine neue Batch-Operation"""
        operation_id = str(uuid.uuid4())

        # Create jobs for each file
        jobs = []
        for file_path in file_paths:
            job_id = str(uuid.uuid4())
            job = BatchJob(
                id=job_id,
                file_path=file_path,
                target_category=target_category
            )
            jobs.append(job)

        # Create operation
        operation = BatchOperation(
            id=operation_id,
            name=name,
            jobs=jobs
        )

        with self.operations_lock:
            self.operations[operation_id] = operation

        self.logger.info("Batch operation created",
                        operation_id=operation_id,
                        name=name,
                        total_jobs=len(jobs))

        if auto_process:
            self.start_batch_operation(operation_id)

        self._save_state()
        return operation_id

    def start_batch_operation(self, operation_id: str) -> bool:
        """Startet eine Batch-Operation"""
        with self.operations_lock:
            operation = self.operations.get(operation_id)
            if not operation:
                return False

            if operation.status != JobStatus.PENDING:
                return False

            operation.status = JobStatus.RUNNING
            operation.started_at = datetime.now().isoformat()

        # Ensure workers are running
        if not self.is_running:
            self.start_workers()

        # Queue all jobs
        for job in operation.jobs:
            self.job_queue.put((operation_id, job.id))

        self.logger.info("Batch operation started", operation_id=operation_id)
        self._save_state()
        return True

    def cancel_batch_operation(self, operation_id: str) -> bool:
        """Bricht eine Batch-Operation ab"""
        with self.operations_lock:
            operation = self.operations.get(operation_id)
            if not operation:
                return False

            operation.status = JobStatus.CANCELLED
            operation.completed_at = datetime.now().isoformat()

            # Cancel pending jobs
            for job in operation.jobs:
                if job.status == JobStatus.PENDING:
                    job.status = JobStatus.CANCELLED

        self.logger.info("Batch operation cancelled", operation_id=operation_id)
        self._save_state()
        return True

    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Gibt den Status einer Batch-Operation zurück"""
        with self.operations_lock:
            operation = self.operations.get(operation_id)
            if not operation:
                return None

            return {
                'id': operation.id,
                'name': operation.name,
                'status': operation.status.value,
                'created_at': operation.created_at,
                'started_at': operation.started_at,
                'completed_at': operation.completed_at,
                'total_jobs': operation.total_jobs,
                'completed_jobs': operation.completed_jobs,
                'failed_jobs': operation.failed_jobs,
                'progress': operation.progress,
                'jobs': [self._job_to_dict(job) for job in operation.jobs]
            }

    def list_operations(self, status_filter: Optional[JobStatus] = None) -> List[Dict[str, Any]]:
        """Listet alle Batch-Operationen auf"""
        with self.operations_lock:
            operations = []
            for operation in self.operations.values():
                if status_filter is None or operation.status == status_filter:
                    operations.append({
                        'id': operation.id,
                        'name': operation.name,
                        'status': operation.status.value,
                        'created_at': operation.created_at,
                        'started_at': operation.started_at,
                        'completed_at': operation.completed_at,
                        'total_jobs': operation.total_jobs,
                        'completed_jobs': operation.completed_jobs,
                        'failed_jobs': operation.failed_jobs,
                        'progress': operation.progress
                    })

            return sorted(operations, key=lambda x: x['created_at'], reverse=True)

    def delete_operation(self, operation_id: str) -> bool:
        """Löscht eine abgeschlossene Batch-Operation"""
        with self.operations_lock:
            operation = self.operations.get(operation_id)
            if not operation:
                return False

            if operation.status in [JobStatus.RUNNING]:
                return False

            del self.operations[operation_id]

        self.logger.info("Batch operation deleted", operation_id=operation_id)
        self._save_state()
        return True

    def _worker_loop(self):
        """Haupt-Loop für Worker-Threads"""
        while self.is_running:
            try:
                item = self.job_queue.get(timeout=1.0)
                if item is None:  # Sentinel value
                    break

                operation_id, job_id = item
                self._process_job(operation_id, job_id)

            except Exception as e:
                self.logger.error("Worker error", exception=e)

    def _process_job(self, operation_id: str, job_id: str):
        """Verarbeitet einen einzelnen Job"""
        with self.operations_lock:
            operation = self.operations.get(operation_id)
            if not operation:
                return

            job = next((j for j in operation.jobs if j.id == job_id), None)
            if not job:
                return

            if job.status != JobStatus.PENDING:
                return

            job.status = JobStatus.RUNNING
            job.started_at = datetime.now().isoformat()

        try:
            # Process the document
            result = self._process_document(job.file_path, job.target_category)

            with self.operations_lock:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now().isoformat()
                job.result = result
                job.progress = 100.0

                operation.completed_jobs += 1
                self._update_operation_progress(operation)

            self.logger.info("Job completed successfully",
                           operation_id=operation_id,
                           job_id=job_id,
                           file_path=job.file_path)

        except Exception as e:
            with self.operations_lock:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now().isoformat()
                job.error_message = str(e)

                operation.failed_jobs += 1
                self._update_operation_progress(operation)

            self.logger.error("Job failed",
                            operation_id=operation_id,
                            job_id=job_id,
                            file_path=job.file_path,
                            exception=e)

        self._save_state()

    def _process_document(self, file_path: str, target_category: Optional[str] = None) -> Dict[str, Any]:
        """Verarbeitet ein einzelnes Dokument mit Workflow Engine"""
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate preview for result
        preview = self.preview_generator.generate_preview(file_path)

        # Use Workflow Engine for intelligent processing
        workflow_context = {
            'is_batch': True,
            'target_category': target_category,
            'batch_mode': True
        }

        workflow_result = workflow_engine.process_document(file_path, workflow_context)

        # Extract text for result (if not already done)
        try:
            text = self.pdf_processor.extract_text(file_path)
            text_length = len(text)
        except Exception:
            text_length = 0

        # Build result dictionary
        result = {
            'original_path': file_path,
            'target_path': workflow_result.target_path,
            'category': workflow_result.target_category,
            'workflow_action': workflow_result.action_taken.value,
            'workflow_success': workflow_result.success,
            'confidence': workflow_result.confidence,
            'applied_rules': workflow_result.applied_rules,
            'move_success': workflow_result.success,
            'preview': preview,
            'text_length': text_length,
            'processing_time': workflow_result.processing_time
        }

        # Add template information if available
        if workflow_result.template_result:
            result['template_recognition'] = {
                'document_type': workflow_result.template_result.document_type,
                'template_id': workflow_result.template_result.template_id,
                'template_confidence': workflow_result.template_result.confidence,
                'matched_keywords': workflow_result.template_result.matched_keywords,
                'metadata': workflow_result.template_result.metadata
            }

        # Add AI classification if available
        if workflow_result.ai_result:
            result['ai_classification'] = workflow_result.ai_result

        # Add subdirectory info
        if workflow_result.target_path:
            target_path_obj = Path(workflow_result.target_path)
            if len(target_path_obj.parts) > 3:  # More than just sorted_dir/category/file
                result['subdirectory'] = target_path_obj.parent.name
            else:
                result['subdirectory'] = ''

        # Add workflow metadata
        result['workflow_metadata'] = workflow_result.metadata

        return result

    def _update_operation_progress(self, operation: BatchOperation):
        """Aktualisiert den Progress einer Operation"""
        total_processed = operation.completed_jobs + operation.failed_jobs
        operation.progress = (total_processed / operation.total_jobs) * 100.0

        # Check if operation is complete
        if total_processed >= operation.total_jobs:
            operation.status = JobStatus.COMPLETED
            operation.completed_at = datetime.now().isoformat()

    def _job_to_dict(self, job: BatchJob) -> Dict[str, Any]:
        """Konvertiert Job zu Dictionary"""
        return {
            'id': job.id,
            'file_path': job.file_path,
            'target_category': job.target_category,
            'status': job.status.value,
            'created_at': job.created_at,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'error_message': job.error_message,
            'result': job.result,
            'progress': job.progress
        }

    def _save_state(self):
        """Speichert den aktuellen Zustand persistent"""
        try:
            state = {}
            with self.operations_lock:
                for op_id, operation in self.operations.items():
                    state[op_id] = {
                        'id': operation.id,
                        'name': operation.name,
                        'status': operation.status.value,
                        'created_at': operation.created_at,
                        'started_at': operation.started_at,
                        'completed_at': operation.completed_at,
                        'total_jobs': operation.total_jobs,
                        'completed_jobs': operation.completed_jobs,
                        'failed_jobs': operation.failed_jobs,
                        'progress': operation.progress,
                        'jobs': [self._job_to_dict(job) for job in operation.jobs]
                    }

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error("Failed to save batch processor state", exception=e)

    def _load_state(self):
        """Lädt den gespeicherten Zustand"""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            with self.operations_lock:
                for op_id, op_data in state.items():
                    jobs = []
                    for job_data in op_data.get('jobs', []):
                        job = BatchJob(
                            id=job_data['id'],
                            file_path=job_data['file_path'],
                            target_category=job_data.get('target_category'),
                            status=JobStatus(job_data['status']),
                            created_at=job_data['created_at'],
                            started_at=job_data.get('started_at'),
                            completed_at=job_data.get('completed_at'),
                            error_message=job_data.get('error_message'),
                            result=job_data.get('result'),
                            progress=job_data.get('progress', 0.0)
                        )
                        jobs.append(job)

                    operation = BatchOperation(
                        id=op_data['id'],
                        name=op_data['name'],
                        jobs=jobs,
                        status=JobStatus(op_data['status']),
                        created_at=op_data['created_at'],
                        started_at=op_data.get('started_at'),
                        completed_at=op_data.get('completed_at'),
                        total_jobs=op_data['total_jobs'],
                        completed_jobs=op_data['completed_jobs'],
                        failed_jobs=op_data['failed_jobs'],
                        progress=op_data['progress']
                    )

                    self.operations[op_id] = operation

            self.logger.info("Batch processor state loaded", operations=len(self.operations))

        except Exception as e:
            self.logger.error("Failed to load batch processor state", exception=e)


# Global instance
batch_processor = BatchProcessor()