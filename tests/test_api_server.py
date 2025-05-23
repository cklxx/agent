import requests
import unittest
import subprocess
import time
import os

# Ensure FLASK_APP environment variable is set for the test environment
os.environ['FLASK_APP'] = 'api_server:app' # Assuming api_server.py contains your Flask app instance named 'app'

class TestAPIServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Start the Flask server as a subprocess
        # Adjust the command if your api_server.py is not in the root or if you use a different way to run it
        cls.server_process = subprocess.Popen(['python', '-m', 'flask', 'run'])
        time.sleep(2) # Give the server a moment to start

    @classmethod
    def tearDownClass(cls):
        # Terminate the Flask server subprocess
        cls.server_process.terminate()
        cls.server_process.wait()

    def test_index_loads_successfully(self):
        try:
            response = requests.get("http://127.0.0.1:5000/")
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.ConnectionError as e:
            self.fail(f"Failed to connect to the server: {e}")

if __name__ == '__main__':
    unittest.main()
