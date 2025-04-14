# Trading parameters
POSITION_LIMITS = {
    'VOUCHER_1': 100,
    'VOUCHER_2': 100,
    'VOUCHER_3': 100,
    'VOUCHER_4': 100,
    'VOUCHER_5': 100,
    'FLIPPERS': 2
}

# Risk management
MAX_LOSS_PER_TRADE = 1000  # SeaShells
MAX_DAILY_LOSS = 5000      # SeaShells

# Manual trading parameters
FLIPPER_RESERVE_RANGES = [
    (160, 200),
    (250, 320)
]

# Enhanced trading hours configuration
TRADING_HOURS = {
    'VOUCHER_1': (9, 16),  # 9AM to 4PM
    'VOUCHER_2': (9, 16),
    'VOUCHER_3': (9, 16),
    'VOUCHER_4': (9, 16),
    'VOUCHER_5': (9, 16),
    'FLIPPERS': (9, 16),
}

# Dynamic position limits based on time to expiry
def get_voucher_position_limit(product, days_to_expiry):
    base_limit = POSITION_LIMITS.get(product, 100)
    return max(10, base_limit * (days_to_expiry / 7))  # Reduce as expiry approaches