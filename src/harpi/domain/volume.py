MIN_VOLUME: float = 0.0
MAX_VOLUME: float = 1.0


def validate_volume(value: float, name: str = "Volume") -> None:
    if not MIN_VOLUME <= value <= MAX_VOLUME:
        raise ValueError(
            f"{name} must be between {MIN_VOLUME} and {MAX_VOLUME}, got {value}"
        )
