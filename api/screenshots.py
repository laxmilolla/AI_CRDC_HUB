"""
Screenshot API endpoints
"""
import zipfile
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
from utils.screenshot_handler import ScreenshotHandler
from utils.logger import get_logger

bp = Blueprint('screenshots', __name__)
logger = get_logger(__name__)


@bp.route('/screenshots/<execution_id>/<test_case_id>', methods=['GET'])
def list_screenshots(execution_id, test_case_id):
    """List all screenshots for a test case"""
    try:
        from utils.file_handler import FileHandler
        
        file_handler = FileHandler()
        screenshot_handler = ScreenshotHandler(base_dir=str(file_handler.base_dir), execution_id=execution_id)
        screenshots = screenshot_handler.list_screenshots(execution_id, test_case_id)
        
        screenshot_info = []
        for screenshot_path in screenshots:
            screenshot_info.append({
                'path': str(screenshot_path),
                'url': screenshot_handler.get_screenshot_url(screenshot_path),
                'name': screenshot_path.name
            })
        
        return jsonify({
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'screenshots': screenshot_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing screenshots: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/screenshots/<execution_id>/<test_case_id>/<int:step_number>', methods=['GET'])
def get_screenshot(execution_id, test_case_id, step_number):
    """Get specific screenshot image"""
    try:
        from utils.file_handler import FileHandler
        
        file_handler = FileHandler()
        screenshot_handler = ScreenshotHandler(base_dir=str(file_handler.base_dir), execution_id=execution_id)
        screenshots = screenshot_handler.list_screenshots(execution_id, test_case_id)
        
        # Find screenshot by step number
        target_screenshot = None
        for screenshot_path in screenshots:
            if f"step_{step_number:02d}" in screenshot_path.name:
                target_screenshot = screenshot_path
                break
        
        if not target_screenshot or not target_screenshot.exists():
            return jsonify({'error': 'Screenshot not found'}), 404
        
        return send_file(
            str(target_screenshot),
            mimetype='image/png',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Error getting screenshot: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/screenshots/file/<path:filepath>', methods=['GET'])
def serve_screenshot_file(filepath):
    """Serve screenshot file directly by path"""
    try:
        from utils.file_handler import FileHandler
        from pathlib import Path
        
        file_handler = FileHandler()
        
        # Handle both absolute and relative paths
        # If it's already an absolute path, use it directly
        if filepath.startswith('/'):
            screenshot_path = Path(filepath)
        elif filepath.startswith('screenshots/'):
            screenshot_path = file_handler.base_dir / filepath
        else:
            screenshot_path = file_handler.base_dir / 'screenshots' / filepath
        
        # Resolve to absolute path
        screenshot_path = screenshot_path.resolve()
        base_screenshots_dir = (file_handler.base_dir / "screenshots").resolve()
        
        # Prevent directory traversal - ensure path is within screenshots directory
        try:
            screenshot_path.relative_to(base_screenshots_dir)
        except ValueError:
            # If it's an absolute path outside our base, check if it's still a valid screenshot path
            if not str(screenshot_path).startswith(str(base_screenshots_dir)):
                logger.error(f"Invalid screenshot path (outside base): {screenshot_path}")
                return jsonify({'error': 'Invalid path'}), 403
        
        if not screenshot_path.exists():
            logger.error(f"Screenshot not found: {screenshot_path}")
            # Try to find it with a different approach
            if 'execution_' in str(screenshot_path):
                # Extract execution ID and try alternative path
                parts = str(screenshot_path).split('execution_')
                if len(parts) > 1:
                    alt_path = base_screenshots_dir / ('execution_' + parts[1])
                    if alt_path.exists():
                        screenshot_path = alt_path
                    else:
                        return jsonify({'error': 'Screenshot not found'}), 404
                else:
                    return jsonify({'error': 'Screenshot not found'}), 404
            else:
                return jsonify({'error': 'Screenshot not found'}), 404
        
        return send_file(
            str(screenshot_path),
            mimetype='image/png',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Error serving screenshot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@bp.route('/screenshots/<execution_id>/download', methods=['GET'])
def download_screenshots(execution_id):
    """Download all screenshots as ZIP"""
    try:
        screenshot_handler = ScreenshotHandler(execution_id=execution_id)
        screenshots = screenshot_handler.list_screenshots(execution_id)
        
        if not screenshots:
            return jsonify({'error': 'No screenshots found'}), 404
        
        # Create ZIP file
        zip_path = Path('screenshots') / f'execution_{execution_id}.zip'
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for screenshot_path in screenshots:
                if screenshot_path.exists():
                    # Add to ZIP with relative path
                    arcname = screenshot_path.relative_to(Path('screenshots'))
                    zipf.write(screenshot_path, arcname)
        
        return send_file(
            str(zip_path),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'screenshots_execution_{execution_id}.zip'
        )
        
    except Exception as e:
        logger.error(f"Error downloading screenshots: {e}")
        return jsonify({'error': str(e)}), 500

