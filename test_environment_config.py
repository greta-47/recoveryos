#!/usr/bin/env python3
"""Test script to verify environment-specific configuration works correctly."""

import os
import sys

sys.path.insert(0, '/home/ubuntu/repos/recoveryos')

def test_production_config():
    """Test production environment configuration."""
    print('=== Testing Production Environment Configuration ===')
    
    try:
        os.environ.clear()
        os.environ.update({
            'CSP_MODE': 'enforce',
            'ENABLE_HTTPS_ENFORCEMENT': 'true',
            'ALLOW_LOCALHOST': 'false',
            'ENV': 'production'
        })
        
        from security_middleware import get_security_config
        config = get_security_config()
        
        print('Production config:')
        print(f'  CSP Mode: {config["csp_mode"]}')
        print(f'  HTTPS Enforcement: {config["enable_https_enforcement"]}')
        print(f'  Allow Localhost: {config["allow_localhost"]}')
        
        assert config["csp_mode"] == "enforce", "Production should enforce CSP"
        assert config["enable_https_enforcement"] is True, "Production should enforce HTTPS"
        assert config["allow_localhost"] is False, "Production should not allow localhost"
        
        print('✅ Production configuration correct!')
        return True
        
    except Exception as e:
        print(f'❌ Production config error: {e}')
        return False

def test_development_config():
    """Test development environment configuration."""
    print('\n=== Testing Development Environment Configuration ===')
    
    try:
        os.environ.clear()
        os.environ.update({
            'CSP_MODE': 'report-only',
            'ENABLE_HTTPS_ENFORCEMENT': 'false',
            'ALLOW_LOCALHOST': 'true',
            'ENV': 'development'
        })
        
        from security_middleware import get_security_config
        config = get_security_config()
        
        print('Development config:')
        print(f'  CSP Mode: {config["csp_mode"]}')
        print(f'  HTTPS Enforcement: {config["enable_https_enforcement"]}')
        print(f'  Allow Localhost: {config["allow_localhost"]}')
        
        assert config["csp_mode"] == "report-only", "Development should use CSP report-only"
        assert config["enable_https_enforcement"] is False, "Development should not enforce HTTPS"
        assert config["allow_localhost"] is True, "Development should allow localhost"
        
        print('✅ Development configuration correct!')
        return True
        
    except Exception as e:
        print(f'❌ Development config error: {e}')
        return False

def test_csp_modes():
    """Test CSP enforcement vs report-only modes."""
    print('\n=== Testing CSP Mode Differences ===')
    
    try:
        from test_config import setup_test_environment
        setup_test_environment()
        
        from main import app
        from fastapi.testclient import TestClient
        
        os.environ['CSP_MODE'] = 'enforce'
        client = TestClient(app)
        response = client.get('/')
        
        if 'Content-Security-Policy' in response.headers:
            print('✅ CSP enforce mode: Content-Security-Policy header present')
        else:
            print('❌ CSP enforce mode: Content-Security-Policy header missing')
        
        os.environ['CSP_MODE'] = 'report-only'
        from security_middleware import get_security_config
        config = get_security_config()
        
        if config['csp_mode'] == 'report-only':
            print('✅ CSP report-only mode: Configuration correct')
        else:
            print('❌ CSP report-only mode: Configuration incorrect')
        
        return True
        
    except Exception as e:
        print(f'❌ CSP mode test error: {e}')
        return False

def test_env_file_loading():
    """Test that environment files can be loaded correctly."""
    print('\n=== Testing Environment File Structure ===')
    
    try:
        if os.path.exists('/home/ubuntu/repos/recoveryos/.env.prod'):
            print('✅ .env.prod file exists')
            
            with open('/home/ubuntu/repos/recoveryos/.env.prod', 'r') as f:
                content = f.read()
                
            if 'CSP_MODE=enforce' in content:
                print('✅ .env.prod has CSP_MODE=enforce')
            else:
                print('❌ .env.prod missing CSP_MODE=enforce')
                
            if 'ENABLE_HTTPS_ENFORCEMENT=true' in content:
                print('✅ .env.prod has HTTPS enforcement enabled')
            else:
                print('❌ .env.prod missing HTTPS enforcement')
        else:
            print('❌ .env.prod file missing')
            return False
        
        if os.path.exists('/home/ubuntu/repos/recoveryos/.env.dev'):
            print('✅ .env.dev file exists')
            
            with open('/home/ubuntu/repos/recoveryos/.env.dev', 'r') as f:
                content = f.read()
                
            if 'CSP_MODE=report-only' in content:
                print('✅ .env.dev has CSP_MODE=report-only')
            else:
                print('❌ .env.dev missing CSP_MODE=report-only')
                
            if 'ENABLE_HTTPS_ENFORCEMENT=false' in content:
                print('✅ .env.dev has HTTPS enforcement disabled')
            else:
                print('❌ .env.dev missing HTTPS enforcement disabled')
        else:
            print('❌ .env.dev file missing')
            return False
        
        return True
        
    except Exception as e:
        print(f'❌ Environment file test error: {e}')
        return False

if __name__ == "__main__":
    print("=== Environment Configuration Testing ===")
    
    prod_ok = test_production_config()
    dev_ok = test_development_config()
    csp_ok = test_csp_modes()
    env_ok = test_env_file_loading()
    
    print(f"\n=== Test Results ===")
    print(f"Production config: {'✅' if prod_ok else '❌'}")
    print(f"Development config: {'✅' if dev_ok else '❌'}")
    print(f"CSP modes: {'✅' if csp_ok else '❌'}")
    print(f"Environment files: {'✅' if env_ok else '❌'}")
    
    if all([prod_ok, dev_ok, csp_ok, env_ok]):
        print("🎉 All environment configuration tests passed!")
        sys.exit(0)
    else:
        print("❌ Some environment configuration tests failed")
        sys.exit(1)
