"""Fixtures shared by the tests; the fakes themselves live in `cltrplusf.testing`."""

from __future__ import annotations

import pytest

from cltrplusf.testing import BagOfWordsEmbedder, fake_docling

__all__ = ["fake_docling"]


@pytest.fixture
def embedder() -> BagOfWordsEmbedder:
    return BagOfWordsEmbedder()
