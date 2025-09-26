"""
Document Templates API Blueprint
API endpoints for managing document templates and type recognition
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any

from ..ai.document_templates import document_template_engine, DocumentTemplate
from ..monitoring import get_logger

# Create blueprint
templates_bp = Blueprint('templates', __name__, url_prefix='/api/templates')

# Initialize logger
logger = get_logger('templates_api')


@templates_bp.route('/', methods=['GET'])
def list_templates():
    """Liste alle verfügbaren Templates auf"""
    try:
        templates = document_template_engine.get_templates()
        return jsonify({
            'templates': [_template_to_dict(t) for t in templates],
            'count': len(templates)
        })

    except Exception as e:
        logger.error("Failed to list templates", exception=e)
        return jsonify({'error': 'Failed to list templates'}), 500


@templates_bp.route('/types', methods=['GET'])
def list_document_types():
    """Liste alle verfügbaren Dokumenttypen auf"""
    try:
        templates = document_template_engine.get_templates()
        document_types = {}

        for template in templates:
            doc_type = template.document_type
            if doc_type not in document_types:
                document_types[doc_type] = {
                    'type': doc_type,
                    'templates': [],
                    'count': 0
                }

            document_types[doc_type]['templates'].append({
                'id': template.id,
                'name': template.name,
                'language': template.language,
                'priority': template.priority
            })
            document_types[doc_type]['count'] += 1

        return jsonify({
            'document_types': list(document_types.values()),
            'total_types': len(document_types)
        })

    except Exception as e:
        logger.error("Failed to list document types", exception=e)
        return jsonify({'error': 'Failed to list document types'}), 500


@templates_bp.route('/recognize', methods=['POST'])
def recognize_document():
    """Erkenne Dokumenttyp basierend auf Text"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        filename = data.get('filename', '')

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Recognize document type
        result = document_template_engine.recognize_document_type(text, filename)

        if result:
            response = {
                'recognized': True,
                'document_type': result.document_type,
                'template_id': result.template_id,
                'confidence': result.confidence,
                'matched_patterns': result.matched_patterns,
                'matched_keywords': result.matched_keywords,
                'structural_matches': result.structural_matches,
                'language': result.language,
                'metadata': result.metadata
            }

            logger.info("Document type recognized",
                       document_type=result.document_type,
                       template_id=result.template_id,
                       confidence=result.confidence)
        else:
            response = {
                'recognized': False,
                'message': 'No matching template found'
            }

            logger.info("No document type recognized", filename=filename)

        return jsonify(response)

    except Exception as e:
        logger.error("Failed to recognize document type", exception=e)
        return jsonify({'error': 'Failed to recognize document type'}), 500


@templates_bp.route('/', methods=['POST'])
def create_template():
    """Erstelle ein neues Template"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['id', 'name', 'document_type', 'patterns', 'keywords']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Create template
        template = DocumentTemplate(
            id=data['id'],
            name=data['name'],
            document_type=data['document_type'],
            patterns=data['patterns'],
            keywords=data['keywords'],
            structural_markers=data.get('structural_markers', []),
            language=data.get('language', 'de'),
            confidence_threshold=data.get('confidence_threshold', 0.7),
            priority=data.get('priority', 1)
        )

        # Add template
        success = document_template_engine.add_template(template)

        if success:
            logger.info("Template created successfully",
                       template_id=template.id,
                       document_type=template.document_type)
            return jsonify({
                'success': True,
                'template': _template_to_dict(template)
            }), 201
        else:
            return jsonify({'error': 'Failed to add template (ID might already exist)'}), 400

    except Exception as e:
        logger.error("Failed to create template", exception=e)
        return jsonify({'error': 'Failed to create template'}), 500


@templates_bp.route('/<template_id>', methods=['GET'])
def get_template(template_id):
    """Hole spezifisches Template"""
    try:
        templates = document_template_engine.get_templates()
        template = next((t for t in templates if t.id == template_id), None)

        if not template:
            return jsonify({'error': 'Template not found'}), 404

        return jsonify(_template_to_dict(template))

    except Exception as e:
        logger.error("Failed to get template", template_id=template_id, exception=e)
        return jsonify({'error': 'Failed to get template'}), 500


@templates_bp.route('/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Lösche Template"""
    try:
        success = document_template_engine.remove_template(template_id)

        if success:
            logger.info("Template deleted successfully", template_id=template_id)
            return jsonify({'success': True, 'message': 'Template deleted'})
        else:
            return jsonify({'error': 'Template not found'}), 404

    except Exception as e:
        logger.error("Failed to delete template", template_id=template_id, exception=e)
        return jsonify({'error': 'Failed to delete template'}), 500


