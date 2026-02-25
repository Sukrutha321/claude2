"""
CodeGenie - AI Code Generator Backend
Flask application with Hugging Face integration
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import os
from datetime import datetime
import logging
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret") # Change this!
CORS(app)

# Hugging Face API Configuration
users = {
    'demo@codegenie.dev': {
        'password': 'Demo2024!',
        'name': 'Demo User'
    }
}

# ============= Routes =============

@app.route('/')
def index():
    """Serve the login page"""
    return render_template('login.html')

@app.route('/homepage')
def homepage():
    """Serve the homepage (requires login)"""
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('homepage.html', user=session['user'])

# ============= API Endpoints =============

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400
        
        if email in users and users[email]['password'] == password:
            session['user'] = {
                'email': email,
                'name': users[email]['name']
            }
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': session['user']
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during login'
        }), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Handle user logout"""
    session.pop('user', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/signup', methods=['POST'])
def signup():
    """Handle user signup"""
    try:
        data = request.json
        logger.debug(f"Signup attempt - Raw data: {data}")
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        logger.debug(f"Signup attempt - Email: {email}, Name: {name}, Password length: {len(password)}")
        
        # Validate input
        if not all([name, email, password]):
            logger.warning(f"Signup failed - Missing fields")
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400
        
        # Validate email format (basic check)
        if '@' not in email or '.' not in email:
            logger.warning(f"Signup failed - Invalid email format: {email}")
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400
        
        # Validate password length
        if len(password) < 8:
            logger.warning(f"Signup failed - Password too short")
            return jsonify({
                'success': False,
                'message': 'Password must be at least 8 characters'
            }), 400
        
        # Check if user already exists
        if email in users:
            logger.warning(f"Signup failed - Email already registered: {email}")
            return jsonify({
                'success': False,
                'message': 'Email already registered'
            }), 400
        
        # In production, hash the password!
        users[email] = {
            'name': name,
            'password': password  # USE HASHING IN PRODUCTION!
        }
        
        logger.info(f"Signup successful - Email: {email}, Name: {name}")
        logger.debug(f"Current users: {list(users.keys())}")
        
        return jsonify({
            'success': True,
            'message': 'Account created successfully'
        })
        
    except Exception as e:
        logger.error(f"Signup error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration'
        }), 500

@app.route('/api/generate', methods=['POST'])
def generate_code():
    """
    Generate code from natural language prompt using Hugging Face
    
    Expected JSON payload:
    {
        "prompt": "Create a function to calculate factorial",
        "language": "python"
    }
    """
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        prompt = data.get('prompt', '')
        language = data.get('language', 'python')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Format the prompt for code generation
        formatted_prompt = format_prompt(prompt, language)
        
        # Call Hugging Face API
        generated_code = call_huggingface_api(formatted_prompt)
        
        return jsonify({
            'success': True,
            'code': generated_code,
            'language': language,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/explain', methods=['POST'])
def explain_code():
    """
    Convert code to natural language explanation
    
    Expected JSON payload:
    {
        "code": "def factorial(n): ...",
        "language": "python"
    }
    """
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        
        if not code:
            return jsonify({'error': 'Code is required'}), 400
        
        # Format the prompt for code explanation
        formatted_prompt = f"Explain this {language} code in simple terms:\n\n{code}"
        
        # Call Hugging Face API
        explanation = call_huggingface_api(formatted_prompt)
        
        return jsonify({
            'success': True,
            'explanation': explanation,
            'language': language,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============= Helper Functions =============

def format_prompt(prompt, language):
    """Format the user prompt for the AI model"""
    language_templates = {
        'python': f"Write Python code for the following task:\n{prompt}\n\nPython code:",
        'javascript': f"Write JavaScript code for the following task:\n{prompt}\n\nJavaScript code:",
        'java': f"Write Java code for the following task:\n{prompt}\n\nJava code:",
        'cpp': f"Write C++ code for the following task:\n{prompt}\n\nC++ code:"
    }
    
    return language_templates.get(language, f"Write {language} code:\n{prompt}")

from huggingface_hub import InferenceClient

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
client = InferenceClient(token=HUGGINGFACE_API_TOKEN)

def call_huggingface_api(prompt):
    try:
        response = client.text_generation(
            model="google/flan-t5-base",
            provider="hf-inference",
            prompt=prompt,
            max_new_tokens=300,
            temperature=0.7,
        )
        print("HF RESPONSE:", response)
        return response

    except Exception as e:
        print("HF ERROR:", repr(e))
        raise
    
def get_demo_code(prompt):
    """Fallback demo code when API is unavailable"""
    return f"""# Demo code (API not configured)
# Original prompt: {prompt}

def example_function():
    '''
    This is a demo placeholder.
    Configure your Hugging Face API token to get real AI-generated code.
    '''
    pass
"""

# ============= Error Handlers =============

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Route not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# ============= Main =============

if __name__ == '__main__':
    # In production, use a proper WSGI server like Gunicorn
    app.run(debug=True, host='0.0.0.0', port=5000)