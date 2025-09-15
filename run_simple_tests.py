#!/usr/bin/env python3
"""
Simple test runner for Quant-Bot-Crypto (without pytest)
"""
import sys
import os
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def run_simple_tests():
    """Run simple tests without pytest dependencies"""
    # Test modules to run
    test_modules = [
        'tests.test_crypto_handler_simple',
    ]
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for module_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            suite.addTests(loader.loadTestsFromModule(module))
        except ImportError as e:
            print(f"Warning: Could not import {module_name}: {e}")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    exit_code = run_simple_tests()
    sys.exit(exit_code)
