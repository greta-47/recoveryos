#!/usr/bin/env python3
"""Test script to verify container hardening implementation."""

import subprocess
import sys
import time

def test_docker_build():
    """Test that the hardened Docker image builds successfully."""
    print('=== Testing Docker Build ===')
    
    try:
        result = subprocess.run([
            'docker', 'build', 
            '--target', 'runtime',
            '-t', 'recoveryos:hardened-test',
            '.'
        ], capture_output=True, text=True, cwd='/home/ubuntu/repos/recoveryos')
        
        if result.returncode == 0:
            print('✅ Docker image builds successfully')
            return True
        else:
            print(f'❌ Docker build failed: {result.stderr}')
            return False
            
    except Exception as e:
        print(f'❌ Docker build error: {e}')
        return False

def test_read_only_filesystem():
    """Test that container works with read-only filesystem."""
    print('\n=== Testing Read-Only Filesystem ===')
    
    try:
        result = subprocess.run([
            'docker', 'run', '--rm', '-d',
            '--read-only',
            '--tmpfs', '/tmp/app:size=100M,noexec,nosuid,nodev',
            '--tmpfs', '/var/log/app:size=50M,noexec,nosuid,nodev', 
            '--tmpfs', '/var/cache/app:size=50M,noexec,nosuid,nodev',
            '-e', 'READONLY_MODE=true',
            '-p', '8001:8000',
            '--name', 'recoveryos-readonly-test',
            'recoveryos:hardened-test'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            container_id = result.stdout.strip()
            print(f'✅ Container started with read-only filesystem: {container_id[:12]}')
            
            time.sleep(5)
            
            health_result = subprocess.run([
                'curl', '-f', 'http://localhost:8001/healthz'
            ], capture_output=True, text=True)
            
            if health_result.returncode == 0:
                print('✅ Health endpoint accessible with read-only filesystem')
                success = True
            else:
                print('❌ Health endpoint not accessible with read-only filesystem')
                success = False
            
            subprocess.run(['docker', 'stop', container_id], capture_output=True)
            return success
            
        else:
            print(f'❌ Read-only container failed to start: {result.stderr}')
            return False
            
    except Exception as e:
        print(f'❌ Read-only filesystem test error: {e}')
        return False

def test_no_build_tools():
    """Test that build tools are not present in runtime image."""
    print('\n=== Testing Build Tools Removal ===')
    
    try:
        result = subprocess.run([
            'docker', 'run', '--rm',
            'recoveryos:hardened-test',
            'sh', '-c', 'which gcc || echo "gcc not found"'
        ], capture_output=True, text=True)
        
        if 'gcc not found' in result.stdout:
            print('✅ Build tools (gcc) successfully removed from runtime image')
            build_tools_removed = True
        else:
            print('❌ Build tools still present in runtime image')
            build_tools_removed = False
        
        result = subprocess.run([
            'docker', 'run', '--rm',
            'recoveryos:hardened-test',
            'sh', '-c', 'dpkg -l | grep -E "(build-essential|libpq-dev)" || echo "dev packages not found"'
        ], capture_output=True, text=True)
        
        if 'dev packages not found' in result.stdout:
            print('✅ Development packages successfully removed from runtime image')
            dev_packages_removed = True
        else:
            print('❌ Development packages still present in runtime image')
            dev_packages_removed = False
        
        return build_tools_removed and dev_packages_removed
        
    except Exception as e:
        print(f'❌ Build tools test error: {e}')
        return False

def test_non_root_user():
    """Test that container runs as non-root user."""
    print('\n=== Testing Non-Root User ===')
    
    try:
        result = subprocess.run([
            'docker', 'run', '--rm',
            'recoveryos:hardened-test',
            'id'
        ], capture_output=True, text=True)
        
        if 'uid=10001(appuser)' in result.stdout:
            print('✅ Container runs as non-root user (appuser, UID 10001)')
            return True
        else:
            print(f'❌ Container not running as expected user: {result.stdout}')
            return False
            
    except Exception as e:
        print(f'❌ Non-root user test error: {e}')
        return False

def test_security_labels():
    """Test that security labels are present."""
    print('\n=== Testing Security Labels ===')
    
    try:
        result = subprocess.run([
            'docker', 'inspect', 'recoveryos:hardened-test'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            labels_found = 0
            expected_labels = [
                'security.hardened=true',
                'security.non-root=true', 
                'security.readonly=supported',
                'security.build-tools=removed'
            ]
            
            for label in expected_labels:
                if label in result.stdout:
                    labels_found += 1
                    print(f'✅ Found security label: {label}')
                else:
                    print(f'❌ Missing security label: {label}')
            
            return labels_found == len(expected_labels)
        else:
            print(f'❌ Failed to inspect image: {result.stderr}')
            return False
            
    except Exception as e:
        print(f'❌ Security labels test error: {e}')
        return False

def cleanup():
    """Clean up test containers and images."""
    print('\n=== Cleaning Up ===')
    
    try:
        subprocess.run(['docker', 'stop', 'recoveryos-readonly-test'], capture_output=True)
        subprocess.run(['docker', 'rm', 'recoveryos-readonly-test'], capture_output=True)
        
        subprocess.run(['docker', 'rmi', 'recoveryos:hardened-test'], capture_output=True)
        
        print('✅ Cleanup completed')
        
    except Exception as e:
        print(f'❌ Cleanup error: {e}')

if __name__ == "__main__":
    print("=== Container Hardening Test Suite ===")
    
    try:
        build_ok = test_docker_build()
        if not build_ok:
            print("❌ Docker build failed, skipping other tests")
            sys.exit(1)
        
        readonly_ok = test_read_only_filesystem()
        tools_ok = test_no_build_tools()
        user_ok = test_non_root_user()
        labels_ok = test_security_labels()
        
        print(f"\n=== Test Results ===")
        print(f"Docker build: {'✅' if build_ok else '❌'}")
        print(f"Read-only filesystem: {'✅' if readonly_ok else '❌'}")
        print(f"Build tools removed: {'✅' if tools_ok else '❌'}")
        print(f"Non-root user: {'✅' if user_ok else '❌'}")
        print(f"Security labels: {'✅' if labels_ok else '❌'}")
        
        if all([build_ok, readonly_ok, tools_ok, user_ok, labels_ok]):
            print("🎉 All container hardening tests passed!")
            sys.exit(0)
        else:
            print("❌ Some container hardening tests failed")
            sys.exit(1)
            
    finally:
        cleanup()
