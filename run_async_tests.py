#!/usr/bin/env python3
"""
Async test runner for Quant-Bot-Crypto
"""
import sys
import os
import asyncio
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class AsyncTestRunner:
    """Custom test runner that handles async test methods"""
    
    def __init__(self, test_class):
        self.test_class = test_class
        self.results = []
    
    async def run_async_test(self, test_method):
        """Run a single async test method"""
        try:
            test_instance = self.test_class()
            test_instance.setUp()
            await test_method(test_instance)
            test_instance.tearDown()
            return True, None
        except Exception as e:
            return False, str(e)
    
    def run_sync_test(self, test_method):
        """Run a single sync test method"""
        try:
            test_instance = self.test_class()
            test_instance.setUp()
            test_method(test_instance)
            test_instance.tearDown()
            return True, None
        except Exception as e:
            return False, str(e)
    
    async def run_all_tests(self):
        """Run all tests in the test class"""
        print(f"Running tests for {self.test_class.__name__}")
        print("=" * 50)
        
        # Get all test methods
        test_methods = [method for method in dir(self.test_class) if method.startswith('test_')]
        
        passed = 0
        failed = 0
        
        for method_name in test_methods:
            test_method = getattr(self.test_class, method_name)
            
            # Check if method is async
            if asyncio.iscoroutinefunction(test_method):
                success, error = await self.run_async_test(test_method)
            else:
                success, error = self.run_sync_test(test_method)
            
            if success:
                print(f"✅ {method_name}")
                passed += 1
            else:
                print(f"❌ {method_name}: {error}")
                failed += 1
        
        print("=" * 50)
        print(f"Results: {passed} passed, {failed} failed")
        return failed == 0

async def main():
    """Main async test runner"""
    # Import test classes
    from tests.test_crypto_handler_simple import TestCryptoHandlerSimple
    
    # Run tests
    runner = AsyncTestRunner(TestCryptoHandlerSimple)
    success = await runner.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
