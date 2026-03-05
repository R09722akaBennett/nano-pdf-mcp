import json
import urllib.request
import sys
from jsonschema import validate, ValidationError

def validate_server_json(file_path):
    # 1. Read the server.json
    try:
        with open(file_path, 'r') as f:
            instance = json.load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    # 2. Get the schema URL from the $schema field or use the default
    schema_url = instance.get("$schema")
    if not schema_url:
        # Fallback to the latest known schema if $schema is missing
        schema_url = "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"
        print(f"Warning: $schema field missing, using default: {schema_url}")
    
    # 3. Fetch the schema
    try:
        with urllib.request.urlopen(schema_url) as response:
            schema = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching schema from {schema_url}: {e}")
        return False

    # 4. Validate
    try:
        validate(instance=instance, schema=schema)
        print("✓ server.json is valid according to the schema!")
        return True
    except ValidationError as e:
        print("✗ Validation failed!")
        print(f"Message: {e.message}")
        print(f"Path: {' -> '.join(map(str, e.path))}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_server_json.py <path_to_server.json>")
        sys.exit(1)
    
    success = validate_server_json(sys.argv[1])
    if not success:
        sys.exit(1)
