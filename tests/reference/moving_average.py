def moving_average(values: list[float], window: int) -> list[float]:
    if window < 1:
        raise ValueError("window must be at least 1")
    return [
        round(sum(values[i : i + window]) / window, 2) for i in range(len(values) - window + 1)
    ]
