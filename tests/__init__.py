"""
MagicLamp Test Suite
====================

This directory contains comprehensive tests for the MagicLamp codebase.

Test Structure:
--------------
- conftest.py: Shared fixtures and configuration
- test_auth.py: Authentication and authorization tests
- test_circuit.py: Circuit breaker pattern tests
- test_bus.py: Event bus tests
- test_api_*.py: API endpoint tests
- test_integration.py: Full integration tests

Running Tests:
-------------
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov

# Run specific test file
pytest tests/test_auth.py -v

# Run with markers
pytest tests/ -m unit

Coverage Goals:
--------------
- Critical modules (auth, security): 90%+
- Core modules (bus, circuit, registry): 80%+
- API endpoints: 70%+
- Overall target: 60%+

Note: Test files will be added incrementally as the test suite is developed.
"""
