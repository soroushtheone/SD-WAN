POLICIES = {
    "voip": {
        "metric": "latency+jitter",
        "prefer_stable": True
    },
    "bulk": {
        "metric": "cost",
        "prefer_any": True
    },
    "video": {
        "metric": "latency",
        "prefer_low_latency": True
    }
}
