print("Debug script loaded")
import sys
print("Python path:", sys.path)

try:
    from app import app
    print("App imported successfully")
    print("Routes:", [str(rule) for rule in app.url_map.iter_rules()])
except Exception as e:
    print("Error importing app:", str(e))
