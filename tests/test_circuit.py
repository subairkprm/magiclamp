"""
Test Suite — Circuit Breaker
Tests for circuit breaker states, failure thresholds, and recovery logic.
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock

# Add brain to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'brain'))

from core.circuit import CircuitBreaker, CircuitState, CircuitOpenError


class TestCircuitBreakerStates:
    """Test circuit breaker state transitions"""

    @pytest.mark.asyncio
    async def test_initial_state_closed(self):
        """Circuit should start in CLOSED state"""
        cb = CircuitBreaker("test_service", failure_threshold=3, recovery_timeout=5)

        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    @pytest.mark.asyncio
    async def test_transition_to_open_on_failures(self):
        """Circuit should open after reaching failure threshold"""
        cb = CircuitBreaker("test_service", failure_threshold=3, recovery_timeout=5)

        async def failing_func():
            raise Exception("Service unavailable")

        # First 2 failures should keep circuit closed
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)
            assert cb.state == CircuitState.CLOSED

        # Third failure should open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN
        assert cb._failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_open_blocks_requests(self):
        """Circuit in OPEN state should block all requests immediately"""
        cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=5)

        async def failing_func():
            raise Exception("Service unavailable")

        # Trigger circuit to open
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Now all requests should be blocked with CircuitOpenError
        async def any_func():
            return "success"

        with pytest.raises(CircuitOpenError) as exc_info:
            await cb.call(any_func)

        assert "Circuit is OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transition_to_half_open_after_timeout(self):
        """Circuit should transition to HALF_OPEN after recovery timeout"""
        cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=0.5)

        async def failing_func():
            raise Exception("Service unavailable")

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.6)

        # Check state (accessing .state property triggers transition check)
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """Successful calls in HALF_OPEN should close the circuit"""
        cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=0.5, success_threshold=2)

        async def failing_func():
            raise Exception("Service unavailable")

        async def success_func():
            return "success"

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.6)
        assert cb.state == CircuitState.HALF_OPEN

        # First success in HALF_OPEN
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.HALF_OPEN  # Still half-open, need 2 successes

        # Second success should close the circuit
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Failure in HALF_OPEN should reopen the circuit"""
        cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=0.5)

        async def failing_func():
            raise Exception("Service unavailable")

        async def success_func():
            return "success"

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.6)
        assert cb.state == CircuitState.HALF_OPEN

        # Failure in HALF_OPEN should reopen circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_success_in_closed_resets_failures(self):
        """Successful call in CLOSED state should reset failure count"""
        cb = CircuitBreaker("test_service", failure_threshold=3, recovery_timeout=5)

        async def failing_func():
            raise Exception("Service unavailable")

        async def success_func():
            return "success"

        # One failure
        with pytest.raises(Exception):
            await cb.call(failing_func)

        assert cb._failure_count == 1

        # Success should reset counter
        result = await cb.call(success_func)
        assert result == "success"
        assert cb._failure_count == 0
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerConcurrency:
    """Test circuit breaker behavior under concurrent load"""

    @pytest.mark.asyncio
    async def test_concurrent_calls_with_lock(self):
        """Circuit breaker should handle concurrent calls safely"""
        cb = CircuitBreaker("test_service", failure_threshold=5, recovery_timeout=5)

        call_count = 0

        async def counted_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate some work
            return "success"

        # Run 10 concurrent calls
        tasks = [cb.call(counted_func) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r == "success" for r in results)
        assert call_count == 10
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_concurrent_failures_dont_duplicate_count(self):
        """Concurrent failures should be counted correctly with lock"""
        cb = CircuitBreaker("test_service", failure_threshold=3, recovery_timeout=5)

        async def failing_func():
            await asyncio.sleep(0.01)
            raise Exception("Service unavailable")

        # Run 3 concurrent failing calls
        tasks = [cb.call(failing_func) for _ in range(3)]

        with pytest.raises(Exception):
            await asyncio.gather(*tasks)

        # All 3 failures should be counted, circuit should be open
        assert cb.state == CircuitState.OPEN
        assert cb._failure_count == 3

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test get_status returns correct circuit information"""
        cb = CircuitBreaker("test_service", failure_threshold=3, recovery_timeout=5)

        status = cb.get_status()

        assert status["name"] == "test_service"
        assert status["state"] == "closed"
        assert status["failures"] == 0

        # Trigger a failure
        async def failing_func():
            raise Exception("Error")

        with pytest.raises(Exception):
            await cb.call(failing_func)

        status = cb.get_status()
        assert status["failures"] == 1

    @pytest.mark.asyncio
    async def test_multiple_services_independent(self):
        """Test that multiple circuit breakers operate independently"""
        cb1 = CircuitBreaker("service_1", failure_threshold=2, recovery_timeout=5)
        cb2 = CircuitBreaker("service_2", failure_threshold=2, recovery_timeout=5)

        async def failing_func():
            raise Exception("Service unavailable")

        # Fail service_1 twice to open its circuit
        for i in range(2):
            with pytest.raises(Exception):
                await cb1.call(failing_func)

        assert cb1.state == CircuitState.OPEN
        assert cb2.state == CircuitState.CLOSED  # service_2 should be unaffected

        # service_2 can still make calls
        async def success_func():
            return "success"

        result = await cb2.call(success_func)
        assert result == "success"
        assert cb2.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_async_function(self):
        """Test circuit breaker works with async functions"""
        cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=5)

        async def async_success():
            await asyncio.sleep(0.01)
            return "async_result"

        result = await cb.call(async_success)
        assert result == "async_result"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_custom_thresholds(self):
        """Test circuit breaker with custom failure and success thresholds"""
        cb = CircuitBreaker(
            "custom_service",
            failure_threshold=5,
            recovery_timeout=0.5,
            success_threshold=3
        )

        async def failing_func():
            raise Exception("Error")

        # Should take 5 failures to open
        for i in range(4):
            with pytest.raises(Exception):
                await cb.call(failing_func)
            assert cb.state == CircuitState.CLOSED

        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.6)
        assert cb.state == CircuitState.HALF_OPEN

        # Should take 3 successes to close
        async def success_func():
            return "ok"

        await cb.call(success_func)
        assert cb.state == CircuitState.HALF_OPEN

        await cb.call(success_func)
        assert cb.state == CircuitState.HALF_OPEN

        await cb.call(success_func)
        assert cb.state == CircuitState.CLOSED
