from datamodel import Order, TradingState
import numpy as np
import math











# inherited common methods
class Strategy:
    def __init__(self, symbol: str, limit: int) -> None:
        self.symbol = symbol
        self.limit = limit
        self.state = {}

    def run(self, state: TradingState) -> list[Order]:
        self.orders = []
        return self.act(state)

    def buy(self, price: int, quantity: int) -> None:
        self.orders.append(Order(self.symbol, int(price), quantity))

    def sell(self, price: int, quantity: int) -> None:
        self.orders.append(Order(self.symbol, int(price), -quantity))






#stable
class ResinStrategy(Strategy):
     def __init__(self, symbol: str, limit: int) -> None:
         super().__init__(symbol, limit)
         self.fair_value = 10000
         self.take_width = 1
         self.edge_width = 2
     def act(self, state: TradingState) -> list[Order]:
         order_depth = state.order_depths[self.symbol]
         position = state.position.get(self.symbol, 0)
         if not order_depth.buy_orders and not order_depth.sell_orders:
             return []
         buy_volume = 0
         sell_volume = 0
         # MARKET TAKE, BUY AND SELL ON THE EDGE
         best_ask = min(order_depth.sell_orders.keys(), default=None)
         best_bid = max(order_depth.buy_orders.keys(), default=None)
         if best_ask is not None and best_ask <= self.fair_value - self.take_width:
             quantity = min(-order_depth.sell_orders[best_ask], self.limit - position)
             if quantity > 0:
                 self.buy(best_ask, quantity)
                 buy_volume += quantity
         if best_bid is not None and best_bid >= self.fair_value + self.take_width:
             quantity = min(order_depth.buy_orders[best_bid], self.limit + position)
             if quantity > 0:
                 self.sell(best_bid, quantity)
                 sell_volume += quantity
         # STAY NEAR ZERO, CLEAR INVENTORY LOGIC
         fair_bid = self.fair_value
         fair_ask = self.fair_value
         # Net inventory after expected market taking
         net_position = position + buy_volume - sell_volume
         # Clear long position at fair ask if buyer exists
         if net_position > 0 and fair_ask in order_depth.buy_orders:
             max_qty = min(order_depth.buy_orders[fair_ask], net_position)
             self.sell(fair_ask, max_qty)
             sell_volume += max_qty
         # Clear short position at fair bid if seller exists
         if net_position < 0 and fair_bid in order_depth.sell_orders:
             max_qty = min(-order_depth.sell_orders[fair_bid], -net_position)
             self.buy(fair_bid, max_qty)
             buy_volume += max_qty
         # MARKET MAKE, FIND A LARGE SPREAD AND PLACE ORDERS JUST INSIDE OF IT
         book_asks = [p for p in order_depth.sell_orders if p > self.fair_value + self.edge_width - 1]
         book_bids = [p for p in order_depth.buy_orders if p < self.fair_value - self.edge_width + 1]
         ask_quote = min(book_asks, default=self.fair_value + self.edge_width) - 1
         bid_quote = max(book_bids, default=self.fair_value - self.edge_width) + 1
         buy_qty = self.limit - (position + buy_volume)
         sell_qty = self.limit + (position - sell_volume)
         if buy_qty > 0:
             self.buy(bid_quote, buy_qty)
         if sell_qty > 0:
             self.sell(ask_quote, sell_qty)
         return self.orders





