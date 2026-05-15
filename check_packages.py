import sys
print("Python version:", sys.version)

try:
    import flask
    print("Flask: OK")
except ImportError as e:
    print("Flask: NOT INSTALLED -", e)

try:
    import requests
    print("Requests: OK")
except ImportError as e:
    print("Requests: NOT INSTALLED -", e)
