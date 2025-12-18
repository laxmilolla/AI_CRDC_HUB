"""
Main Flask application for AI_CRDC_HUB
"""
import os
from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for API endpoints

# Configure Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Setup logging
logger = setup_logger()

# Import API routes
from api import stories, test_cases, executions, screenshots, reports

# Register API routes
app.register_blueprint(stories.bp, url_prefix='/api')
app.register_blueprint(test_cases.bp, url_prefix='/api')
app.register_blueprint(executions.bp, url_prefix='/api')
app.register_blueprint(screenshots.bp, url_prefix='/api')
app.register_blueprint(reports.bp, url_prefix='/api')


@app.route('/')
def index():
    """Home page - redirect to upload story"""
    return render_template('upload_story.html')


@app.route('/test-cases')
def test_cases_page():
    """Test cases selection page"""
    return render_template('test_cases.html')


@app.route('/progress')
def progress_page():
    """Execution progress page"""
    return render_template('progress.html')


@app.route('/results')
def results_page():
    """Results and report page"""
    return render_template('results.html')


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return {'error': 'Not found'}, 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return {'error': 'Internal server error'}, 500


if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting AI_CRDC_HUB on {host}:{port}")
    app.run(host=host, port=port, debug=debug)

