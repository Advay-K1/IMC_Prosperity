import random

def get_bids():
    # First bid strategy - target lower range with some randomness
    first_bid = random.choice([x for x in range(160, 201) if x not in range(200, 251)])
    
    # Second bid strategy - slightly above expected average
    second_bid = random.randint(305, 315)
    
    return {
        "FLIPPERS": [
            {"price": first_bid, "quantity": 1},
            {"price": second_bid, "quantity": 1}
        ]
    }

def estimate_second_bid_average():
    # This could be improved with historical data analysis
    return 300  # Conservative estimate