import pytest
import sys
import os

# Add the parent directory to the Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Store original environment variables
_original_env = {}

# Set test environment variables immediately (needed for app.py import)
test_vars = ['CATALOG_USERNAME', 'CATALOG_PASSWORD',
             'BACKEND_URL', 'OPENAI_API_KEY']
for var in test_vars:
    _original_env[var] = os.environ.get(var)

# Set test values
os.environ['CATALOG_USERNAME'] = 'test_user'
os.environ['CATALOG_PASSWORD'] = 'test_password'
os.environ['BACKEND_URL'] = 'https://test-db.example.com/'
os.environ['OPENAI_API_KEY'] = 'test_key'


@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Restore original environment variables after all tests complete."""
    yield

    # Restore original values after all tests complete
    for var, original_value in _original_env.items():
        if original_value is None:
            os.environ.pop(var, None)  # Remove if it didn't exist before
        else:
            os.environ[var] = original_value  # Restore original value
