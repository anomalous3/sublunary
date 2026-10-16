from pathlib import Path

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

# The plugin imports its own testing_config/custom_components package first;
# put ours on that package's search path so HA's loader can find sublunary.
import custom_components  # noqa: E402

_OURS = str(Path(__file__).resolve().parents[1] / "custom_components")
if _OURS not in custom_components.__path__:
    custom_components.__path__.insert(0, _OURS)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
