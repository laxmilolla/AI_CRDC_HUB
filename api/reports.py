"""
Report API endpoints
"""
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
from core.result_analyzer import ResultAnalyzer
from utils.file_handler import FileHandler
from utils.logger import get_logger

bp = Blueprint('reports', __name__)
logger = get_logger(__name__)
result_analyzer = ResultAnalyzer()
file_handler = FileHandler()


@bp.route('/reports/<execution_id>', methods=['GET'])
def get_report(execution_id):
    """Get analysis report for execution"""
    try:
        # Load results
        results = file_handler.load_results(execution_id)
        
        # Analyze results (if not already analyzed)
        report_dir = Path('reports') / f'execution_{execution_id}'
        report_file = report_dir / 'report.html'
        
        if not report_file.exists():
            # Generate analysis and report
            analysis_result = result_analyzer.analyze_results(results, execution_id)
            report_content = analysis_result['report']
        else:
            # Load existing report
            report_content = report_file.read_text(encoding='utf-8')
        
        # Try to load analysis JSON
        analysis_json = {}
        json_file = report_dir / 'report.json'
        if json_file.exists():
            import json
            analysis_json = json.loads(json_file.read_text(encoding='utf-8'))
        
        return jsonify({
            'execution_id': execution_id,
            'report': report_content,
            'analysis': analysis_json
        }), 200
        
    except FileNotFoundError:
        return jsonify({'error': 'Report not found'}), 404
    except Exception as e:
        logger.error(f"Error getting report: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/reports/<execution_id>/download', methods=['GET'])
def download_report(execution_id):
    """Download report as HTML file"""
    try:
        report_dir = Path('reports') / f'execution_{execution_id}'
        report_file = report_dir / 'report.html'
        
        if not report_file.exists():
            # Generate report if doesn't exist
            results = file_handler.load_results(execution_id)
            analysis_result = result_analyzer.analyze_results(results, execution_id)
            report_content = analysis_result['report']
            report_file.write_text(report_content, encoding='utf-8')
        
        return send_file(
            str(report_file),
            mimetype='text/html',
            as_attachment=True,
            download_name=f'report_execution_{execution_id}.html'
        )
        
    except FileNotFoundError:
        return jsonify({'error': 'Report not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        return jsonify({'error': str(e)}), 500

