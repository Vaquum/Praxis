'''
Run the test suite excluding testnet integration tests.
'''

from __future__ import annotations


import sys

import pytest

sys.exit(pytest.main(['-v', 'tests/', '--ignore=tests/testnet']))
