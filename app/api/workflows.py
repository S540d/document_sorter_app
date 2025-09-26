"""
Workflow Management API Blueprint
API endpoints for managing workflow rules and automation
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any

from ..services.workflow_engine import workflow_engine, WorkflowRule
from ..monitoring import get_logger

# Create blueprint
workflows_bp = Blueprint('workflows', __name__, url_prefix='/api/workflows')

# Initialize logger
logger = get_logger('workflows_api')


@workflows_bp.route('/rules', methods=['GET'])
def list_rules():
    """Liste alle Workflow-Regeln auf"""
    try:
        rules = workflow_engine.get_rules()
        return jsonify({
            'rules': [_rule_to_dict(r) for r in rules],
            'count': len(rules)
        })

    except Exception as e:
        logger.error("Failed to list workflow rules", exception=e)
        return jsonify({'error': 'Failed to list workflow rules'}), 500


@workflows_bp.route('/rules', methods=['POST'])
def create_rule():
    """Erstelle neue Workflow-Regel"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['id', 'name', 'conditions', 'actions']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Create rule
        rule = WorkflowRule(
            id=data['id'],
            name=data['name'],
            conditions=data['conditions'],
            actions=data['actions'],
            priority=data.get('priority', 1),
            enabled=data.get('enabled', True)
        )

        # Add rule
        success = workflow_engine.add_rule(rule)

        if success:
            logger.info("Workflow rule created successfully",
                       rule_id=rule.id,
                       name=rule.name)
            return jsonify({
                'success': True,
                'rule': _rule_to_dict(rule)
            }), 201
        else:
            return jsonify({'error': 'Failed to add rule (ID might already exist)'}), 400

    except Exception as e:
        logger.error("Failed to create workflow rule", exception=e)
        return jsonify({'error': 'Failed to create workflow rule'}), 500


@workflows_bp.route('/rules/<rule_id>', methods=['GET'])
def get_rule(rule_id):
    """Hole spezifische Workflow-Regel"""
    try:
        rules = workflow_engine.get_rules()
        rule = next((r for r in rules if r.id == rule_id), None)

        if not rule:
            return jsonify({'error': 'Rule not found'}), 404

        return jsonify(_rule_to_dict(rule))

    except Exception as e:
        logger.error("Failed to get workflow rule", rule_id=rule_id, exception=e)
        return jsonify({'error': 'Failed to get workflow rule'}), 500


