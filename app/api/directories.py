"""
Directory Management API Blueprint
Handles directory operations and path suggestions
"""

import os
from flask import Blueprint, request, jsonify, render_template

from ..settings import CONFIG
from ..directory import DirectoryManager, CategoryManager

# Create blueprint
directories_bp = Blueprint('directories', __name__)

# Initialize components
directory_manager = DirectoryManager()
category_manager = CategoryManager()


@directories_bp.route('/api/suggest-subdirs', methods=['POST'])
def suggest_subdirs():
    """API: Unterverzeichnisse zu Kategorie vorschlagen"""
    data = request.get_json()
    category = data.get('category', '')
    if not category:
        return jsonify({'error': 'Keine Kategorie angegeben'}), 400

    # Use category manager to get subdirectories
    subdirs = category_manager.get_subdirectories(category)
    return jsonify({'subdirs': subdirs})


@directories_bp.route('/api/directory-structure')
def directory_structure():
    """Verzeichnisstruktur für Frontend mit Blacklist-Filter"""
    tree = category_manager.get_directory_tree()
    return jsonify({
        'structure': tree,
        'base_path': CONFIG['SORTED_DIR']
    })


@directories_bp.route('/api/suggest-alternative-paths', methods=['POST'])
def suggest_alternative_paths():
    """Schlägt alternative Zielpfade vor"""
    data = request.get_json()
    filename = data.get('filename', '')

    # Intelligente Pfadvorschläge basierend auf existierenden Verzeichnissen
    categories = category_manager.get_smart_categories()
    suggestions = directory_manager.suggest_alternative_paths(filename, categories)

    return jsonify({'suggestions': suggestions})


@directories_bp.route('/path-management')
def path_management():
    """Neue Route für Pfad-Management-Seite"""
    return render_template('path_management.html')


@directories_bp.route('/api/suggest-similar-paths', methods=['POST'])
def suggest_similar_paths():
    """API für ähnliche Pfade und Kombinationsvorschläge"""
    data = request.get_json()
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'error': 'Kein Dateiname angegeben'}), 400

    # Hole alle Kategorien/Verzeichnisse
    categories = category_manager.get_smart_categories()
    similar_paths = []
    combinations = []

    # Suche existierende Verzeichnisse im SORTED_DIR (max. 2 Ebenen tief)
    existing_dirs = []
    for root, dirs, files in os.walk(CONFIG['SORTED_DIR']):
        depth = root[len(CONFIG['SORTED_DIR']):].count(os.sep)
        if depth <= 2:
            for d in dirs:
                dir_path = os.path.join(root, d)
                if d not in CONFIG['BLACKLIST_DIRS']:
                    existing_dirs.append(dir_path)

    # String-Similarity für Kategorien
    for cat in categories:
        similarity = 1.0 if cat.lower() in filename.lower() else 0.5 if filename.lower()[:3] in cat.lower() else 0.2
        path = os.path.join(CONFIG['SORTED_DIR'], cat, filename)
        similar_paths.append({
            'directory': cat,
            'path': path,
            'similarity': similarity
        })

    # String-Similarity für existierende Verzeichnisse
    for dir_path in existing_dirs:
        dir_name = os.path.basename(dir_path)
        similarity = 1.0 if dir_name.lower() in filename.lower() else 0.5 if filename.lower()[:3] in dir_name.lower() else 0.2
        path = os.path.join(dir_path, filename)
        similar_paths.append({
            'directory': dir_name,
            'path': path,
            'similarity': similarity
        })

    # Kombinationsvorschläge: Jede Kategorie mit jeder anderen
    for i, cat_a in enumerate(categories):
        for j, cat_b in enumerate(categories):
            if i != j:
                combined_path_ab = os.path.join(CONFIG['SORTED_DIR'], cat_a, cat_b, filename)
                combined_path_ba = os.path.join(CONFIG['SORTED_DIR'], cat_b, cat_a, filename)
                combined_similarity = (similar_paths[i]['similarity'] + similar_paths[j]['similarity']) / 2
                combinations.append({
                    'path_a': similar_paths[i],
                    'path_b': similar_paths[j],
                    'combined_path_ab': combined_path_ab,
                    'combined_path_ba': combined_path_ba,
                    'combined_similarity': combined_similarity
                })

    return jsonify({
        'similar_paths': similar_paths,
        'combinations': combinations
    })


@directories_bp.route('/api/directory-stats')
def directory_stats():
    """Get directory statistics"""
    stats = category_manager.get_category_stats()
    dir_info = directory_manager.get_directory_info()

    return jsonify({
        'category_stats': stats,
        'directory_info': dir_info
    })


@directories_bp.route('/api/create-category', methods=['POST'])
def create_category():
    """Create new category directory"""
    data = request.get_json()
    category = data.get('category', '').strip()

    if not category:
        return jsonify({'error': 'Category name required'}), 400

    success = category_manager.create_category_if_not_exists(category)

    if success:
        return jsonify({
            'success': True,
            'message': f'Category "{category}" created successfully'
        })
    else:
        return jsonify({
            'error': f'Failed to create category "{category}"'
        }), 500


@directories_bp.route('/api/validate-category/<category>')
def validate_category(category):
    """Validate if category exists and is valid"""
    is_valid = category_manager.validate_category(category)

    return jsonify({
        'valid': is_valid,
        'category': category
    })


@directories_bp.route('/api/cleanup-empty-dirs', methods=['POST'])
def cleanup_empty_directories():
    """Remove empty directories"""
    result = directory_manager.cleanup_empty_directories()

    return jsonify(result)