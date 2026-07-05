import pytest

from harpi.domain.volume import validate_volume


class TestValidateVolumeBVA:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(0.0, id="minimum"),
            pytest.param(0.001, id="just-above-minimum"),
            pytest.param(0.5, id="midpoint"),
            pytest.param(0.999, id="just-below-maximum"),
            pytest.param(1.0, id="maximum"),
        ],
    )
    def test_valid_volumes_accepted(self, value: float):
        validate_volume(value)

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(-0.1, id="below-minimum"),
            pytest.param(1.1, id="above-maximum"),
            pytest.param(-1.0, id="far-below-minimum"),
            pytest.param(2.0, id="far-above-maximum"),
        ],
    )
    def test_invalid_volumes_rejected(self, value: float):
        with pytest.raises(ValueError, match="must be between"):
            validate_volume(value)

    def test_custom_name_in_error(self):
        with pytest.raises(ValueError, match="Duck level"):
            validate_volume(-0.1, "Duck level")

    def test_default_name_in_error(self):
        with pytest.raises(ValueError, match="^Volume must be between"):
            validate_volume(-0.1)