# #volatile
class KelpStrategy(Strategy):
 def __init__(self, symbol: str, limit: int) -> None:
     super().__init__(symbol, limit)
     self.take_width = 1
     self.edge_width = 3.5
     self.tick = 0
     self.kelp_prices = []
     self.kelp_vwap = []
 def act(self, state: TradingState) -> list[Order]:
     self.tick += 1
     order_depth = state.order_depths[self.symbol]
     position = state.position.get(self.symbol, 0)
     if not order_depth.buy_orders or not order_depth.sell_orders:
         return []
     best_ask = min(order_depth.sell_orders.keys())
     best_bid = max(order_depth.buy_orders.keys())

     # --- Filtered Fair Value ---
     filtered_asks = [p for p in order_depth.sell_orders if -order_depth.sell_orders[p] >= 15]
     filtered_bids = [p for p in order_depth.buy_orders if order_depth.buy_orders[p] >= 15]
     mm_ask = min(filtered_asks) if filtered_asks else best_ask
     mm_bid = max(filtered_bids) if filtered_bids else best_bid
     mmmid_price = (mm_bid + mm_ask) / 2
     self.kelp_prices.append(mmmid_price)
     volume = -order_depth.sell_orders[best_ask] + order_depth.buy_orders[best_bid]
     if volume != 0:
         vwap = (best_bid * (-order_depth.sell_orders[best_ask]) + best_ask * order_depth.buy_orders[best_bid]) / volume
     else:
         vwap = mmmid_price
     self.kelp_vwap.append({"vol": volume, "vwap": vwap})
     if len(self.kelp_prices) > 20:
         self.kelp_prices.pop(0)
     if len(self.kelp_vwap) > 20:
         self.kelp_vwap.pop(0)
     fair_value = mmmid_price  # Using filtered mid as fair value
     orders = []
     buy_volume = 0
     sell_volume = 0
     # --- Market Taking ---
     if best_ask <= fair_value - self.take_width:
         ask_volume = -order_depth.sell_orders[best_ask]
         if ask_volume <= 20:
             qty = min(ask_volume, self.limit - position)
             if qty > 0:
                 self.buy(best_ask, qty)
                 buy_volume += qty
     if best_bid >= fair_value + self.take_width:
         bid_volume = order_depth.buy_orders[best_bid]
         if bid_volume <= 20:
             qty = min(bid_volume, self.limit + position)
             if qty > 0:
                 self.sell(best_bid, qty)
                 sell_volume += qty
     # --- Position Clearing ---
     post_take_pos = position + buy_volume - sell_volume
     fair_bid = math.floor(fair_value)
     fair_ask = math.ceil(fair_value)
     buy_clear_qty = self.limit - (position + buy_volume)
     sell_clear_qty = self.limit + (position - sell_volume)
     if post_take_pos > 0 and fair_ask in order_depth.buy_orders:
         clear_qty = min(order_depth.buy_orders[fair_ask], post_take_pos, sell_clear_qty)
         if clear_qty > 0:
             self.sell(fair_ask, clear_qty)
             sell_volume += clear_qty
     if post_take_pos < 0 and fair_bid in order_depth.sell_orders:
         clear_qty = min(-order_depth.sell_orders[fair_bid], -post_take_pos, buy_clear_qty)
         if clear_qty > 0:
             self.buy(fair_bid, clear_qty)
             buy_volume += clear_qty

     # --- Market Making ---
     aaf = [p for p in order_depth.sell_orders if p > fair_value + 1]
     bbf = [p for p in order_depth.buy_orders if p < fair_value - 1]
     baaf = min(aaf) if aaf else fair_value + 2
     bbbf = max(bbf) if bbf else fair_value - 2
     buy_qty = self.limit - (position + buy_volume)
     sell_qty = self.limit + (position - sell_volume)
     if buy_qty > 0:
         self.buy(int(bbbf + 1), buy_qty)
     if sell_qty > 0:
         self.sell(int(baaf - 1), sell_qty)
     return self.orders




#volatile with only 1-2 active participants
# super volatile pnl need to clean this up

