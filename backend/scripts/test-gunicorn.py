#!/usr/bin/env python3
"""
Test script to validate Gunicorn configurations
"""
import os
import sys
import importlib.util
import tempfile

def test_config_file(config_path, config_name):
    """Test a Gunicorn configuration file"""
    print(f"\nTesting {config_name}...")
    
    # Check if file exists
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return False
    
    try:
        # Load the config module
        spec = importlib.util.spec_from_file_location("gunicorn_config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        # Check required attributes
        required_attrs = ['bind', 'workers', 'worker_class', 'wsgi_module']
        for attr in required_attrs:
            if not hasattr(config_module, attr):
                print(f"❌ Missing required attribute: {attr}")
                return False
            value = getattr(config_module, attr)
            print(f"✅ {attr}: {value}")
        
        # Check optional but important attributes
        optional_attrs = ['timeout', 'keepalive', 'max_requests', 'loglevel']
        for attr in optional_attrs:
            if hasattr(config_module, attr):
                value = getattr(config_module, attr)
                print(f"✅ {attr}: {value}")
        
        print(f"✅ {config_name} configuration is valid!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading {config_name}: {e}")
        return False

def main():
    """Main test function"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Test configurations
    configs = [
        (os.path.join(script_dir, "gunicorn.py"), "Production"),
        (os.path.join(script_dir, "gunicorn-dev.py"), "Development")
    ]
    
    print("🧪 Testing Gunicorn Configurations")
    print("=" * 50)
    
    all_passed = True
    for config_path, config_name in configs:
        if not test_config_file(config_path, config_name):
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All configurations are valid!")
        sys.exit(0)
    else:
        print("❌ Some configurations failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()