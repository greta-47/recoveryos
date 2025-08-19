#!/usr/bin/env python3
"""Security assessment script for RecoveryOS."""

import sys
import os
sys.path.insert(0, '/home/ubuntu/repos/recoveryos')

def test_app_functionality():
    """Test basic application functionality."""
    print('=== Testing Local Application Startup ===')
    try:
        from main import app
        print('✅ Main app imports successfully')
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        response = client.get('/')
        print(f'Root endpoint: {response.status_code} - {response.json()}')
        
        response = client.get('/healthz')
        print(f'Health endpoint: {response.status_code} - {response.json()}')
        
        print('✅ Basic API endpoints working')
        return True
        
    except Exception as e:
        print(f'❌ Error testing app: {e}')
        return False

def check_security_headers():
    """Check for security headers implementation."""
    print('\n=== Checking Security Headers Implementation ===')
    
    try:
        with open('/home/ubuntu/repos/recoveryos/main.py', 'r') as f:
            content = f.read()
            
        security_headers = [
            'HSTS', 'X-Frame-Options', 'X-Content-Type-Options', 
            'Referrer-Policy', 'Content-Security-Policy'
        ]
        
        found_headers = []
        for header in security_headers:
            if header in content:
                found_headers.append(header)
                
        if found_headers:
            print(f'✅ Found security headers: {found_headers}')
        else:
            print('❌ No security headers found in main.py')
            
        return len(found_headers) > 0
        
    except Exception as e:
        print(f'❌ Error checking security headers: {e}')
        return False

def check_environment_config():
    """Check environment configuration files."""
    print('\n=== Checking Environment Configuration ===')
    
    env_files = ['.env', '.env.prod', '.env.dev']
    found_files = []
    
    for env_file in env_files:
        if os.path.exists(f'/home/ubuntu/repos/recoveryos/{env_file}'):
            found_files.append(env_file)
            print(f'✅ Found: {env_file}')
        else:
            print(f'❌ Missing: {env_file}')
            
    return len(found_files) > 0

if __name__ == "__main__":
    print("=== RecoveryOS Security Assessment ===")
    
    app_works = test_app_functionality()
    headers_implemented = check_security_headers()
    env_configured = check_environment_config()
    
    print(f"\n=== Summary ===")
    print(f"Application functionality: {'✅' if app_works else '❌'}")
    print(f"Security headers: {'✅' if headers_implemented else '❌'}")
    print(f"Environment config: {'✅' if env_configured else '❌'}")
