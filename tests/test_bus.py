"""
Test Suite — Event Bus
Tests for event subscription, emission, and wildcard pattern matching.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

# Add brain to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'brain'))

from core.bus import EventBus


class TestEventBusSubscription:
    """Test event subscription and handler registration"""

    def test_subscribe_handler(self):
        """Test basic handler subscription"""
        bus = EventBus()

        def handler(envelope):
            pass
        handler.__name__ = "test_handler"

        bus.subscribe("test.event", handler)

        assert "test.event" in bus._subscribers
        assert handler in bus._subscribers["test.event"]

    def test_subscribe_multiple_handlers_same_event(self):
        """Test multiple handlers can subscribe to same event"""
        bus = EventBus()

        def handler1(envelope):
            pass
        handler1.__name__ = "handler1"

        def handler2(envelope):
            pass
        handler2.__name__ = "handler2"

        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)

        assert len(bus._subscribers["test.event"]) == 2
        assert handler1 in bus._subscribers["test.event"]
        assert handler2 in bus._subscribers["test.event"]

    def test_subscribe_wildcard_pattern(self):
        """Test subscription with wildcard patterns"""
        bus = EventBus()

        def handler(envelope):
            pass
        handler.__name__ = "wildcard_handler"

        bus.subscribe("lead.*", handler)

        assert "lead.*" in bus._subscribers
        assert handler in bus._subscribers["lead.*"]

    def test_pattern_matching_exact(self):
        """Test exact pattern matching"""
        bus = EventBus()

        assert bus._matches("user.created", "user.created") is True
        assert bus._matches("user.created", "user.updated") is False

    def test_pattern_matching_wildcard(self):
        """Test wildcard pattern matching"""
        bus = EventBus()

        assert bus._matches("lead.created", "lead.*") is True
        assert bus._matches("lead.updated", "lead.*") is True
        assert bus._matches("lead.deleted", "lead.*") is True
        assert bus._matches("user.created", "lead.*") is False

    def test_pattern_matching_prefix(self):
        """Test wildcard matches prefix correctly"""
        bus = EventBus()

        # Wildcard should match anything starting with prefix
        assert bus._matches("api.v1.users.get", "api.*") is True
        assert bus._matches("api.v2.leads.post", "api.*") is True
        assert bus._matches("webhook.received", "api.*") is False


class TestEventEmission:
    """Test event emission and handler invocation"""

    @pytest.mark.asyncio
    async def test_emit_calls_subscribed_handler(self):
        """Test that emitting event calls subscribed handler"""
        bus = EventBus()
        handler = AsyncMock()

        bus.subscribe("test.event", handler)

        # Start bus processing
        bus_task = asyncio.create_task(bus.start())

        # Emit event
        await bus.emit("test.event", {"data": "test_value"})

        # Give bus time to process
        await asyncio.sleep(0.1)

        # Stop bus
        await bus.stop()
        await bus_task

        # Handler should have been called
        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args["event"] == "test.event"
        assert call_args["data"]["data"] == "test_value"

    @pytest.mark.asyncio
    async def test_emit_with_org_id(self):
        """Test emitting event with org_id for multi-tenant isolation"""
        bus = EventBus()
        handler = AsyncMock()

        bus.subscribe("lead.created", handler)

        bus_task = asyncio.create_task(bus.start())

        await bus.emit("lead.created", {"lead_id": 123}, org_id="org_456")

        await asyncio.sleep(0.1)
        await bus.stop()
        await bus_task

        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args["org_id"] == "org_456"
        assert call_args["data"]["lead_id"] == 123

    @pytest.mark.asyncio
    async def test_emit_calls_multiple_handlers(self):
        """Test that one event can trigger multiple handlers"""
        bus = EventBus()
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)

        bus_task = asyncio.create_task(bus.start())

        await bus.emit("test.event", {"msg": "hello"})

        await asyncio.sleep(0.1)
        await bus.stop()
        await bus_task

        handler1.assert_called_once()
        handler2.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_with_wildcard_subscription(self):
        """Test that wildcard subscriptions receive matching events"""
        bus = EventBus()
        handler = AsyncMock()

        bus.subscribe("lead.*", handler)

        bus_task = asyncio.create_task(bus.start())

        # All these should trigger the wildcard handler
        await bus.emit("lead.created", {"id": 1})
        await bus.emit("lead.updated", {"id": 2})
        await bus.emit("lead.deleted", {"id": 3})

        await asyncio.sleep(0.2)
        await bus.stop()
        await bus_task

        # Handler should have been called 3 times
        assert handler.call_count == 3

    @pytest.mark.asyncio
    async def test_emit_sync_method(self):
        """Test synchronous emit_sync method"""
        bus = EventBus()
        handler = AsyncMock()

        bus.subscribe("sync.test", handler)

        bus_task = asyncio.create_task(bus.start())

        # Use sync emit (from non-async code)
        bus.emit_sync("sync.test", {"value": 42})

        await asyncio.sleep(0.1)
        await bus.stop()
        await bus_task

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_no_subscribers(self):
        """Test emitting event with no subscribers doesn't crash"""
        bus = EventBus()

        bus_task = asyncio.create_task(bus.start())

        # This should not raise an error
        await bus.emit("unsubscribed.event", {"data": "test"})

        await asyncio.sleep(0.1)
        await bus.stop()
        await bus_task

        # No assertion needed - just verifying no exception

    @pytest.mark.asyncio
    async def test_handler_exception_doesnt_stop_bus(self):
        """Test that handler exception doesn't stop event bus"""
        bus = EventBus()

        async def failing_handler(envelope):
            raise Exception("Handler failed")

        async def working_handler(envelope):
            working_handler.called = True

        working_handler.called = False

        bus.subscribe("test.event", failing_handler)
        bus.subscribe("test.event", working_handler)

        bus_task = asyncio.create_task(bus.start())

        await bus.emit("test.event", {"data": "test"})

        await asyncio.sleep(0.1)
        await bus.stop()
        await bus_task

        # Working handler should still have been called
        assert working_handler.called is True

    @pytest.mark.asyncio
    async def test_sync_handler_in_async_bus(self):
        """Test that synchronous handlers work in async event bus"""
        bus = EventBus()

        def sync_handler(envelope):
            sync_handler.called = True
            sync_handler.data = envelope["data"]

        sync_handler.called = False
        sync_handler.data = None

        bus.subscribe("test.event", sync_handler)

        bus_task = asyncio.create_task(bus.start())

        await bus.emit("test.event", {"value": "sync_test"})

        await asyncio.sleep(0.1)
        await bus.stop()
        await bus_task

        assert sync_handler.called is True
        assert sync_handler.data["value"] == "sync_test"

    @pytest.mark.asyncio
    async def test_queue_full_handling(self):
        """Test that queue full scenario is handled gracefully"""
        # Create bus with small queue
        bus = EventBus()
        bus._queue = asyncio.Queue(maxsize=2)

        # Fill the queue without starting the bus
        bus.emit_sync("event1", {})
        bus.emit_sync("event2", {})

        # This should be dropped (queue full)
        bus.emit_sync("event3", {})  # Should log warning but not crash

        # Queue should still have exactly 2 items
        assert bus._queue.qsize() == 2

    @pytest.mark.asyncio
    async def test_stats(self):
        """Test event bus statistics"""
        bus = EventBus()

        def handler1(envelope):
            pass
        handler1.__name__ = "handler1"

        def handler2(envelope):
            pass
        handler2.__name__ = "handler2"

        def handler3(envelope):
            pass
        handler3.__name__ = "handler3"

        bus.subscribe("event.one", handler1)
        bus.subscribe("event.one", handler2)
        bus.subscribe("event.two", handler3)

        # Emit some events
        bus.emit_sync("event.one", {})
        bus.emit_sync("event.two", {})

        stats = bus.stats()

        assert stats["event_types"] == 2
        assert stats["total_handlers"] == 3
        assert stats["queue_size"] == 2

    @pytest.mark.asyncio
    async def test_multiple_pattern_subscriptions(self):
        """Test event matching multiple wildcard patterns"""
        bus = EventBus()

        handler_all = AsyncMock()
        handler_lead = AsyncMock()
        handler_specific = AsyncMock()

        bus.subscribe("*", handler_all)  # Won't match due to _matches logic
        bus.subscribe("lead.*", handler_lead)
        bus.subscribe("lead.created", handler_specific)

        bus_task = asyncio.create_task(bus.start())

        await bus.emit("lead.created", {"id": 1})

        await asyncio.sleep(0.1)
        await bus.stop()
        await bus_task

        # Both wildcard and specific should be called
        assert handler_lead.call_count == 1
        assert handler_specific.call_count == 1

    @pytest.mark.asyncio
    async def test_bus_start_stop_lifecycle(self):
        """Test event bus start and stop lifecycle"""
        bus = EventBus()

        assert bus._running is False

        bus_task = asyncio.create_task(bus.start())

        await asyncio.sleep(0.05)
        assert bus._running is True

        await bus.stop()
        await bus_task

        assert bus._running is False
