import json
import urllib.request
from jsonschema import validate, ValidationError

def validate_server_json():
    with open('server.json', 'r') as f:
        server_json = json.load(f)
    
    schema_url = server_json.get('$schema')
    if not schema_url:
        print("Error: $schema field missing in server.json")
        return False
    
    print(f"Fetching schema from {schema_url}...")
    try:
        with urllib.request.urlopen(schema_url) as response:
            schema = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching schema: {e}")
        return False
    
    try:
        validate(instance=server_json, schema=schema)
        print("Validation successful: server.json matches the schema.")
        return True
    except ValidationError as e:
        print(f"Validation failed: {e.message}")
        print(f"Path: {list(e.path)}")
        return False

if __name__ == "__main__":
    if validate_server_json():
        exit(0)
    else:
        exit(1)
