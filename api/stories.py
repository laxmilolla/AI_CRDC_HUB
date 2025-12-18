"""
Story management API endpoints
"""
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from core.story_processor import StoryProcessor
from utils.file_handler import FileHandler
from utils.validators import validate_story_format, validate_file_upload
from utils.logger import get_logger
from pathlib import Path

bp = Blueprint('stories', __name__)
logger = get_logger(__name__)
story_processor = StoryProcessor()
file_handler = FileHandler()


@bp.route('/stories', methods=['POST'])
def upload_story():
    """Upload user story (file or text)"""
    try:
        story_content = None
        story_id = f"story_{uuid.uuid4().hex[:8]}"
        
        # Check if file upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename:
                # Validate file
                file_path = Path(secure_filename(file.filename))
                is_valid, error = validate_file_upload(file_path)
                if not is_valid:
                    return jsonify({'error': error}), 400
                
                story_content = file.read().decode('utf-8')
        
        # Check if text content
        elif 'story' in request.json:
            story_content = request.json['story']
        
        # Check if form data
        elif 'story' in request.form:
            story_content = request.form['story']
        
        if not story_content:
            return jsonify({'error': 'No story content provided'}), 400
        
        # Validate story format
        is_valid, error = validate_story_format(story_content)
        if not is_valid:
            return jsonify({'error': error}), 400
        
        # Parse and save story
        parsed_story = story_processor.parse_story(story_content)
        file_handler.save_story(story_id, story_content)
        
        logger.info(f"Story uploaded: {story_id}")
        
        return jsonify({
            'story_id': story_id,
            'status': 'uploaded',
            'scenarios_count': len(parsed_story.get('scenarios', []))
        }), 201
        
    except Exception as e:
        logger.error(f"Error uploading story: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/stories/<story_id>', methods=['GET'])
def get_story(story_id):
    """Get user story by ID"""
    try:
        content = file_handler.load_story(story_id)
        parsed = story_processor.parse_story(content)
        
        return jsonify({
            'id': story_id,
            'content': content,
            'scenarios': parsed.get('scenarios', []),
            'user_type': parsed.get('user_type'),
            'actions': parsed.get('actions', [])
        }), 200
        
    except FileNotFoundError:
        return jsonify({'error': 'Story not found'}), 404
    except Exception as e:
        logger.error(f"Error getting story: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/stories', methods=['GET'])
def list_stories():
    """List all stories"""
    try:
        stories_dir = Path('data/stories')
        stories = []
        
        if stories_dir.exists():
            for file in stories_dir.glob('story_*.txt'):
                story_id = file.stem.replace('story_', '')
                try:
                    content = file_handler.load_story(story_id)
                    parsed = story_processor.parse_story(content)
                    stories.append({
                        'id': story_id,
                        'scenarios_count': len(parsed.get('scenarios', [])),
                        'preview': content[:200] + '...' if len(content) > 200 else content
                    })
                except Exception:
                    continue
        
        return jsonify({'stories': stories}), 200
        
    except Exception as e:
        logger.error(f"Error listing stories: {e}")
        return jsonify({'error': str(e)}), 500

