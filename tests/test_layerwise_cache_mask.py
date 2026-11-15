import pytest
import torch

from authoritykv_experiments.layerwise_cache_mask import (
    adapt_attention_mask,
)


def test_uniform_length_returns_original_tensor() -> None:
    mask = torch.arange(12).reshape(1, 1, 3, 4)
    adjusted = adapt_attention_mask(
        mask,
        past_length=1,
        query_length=3,
    )
    assert adjusted is mask


def test_heterogeneous_length_keeps_prefix_and_query_tail() -> None:
    mask = torch.arange(24).reshape(1, 1, 3, 8)
    adjusted = adapt_attention_mask(
        mask,
        past_length=2,
        query_length=3,
    )
    expected = torch.cat((mask[..., :2], mask[..., -3:]), dim=-1)
    assert adjusted.shape[-1] == 5
    assert torch.equal(adjusted, expected)


def test_short_shared_mask_is_rejected() -> None:
    mask = torch.zeros(1, 1, 1, 4)
    with pytest.raises(RuntimeError, match="shorter than the layer cache"):
        adapt_attention_mask(
            mask,
            past_length=4,
            query_length=1,
        )