class SquidInkStrategy(Strategy):
    def __init__(self, symbol: str, limit: int) -> None:
        super().__init__(symbol, limit)
        # Initialize internal state storage in our own state dictionary.
        self.state = {}
        self.state.setdefault("prices", [])
        self.state.setdefault("position", 0)
        self.state.setdefault("entry_price", None)  

        self.rolling_window = 50         
        self.z_entry_threshold = 1.5       
        self.z_exit_threshold = 0.3
        self.max_position = 50        

        # Dynamic trade sizing
        self.min_trade_qty = 5             # Minimum quantity to trade
        self.max_trade_qty = 30            # Maximum quantity to trade

        # Profit-taking settings
        self.profit_take_threshold = 300   # Profit (in tick-units) to trigger profit taking
        self.profit_lock_steps = 5         # Number of units to exit when profit target is reached

    def calculate_dynamic_quantity(self, z_score: float) -> int:
        strength = abs(z_score) / self.z_entry_threshold
        qty = self.min_trade_qty + (strength - 1) * (self.max_trade_qty - self.min_trade_qty)
        return max(self.min_trade_qty, min(int(qty), self.max_trade_qty))

    def update_entry_price(self, midprice: float, trade_qty: int, position: int):
        entry_price = self.state.get("entry_price")
        abs_pos = abs(position)
        if abs_pos == 0:
            self.state["entry_price"] = midprice
        elif entry_price is not None:
            total_value = entry_price * abs_pos + midprice * abs(trade_qty)
            new_qty = abs_pos + abs(trade_qty)
            self.state["entry_price"] = total_value / new_qty

    def check_take_profit(self, midprice: float, position: int) -> bool:
        entry_price = self.state.get("entry_price")
        if entry_price is None:
            return False
        pnl = 0
        if position > 0:
            pnl = (midprice - entry_price) * position
        elif position < 0:
            pnl = (entry_price - midprice) * abs(position)
        return pnl >= self.profit_take_threshold

    def get_mid_price(self, order_depth) -> float:
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2.0

    def act(self, state: 'TradingState') -> list:
        self.orders = []
        product = self.symbol
        order_depth = state.order_depths.get(product)
        if not order_depth:
            return self.orders

        position = state.position.get(product, 0)
        self.state["position"] = position

        midprice = self.get_mid_price(order_depth)
        if midprice is None:
            return self.orders

        # Update price history in state.
        self.state["prices"].append(midprice)
        prices = self.state["prices"]
        if len(prices) < self.rolling_window:
            return []  # Wait until enough data is collected.

        # --- Profit-taking override ---
        if self.check_take_profit(midprice, position):
            if position > 0:
                self.sell(int(midprice), min(position, self.profit_lock_steps))
            elif position < 0:
                self.buy(int(midprice), min(-position, self.profit_lock_steps))
            return self.orders  # Skip further logic this tick.

        # Compute rolling statistics.
        recent = prices[-self.rolling_window:]
        mean_price = np.mean(recent)
        std_price = np.std(recent)
        if std_price == 0:
            return self.orders

        # Compute z-score for current midprice.
        z = (midprice - mean_price) / std_price

      

        # --- Entry logic: only if flat.
        if z < -self.z_entry_threshold and position < self.max_position:
            qty = min(self.calculate_dynamic_quantity(z), self.max_position - position)
            if qty > 0:
                self.update_entry_price(midprice, qty, position)
                self.buy(int(midprice), qty)

        elif z > self.z_entry_threshold and position > -self.max_position:
            qty = min(self.calculate_dynamic_quantity(z), self.max_position + position)
            if qty > 0:
                self.update_entry_price(midprice, - qty, position)
                self.sell(int(midprice), qty)

        # Exit logic
        elif abs(z) < self.z_exit_threshold and position != 0:
            self.sell(int(midprice), position)
            self.state["entry_price"] = None  

        return self.orders



#main 
class Trader:
    
    def __init__(self) -> None:
    
      # rr is stable while kelp is volatile
      self.limits = { 
          "RAINFOREST_RESIN" : 50,
          "KELP" : 50,  
          "SQUID_INK" : 50,
      }

      strategy_classes = {
          "RAINFOREST_RESIN" : ResinStrategy,
          "KELP" : KelpStrategy,
          "SQUID_INK" : SquidInkStrategy,
    
      }

      self.strategies = {
            symbol: strategy_class(symbol, self.limits[symbol])
            for symbol, strategy_class in strategy_classes.items()
      }

    
    
    def run(self, state: TradingState):

        print(f"{state.position}")
        
        result = {}
        # NO CONVERSIONS FIRST ROUND
        CONVERSIONS = 0
        traderData = ""

        for symbol, strategy in self.strategies.items():
            if symbol in state.order_depths:
                orders = strategy.run(state)
                result[symbol] = orders

        return result, CONVERSIONS, traderData

  
                

