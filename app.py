"""
TaskMaster
A simple task management application to help users organize their daily tasks.
"""
import os
import sys
import logging
from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_db_connection():
    """Get database connection."""
    database_url = os.environ.get('DATABASE_URL')
    sslmode = os.environ.get('DB_SSLMODE', 'disable')  # Default to disable SSL
    if database_url:
        return psycopg2.connect(database_url, cursor_factory=RealDictCursor, sslmode=sslmode)
    else:
        return psycopg2.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            port=os.environ.get('DB_PORT', '5432'),
            dbname=os.environ.get('DB_NAME', 'app'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', 'postgres'),
            cursor_factory=RealDictCursor,
            sslmode=sslmode
        )

def get_db_connection():
    """Get database connection."""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    else:
        return psycopg2.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            port=os.environ.get('DB_PORT', '5432'),
            dbname=os.environ.get('DB_NAME', 'app'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', 'postgres'),
            cursor_factory=RealDictCursor
        )

def init_db():
    """Initialize database tables."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        conn.close()

@app.route('/health')
def health():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/items', methods=['GET'])
def get_items():
    """Get all items."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM items ORDER BY created_at DESC')
            items = cur.fetchall()
        return jsonify(items)
    finally:
        conn.close()

@app.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """Get item by ID."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM items WHERE id = %s', (item_id,))
            item = cur.fetchone()
        if item:
            return jsonify(item)
        return jsonify({"error": "Item not found"}), 404
    finally:
        conn.close()

@app.route('/items', methods=['POST'])
def create_item():
    """Create new item."""
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Name is required"}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO items (name, description) VALUES (%s, %s) RETURNING *',
                (data['name'], data.get('description', ''))
            )
            item = cur.fetchone()
        conn.commit()
        return jsonify(item), 201
    finally:
        conn.close()

@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """Update item."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE items SET name = COALESCE(%s, name), description = COALESCE(%s, description), updated_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING *',
                (data.get('name'), data.get('description'), item_id)
            )
            item = cur.fetchone()
        conn.commit()
        if item:
            return jsonify(item)
        return jsonify({"error": "Item not found"}), 404
    finally:
        conn.close()

@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Delete item."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM items WHERE id = %s RETURNING id', (item_id,))
            result = cur.fetchone()
        conn.commit()
        if result:
            return jsonify({"message": "Item deleted"})
        return jsonify({"error": "Item not found"}), 404
    finally:
        conn.close()

@app.route('/')
def index():
    """Root endpoint."""
    return jsonify({
        "name": "TaskMaster",
        "description": "A simple task management application to help users organize their daily tasks.",
        "endpoints": [
            {"method": "GET", "path": "/health", "description": "Health check"},
            {"method": "GET", "path": "/items", "description": "List all items"},
            {"method": "POST", "path": "/items", "description": "Create item"},
            {"method": "GET", "path": "/items/<id>", "description": "Get item"},
            {"method": "PUT", "path": "/items/<id>", "description": "Update item"},
            {"method": "DELETE", "path": "/items/<id>", "description": "Delete item"}
        ]
    })

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
