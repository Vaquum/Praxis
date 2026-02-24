import sys

import pytest

sys.exit(pytest.main(['-v', 'tests/', '--ignore=tests/testnet']))
