"""Shared pytest markers for Phase 0."""

import pytest

# Specs for modules not yet implemented — skipped until Phase 0 impl lands.
phase0_impl = pytest.mark.skip(reason="Phase 0 implementation pending — review as acceptance spec")
