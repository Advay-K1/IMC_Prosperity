import pandas as pd


crates = [
    (10, 1), (80, 6), (37, 3), (17, 1), (50, 4),
    (31, 2), (90, 10), (20, 2), (73, 4), (89, 8)
]

base = 10_000

rows = []
for mult, n in crates:
    for p in range(0, 91, 5):   
        denom = n + p
        payout = (base * mult) / denom if denom > 0 else 0
        rows.append({
            "Multiplier": mult,
            "Inhabitants": n,
            "% Picks (p)": p,
            "Payout": payout
        })

df = pd.DataFrame(rows)

pivot = df.pivot_table(
    index=["Multiplier", "Inhabitants"],
    columns="% Picks (p)",
    values="Payout"
)

pivot.to_excel("crate_payouts.xlsx")