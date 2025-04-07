from collections import deque

def MaximizeTrades():
    rates = {
        "Snowballs": {"Pizza": 1.45, "Silicon Nuggets": 0.52, "SeaShells": 0.72},
        "Pizza": {"Snowballs": 0.7, "Silicon Nuggets": 0.31, "SeaShells": 0.48},
        "Silicon Nuggets": {"Snowballs": 1.95, "Pizza": 3.1, "SeaShells": 1.49},
        "SeaShells": {"Snowballs": 1.34, "Pizza": 1.98, "Silicon Nuggets": 0.64}
    }

    max_trades = 5
    start_amount = 1.0
    max_value = start_amount
    all_paths = []

    queue = deque()
    queue.append(("SeaShells", start_amount, 0, ["SeaShells"]))

    while queue:
        curr_currency, curr_amount, trades, path = queue.popleft()

        if curr_currency == "SeaShells" and curr_amount >= 1:
            all_paths.append((curr_amount, path))
            max_value = max(max_value, curr_amount)

        if trades == max_trades:
            continue

        for next_currency, rate in rates[curr_currency].items():
            next_amount = curr_amount * rate
            next_path = path + [next_currency]
            queue.append((next_currency, next_amount, trades + 1, next_path))

    print("Paths ending in SeaShells:")
    for amount, path in all_paths:
        print(f"{' → '.join(path)} | Amount: {amount:.5f}")

    # Final result
    print(f"\nMaximum SeaShells after up to {max_trades} trades: {max_value:.5f}")


MaximizeTrades()