@templates_bp.route('/type/<document_type>', methods=['GET'])
def get_templates_by_type(document_type):
    """Hole alle Templates für einen Dokumenttyp"""
    try:
        templates = document_template_engine.get_templates_by_type(document_type)

        return jsonify({
            'document_type': document_type,
            'templates': [_template_to_dict(t) for t in templates],
            'count': len(templates)
        })

    except Exception as e:
        logger.error("Failed to get templates by type",
                    document_type=document_type,
                    exception=e)
        return jsonify({'error': 'Failed to get templates by type'}), 500


@templates_bp.route('/test', methods=['POST'])
def test_template():
    """Teste Template gegen Beispieltext"""
    try:
        data = request.get_json()
        template_id = data.get('template_id')
        text = data.get('text', '')

        if not template_id or not text:
            return jsonify({'error': 'Missing template_id or text'}), 400

        # Get template
        templates = document_template_engine.get_templates()
        template = next((t for t in templates if t.id == template_id), None)

        if not template:
            return jsonify({'error': 'Template not found'}), 404

        # Test template
        result = document_template_engine._match_template(template, text, "")

        if result:
            response = {
                'match': True,
                'confidence': result.confidence,
                'matched_patterns': result.matched_patterns,
                'matched_keywords': result.matched_keywords,
                'structural_matches': result.structural_matches,
                'metadata': result.metadata
            }
        else:
            response = {
                'match': False,
                'confidence': 0.0,
                'matched_patterns': [],
                'matched_keywords': [],
                'structural_matches': [],
                'metadata': {}
            }

        return jsonify(response)

    except Exception as e:
        logger.error("Failed to test template", exception=e)
        return jsonify({'error': 'Failed to test template'}), 500


@templates_bp.route('/stats', methods=['GET'])
def get_template_stats():
    """Hole Template-Statistiken"""
    try:
        templates = document_template_engine.get_templates()

        stats = {
            'total_templates': len(templates),
            'by_document_type': {},
            'by_language': {},
            'by_priority': {},
            'average_confidence_threshold': 0.0
        }

        for template in templates:
            # Document type stats
            doc_type = template.document_type
            if doc_type not in stats['by_document_type']:
                stats['by_document_type'][doc_type] = 0
            stats['by_document_type'][doc_type] += 1

            # Language stats
            lang = template.language
            if lang not in stats['by_language']:
                stats['by_language'][lang] = 0
            stats['by_language'][lang] += 1

            # Priority stats
            priority = template.priority
            if priority not in stats['by_priority']:
                stats['by_priority'][priority] = 0
            stats['by_priority'][priority] += 1

        # Average confidence threshold
        if templates:
            stats['average_confidence_threshold'] = sum(t.confidence_threshold for t in templates) / len(templates)

        return jsonify(stats)

    except Exception as e:
        logger.error("Failed to get template stats", exception=e)
        return jsonify({'error': 'Failed to get template stats'}), 500


def _template_to_dict(template: DocumentTemplate) -> Dict[str, Any]:
    """Konvertiere Template zu Dictionary"""
    return {
        'id': template.id,
        'name': template.name,
        'document_type': template.document_type,
        'patterns': template.patterns,
        'keywords': template.keywords,
        'structural_markers': template.structural_markers,
        'language': template.language,
        'confidence_threshold': template.confidence_threshold,
        'priority': template.priority,
        'created_at': template.created_at
    }