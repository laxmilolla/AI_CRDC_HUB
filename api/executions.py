"""
Test execution API endpoints
"""
from flask import Blueprint, request, jsonify
from core.execution_manager import ExecutionManager
from core.code_generator import CodeGenerator
from utils.file_handler import FileHandler
from utils.logger import get_logger
import threading

bp = Blueprint('executions', __name__)
logger = get_logger(__name__)
execution_manager = ExecutionManager()
code_generator = CodeGenerator()
file_handler = FileHandler()


@bp.route('/executions', methods=['POST'])
def start_execution():
    """Start test execution"""
    try:
        data = request.json
        execution_id = data.get('execution_id')
        
        if not execution_id:
            return jsonify({'error': 'execution_id is required'}), 400
        
        # Get selected test cases
        selected_ids = file_handler.load_selection(execution_id)
        if not selected_ids:
            return jsonify({'error': 'No test cases selected'}), 400
        
        # Get all test cases
        all_test_cases = file_handler.load_test_cases(execution_id)
        
        # Filter selected test cases
        selected_test_cases = [
            tc for tc in all_test_cases 
            if tc.get('id') in selected_ids
        ]
        
        if not selected_test_cases:
            return jsonify({'error': 'Selected test cases not found'}), 404
        
        # Generate Playwright code
        playwright_code = code_generator.generate_playwright_code(
            selected_test_cases,
            execution_id
        )
        
        # Start execution in background thread
        # This allows the API to return immediately while execution runs
        def run_execution():
            try:
                execution_manager.execute_tests(
                    playwright_code,
                    execution_id,
                    selected_test_cases
                )
            except Exception as e:
                logger.error(f"Execution error: {e}")
                execution_manager.handle_execution_errors(e, execution_id)
        
        execution_thread = threading.Thread(target=run_execution, daemon=True)
        execution_thread.start()
        
        logger.info(f"Execution started: {execution_id}")
        
        return jsonify({
            'execution_id': execution_id,
            'status': 'started'
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting execution: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/executions/<execution_id>/status', methods=['GET'])
def get_execution_status(execution_id):
    """Get execution status and progress"""
    try:
        status = execution_manager.monitor_execution(execution_id)
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error getting execution status: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/executions/<execution_id>/results', methods=['GET'])
def get_execution_results(execution_id):
    """Get execution results"""
    try:
        results = file_handler.load_results(execution_id)
        
        # Calculate summary if not present
        if 'summary' not in results:
            test_results = results.get('test_results', [])
            total = len(test_results)
            passed = sum(1 for r in test_results if r.get('status') == 'passed')
            failed = total - passed
            
            results['summary'] = {
                'total': total,
                'passed': passed,
                'failed': failed,
                'duration': results.get('duration', 0)
            }
        
        return jsonify({
            'results': results,
            'summary': results.get('summary', {})
        }), 200
        
    except FileNotFoundError:
        return jsonify({'error': 'Results not found'}), 404
    except Exception as e:
        logger.error(f"Error getting results: {e}")
        return jsonify({'error': str(e)}), 500

