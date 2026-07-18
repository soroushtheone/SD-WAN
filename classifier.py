def classify(flow):
    port = flow.get("port")

    if port in [5060] or (10000 <= port <= 20000):
        return "voip"

    if port in [80, 443]:
        return "bulk"

    return "bulk"