@workflows_bp.route('/rules/<rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    """Lösche Workflow-Regel"""
    try:
        success = workflow_engine.remove_rule(rule_id)

        if success:
            logger.info("Workflow rule deleted successfully", rule_id=rule_id)
            return jsonify({'success': True, 'message': 'Rule deleted'})
        else:
            return jsonify({'error': 'Rule not found'}), 404

    except Exception as e:
        logger.error("Failed to delete workflow rule", rule_id=rule_id, exception=e)
        return jsonify({'error': 'Failed to delete workflow rule'}), 500


@workflows_bp.route('/process', methods=['POST'])
def process_document():
    """Verarbeite Dokument mit Workflow Engine"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        context = data.get('context', {})

        if not file_path:
            return jsonify({'error': 'Missing file_path'}), 400

        # Process document
        result = workflow_engine.process_document(file_path, context)

        response = {
            'success': result.success,
            'action_taken': result.action_taken.value,
            'target_category': result.target_category,
            'target_path': result.target_path,
            'confidence': result.confidence,
            'applied_rules': result.applied_rules,
            'processing_time': result.processing_time,
            'metadata': result.metadata
        }

        # Add template information if available
        if result.template_result:
            response['template_recognition'] = {
                'document_type': result.template_result.document_type,
                'template_id': result.template_result.template_id,
                'confidence': result.template_result.confidence,
                'matched_keywords': result.template_result.matched_keywords,
                'metadata': result.template_result.metadata
            }

        # Add AI classification if available
        if result.ai_result:
            response['ai_classification'] = result.ai_result

        logger.info("Document processed via workflow API",
                   file_path=file_path,
                   action_taken=result.action_taken.value,
                   success=result.success)

        return jsonify(response)

    except Exception as e:
        logger.error("Failed to process document via workflow",
                    file_path=file_path if 'file_path' in locals() else 'unknown',
                    exception=e)
        return jsonify({'error': 'Failed to process document'}), 500


@workflows_bp.route('/test', methods=['POST'])
def test_workflow():
    """Teste Workflow-Regeln gegen Beispieldokument"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        context = data.get('context', {})

        if not file_path:
            return jsonify({'error': 'Missing file_path'}), 400

        # Simulate workflow processing (dry run)
        # Extract document info for rule evaluation
        from pathlib import Path
        from ..ai.document_templates import document_template_engine

        file_path_obj = Path(file_path)

        # Get template recognition (if file exists)
        template_result = None
        if file_path_obj.exists():
            try:
                from ..pdf import PDFProcessor
                pdf_processor = PDFProcessor(max_pages=1)
                text = pdf_processor.extract_text(file_path)
                template_result = document_template_engine.recognize_document_type(text, file_path_obj.name)
            except Exception:
                pass

        # Evaluate rules
        applicable_rules = workflow_engine._evaluate_rules(file_path_obj, template_result, context)

        # Determine action
        action = workflow_engine._determine_action(applicable_rules, template_result)

        response = {
            'file_path': file_path,
            'applicable_rules': [_rule_to_dict(r) for r in applicable_rules],
            'determined_action': action.value,
            'context': context
        }

        if template_result:
            response['template_recognition'] = {
                'document_type': template_result.document_type,
                'template_id': template_result.template_id,
                'confidence': template_result.confidence
            }

        return jsonify(response)

    except Exception as e:
        logger.error("Failed to test workflow", exception=e)
        return jsonify({'error': 'Failed to test workflow'}), 500


@workflows_bp.route('/stats', methods=['GET'])
def get_workflow_stats():
    """Hole Workflow-Statistiken"""
    try:
        rules = workflow_engine.get_rules()

        stats = {
            'total_rules': len(rules),
            'enabled_rules': len([r for r in rules if r.enabled]),
            'disabled_rules': len([r for r in rules if not r.enabled]),
            'by_priority': {},
            'action_types': {}
        }

        for rule in rules:
            # Priority stats
            priority = rule.priority
            if priority not in stats['by_priority']:
                stats['by_priority'][priority] = 0
            stats['by_priority'][priority] += 1

            # Action type stats
            for action in rule.actions:
                action_type = action.get('type', 'unknown')
                if action_type not in stats['action_types']:
                    stats['action_types'][action_type] = 0
                stats['action_types'][action_type] += 1

        return jsonify(stats)

    except Exception as e:
        logger.error("Failed to get workflow stats", exception=e)
        return jsonify({'error': 'Failed to get workflow stats'}), 500


@workflows_bp.route('/actions', methods=['GET'])
def list_available_actions():
    """Liste verfügbare Workflow-Aktionen auf"""
    try:
        actions = [
            {
                'type': 'classify',
                'name': 'Auto-classify with AI',
                'description': 'Use AI and templates for automatic classification',
                'parameters': []
            },
            {
                'type': 'force_category',
                'name': 'Force specific category',
                'description': 'Force document into a specific category',
                'parameters': [
                    {'name': 'category', 'type': 'string', 'required': True}
                ]
            },
            {
                'type': 'manual_review',
                'name': 'Manual review',
                'description': 'Mark document for manual review',
                'parameters': []
            },
            {
                'type': 'skip',
                'name': 'Skip processing',
                'description': 'Skip document processing entirely',
                'parameters': []
            }
        ]

        return jsonify({'actions': actions})

    except Exception as e:
        logger.error("Failed to list available actions", exception=e)
        return jsonify({'error': 'Failed to list available actions'}), 500


@workflows_bp.route('/conditions', methods=['GET'])
def list_available_conditions():
    """Liste verfügbare Workflow-Bedingungen auf"""
    try:
        conditions = [
            {
                'name': 'document_type',
                'type': 'array',
                'description': 'Match specific document types from template recognition',
                'examples': ['invoice', 'contract', 'bank_statement']
            },
            {
                'name': 'min_template_confidence',
                'type': 'number',
                'description': 'Minimum template recognition confidence (0.0-1.0)',
                'examples': [0.8, 0.6, 0.9]
            },
            {
                'name': 'filename_patterns',
                'type': 'array',
                'description': 'Match filename patterns (case-insensitive)',
                'examples': ['invoice', 'rechnung', 'contract']
            },
            {
                'name': 'file_extensions',
                'type': 'array',
                'description': 'Match file extensions',
                'examples': ['.pdf', '.docx', '.txt']
            },
            {
                'name': 'batch_mode',
                'type': 'boolean',
                'description': 'Match only batch or interactive processing',
                'examples': [True, False]
            }
        ]

        return jsonify({'conditions': conditions})

    except Exception as e:
        logger.error("Failed to list available conditions", exception=e)
        return jsonify({'error': 'Failed to list available conditions'}), 500


def _rule_to_dict(rule: WorkflowRule) -> Dict[str, Any]:
    """Konvertiere WorkflowRule zu Dictionary"""
    return {
        'id': rule.id,
        'name': rule.name,
        'conditions': rule.conditions,
        'actions': rule.actions,
        'priority': rule.priority,
        'enabled': rule.enabled,
        'created_at': rule.created_at
    }