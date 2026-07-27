"""
pytest configuration and fixtures for protocol prototype tests.

Provides reusable fixtures for:
- Mock LNS/CUPS servers
- Gateway simulators
- Protocol message factories
- Async test infrastructure
- Hypothesis property-based testing configuration
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))
sys.path.insert(0, str(Path(__file__).parent.parent / "simulation" / "mocks"))

# Configure Hypothesis profiles
try:
    from hypothesis import settings, Verbosity, Phase
    
    # Default profile: balanced speed and coverage
    settings.register_profile(
        "default",
        max_examples=100,
        deadline=None,  # Disable deadline for slow interpreters
    )
    
    # CI profile: more thorough testing
    settings.register_profile(
        "ci",
        max_examples=500,
        deadline=None,
        suppress_health_check=[],
        phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink],
    )
    
    # Dev profile: fast iteration
    settings.register_profile(
        "dev",
        max_examples=10,
        deadline=None,
    )
    
    # Debug profile: verbose output
    settings.register_profile(
        "debug",
        max_examples=10,
        verbosity=Verbosity.verbose,
        deadline=None,
    )
    
    # Load profile from environment
    import os
    profile = os.environ.get("HYPOTHESIS_PROFILE", "default")
    settings.load_profile(profile)
    
except ImportError:
    pass  # Hypothesis not installed


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_lns():
    """
    Provide a mock LNS server for testing.
    
    Usage:
        async def test_uplink(mock_lns):
            @mock_lns.on_message('updf')
            async def handle_uplink(msg):
                return {'msgtype': 'dntxed'}
            
            await mock_lns.start()
            # ... test code ...
    """
    from lns_mock import MockLNS
    
    lns = MockLNS(port=6090)
    await lns.start()
    yield lns
    await lns.stop()


@pytest.fixture
async def mock_cups():
    """
    Provide a mock CUPS server for testing.
    """
    from cups_mock import MockCUPS
    
    cups = MockCUPS(port=6091)
    await cups.start()
    yield cups
    await cups.stop()


@pytest.fixture
async def gateway_sim():
    """
    Provide a gateway simulator for testing.
    
    Usage:
        async def test_gateway(gateway_sim, mock_lns):
            await gateway_sim.connect("ws://localhost:6090/gw-001")
            await gateway_sim.simulate_uplink(freq=868100000, sf=7, payload=b'...')
    """
    from gateway_sim import GatewaySimulator
    
    gw = GatewaySimulator()
    yield gw
    await gw.disconnect()


@pytest.fixture
def message_factory():
    """
    Provide factory functions for creating test messages.
    
    Usage:
        def test_encoding(message_factory):
            uplink = message_factory.uplink(devaddr=0x01020304, fcnt=1)
    """
    from message_factory import MessageFactory
    return MessageFactory()


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "compliance: marks tests as spec compliance tests"
    )


# Async timeout for all async tests
@pytest.fixture(autouse=True)
def async_timeout():
    """Default timeout for async tests."""
    return 30.0  # seconds
