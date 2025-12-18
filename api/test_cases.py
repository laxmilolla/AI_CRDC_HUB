"""
Test case management API endpoints
"""
import uuid
from flask import Blueprint, request, jsonify
from core.test_case_generator import TestCaseGenerator
from core.story_processor import StoryProcessor
from utils.file_handler import FileHandler
from utils.logger import get_logger

bp = Blueprint('test_cases', __name__)
logger = get_logger(__name__)
test_case_generator = TestCaseGenerator()
story_processor = StoryProcessor()
file_handler = FileHandler()


@bp.route('/stories/<story_id>/generate-test-cases', methods=['POST'])
def generate_test_cases(story_id):
    """Generate test cases from user story"""
    try:
        # Load story
        story_content = file_handler.load_story(story_id)
        
        # Generate execution ID
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        # Generate test cases (async in background would be better)
        test_cases = test_case_generator.generate_test_cases(story_content, execution_id)
        
        logger.info(f"Generated {len(test_cases)} test cases for story {story_id}")
        
        return jsonify({
            'execution_id': execution_id,
            'status': 'ready',
            'test_cases_count': len(test_cases)
        }), 200
        
    except FileNotFoundError:
        return jsonify({'error': 'Story not found'}), 404
    except Exception as e:
        logger.error(f"Error generating test cases: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/test-cases/<execution_id>', methods=['GET'])
def get_test_cases(execution_id):
    """Get test cases for an execution"""
    try:
        test_cases = file_handler.load_test_cases(execution_id)
        
        return jsonify({
            'execution_id': execution_id,
            'test_cases': test_cases,
            'status': 'ready'
        }), 200
        
    except FileNotFoundError:
        return jsonify({'error': 'Test cases not found'}), 404
    except Exception as e:
        logger.error(f"Error getting test cases: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/test-cases/select', methods=['POST'])
def select_test_cases():
    """Save selected test case IDs"""
    try:
        data = request.json
        execution_id = data.get('execution_id')
        selected_ids = data.get('selected_ids', [])
        
        if not execution_id:
            return jsonify({'error': 'execution_id is required'}), 400
        
        if not selected_ids:
            return jsonify({'error': 'selected_ids is required'}), 400
        
        # Save selection
        file_handler.save_selection(execution_id, selected_ids)
        
        logger.info(f"Selected {len(selected_ids)} test cases for execution {execution_id}")
        
        return jsonify({
            'status': 'selected',
            'execution_id': execution_id,
            'count': len(selected_ids)
        }), 200
        
    except Exception as e:
        logger.error(f"Error selecting test cases: {e}")
        return jsonify({'error': str(e)}), 500

