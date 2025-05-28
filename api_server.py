import logging
import io
import os # Make sure os is imported
from flask import Flask, request, jsonify, send_from_directory
from agent.flow import create_flow

# Define the absolute path to the 'ui' directory
UI_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui')

app = Flask(__name__, static_folder=UI_DIRECTORY, static_url_path='')
# By setting static_url_path='', files in static_folder (ui) will be served from the root.
# e.g., http://localhost:5000/index.html (if it exists directly in UI_DIRECTORY)

# Configure a logger for capturing agent steps
agent_logger = logging.getLogger('agent_steps')
agent_logger.setLevel(logging.INFO)
# Prevent agent_logger from propagating to root logger to avoid duplicate console output
agent_logger.propagate = False 

# Basic console logging for the API server itself
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

@app.route('/invoke_agent', methods=['POST'])
def invoke_agent():
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "Question not provided"}), 400

    question = data['question']
    
    # Setup in-memory stream for capturing logs
    log_stream = io.StringIO()
    # Add a new StreamHandler to the agent_logger for this request
    # This handler will write logs to our log_stream
    stream_handler = logging.StreamHandler(log_stream)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    agent_logger.addHandler(stream_handler)

    # Also, temporarily redirect the root logger (used by PocketFlow nodes) to our stream
    # This is a bit of a hack. A better way would be to pass the logger to the flow.
    # Or ensure all PocketFlow nodes use a specific logger name we can capture.
    # For now, let's assume PocketFlow nodes use the root logger or a known logger.
    # We'll capture logs from the 'pocketflow' logger specifically if it exists,
    # or configure the root logger if nodes log directly via logging.info() etc.
    
    # Get the root logger (PocketFlow nodes seem to use logging.info directly, which goes to root)
    # We need to be careful not to add handlers repeatedly if other parts of app also configure root logger.
    # For simplicity here, we assume this is the main point of interaction.
    
    # Store original handlers of the root logger
    original_root_handlers = list(logging.root.handlers)
    # Clear existing handlers from root to avoid duplicate console output from it
    logging.root.handlers = []
    # Add our stream_handler to the root logger
    logging.root.addHandler(stream_handler)
    # Set root logger level (PocketFlow logs at INFO)
    original_root_level = logging.root.level
    logging.root.setLevel(logging.INFO)

    shared = {
        "question": question,
        "search_result": None,
        "answer": None,
        # Potentially pass the logger or log capture mechanism to the flow if design allows
    }

    try:
        flow = create_flow()
        app.logger.info(f"Invoking agent with question: {question}")
        flow.run(shared) # This should now log to log_stream via the root logger's stream_handler
        
        answer = shared.get("answer", "No answer found.")
        app.logger.info(f"Agent finished. Answer: {answer}")

    except Exception as e:
        app.logger.error(f"Error during agent invocation: {e}", exc_info=True)
        return jsonify({"error": str(e), "steps": []}), 500
    finally:
        # Remove our handler from the agent_logger and root logger
        agent_logger.removeHandler(stream_handler)
        stream_handler.close()
        
        # Restore original root logger handlers and level
        logging.root.handlers = original_root_handlers
        logging.root.setLevel(original_root_level)


    log_contents = log_stream.getvalue().splitlines()
    
    return jsonify({
        "answer": answer,
        "steps": log_contents
    })

if __name__ == '__main__':
    # Note: For development, Flask's built-in server is fine.
    # For production, use a WSGI server like Gunicorn or uWSGI.
    app.run(host='0.0.0.0', port=5000, debug=True)

@app.route('/')
def serve_index():
    # Serves index.html from the UI_DIRECTORY.
    # Flask with static_folder and static_url_path='' might serve it automatically.
    # But to be explicit:
    return send_from_directory(UI_DIRECTORY, 'index.html')

# The generic @app.route('/<path:path>') is removed as Flask's static_folder
# with static_url_path='' should handle serving other files from UI_DIRECTORY (e.g. /styles.css if ui/styles.css exists)
# If specific routes for other static files were needed, they would be added explicitly or this generic one refined.
