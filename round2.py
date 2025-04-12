from datamodel import Order, TradingState
import numpy as np
import math
from collections import defaultdict






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
     fair_value = mmmid_price 

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

    def act(self, state: 'TradingState') -> list:
        return self.orders




class BasketStrategy(Strategy):
    def __init__(self, symbol: str, limit: int):
        super().__init__(symbol, limit)

    def act(self, state: TradingState) -> None:
        if any(symbol not in state.order_depths for symbol in ["CROISSANTS", "JAMS", "DJEMBES", "PICNIC_BASKET1", "PICNIC_BASKET2"]):
            return

        croissants = self.get_mid_price(state, "CROISSANTS")
        jams = self.get_mid_price(state, "JAMS")
        djembes = self.get_mid_price(state, "DJEMBES")
        basket1 = self.get_mid_price(state, "PICNIC_BASKET1")
        basket2 = self.get_mid_price(state, "PICNIC_BASKET2")

        value1 = 6 * croissants + 3 * jams + 1 * djembes
        value2 = 4 * croissants + 2 * jams

        diff = 0

        if self.symbol == "PICNIC_BASKET1":
            diff = basket1 - value1
        elif self.symbol == "PICNIC_BASKET2":
            diff = basket2 - value2
        elif self.symbol == "CROISSANTS":
            implied1 = basket1 * 6 / 10
            implied2 = basket2 * 4 / 6
            avg_implied = (implied1 + implied2) / 2
            diff = croissants - avg_implied
        elif self.symbol == "JAMS":
            implied1 = basket1 * 3 / 10
            implied2 = basket2 * 2 / 6
            avg_implied = (implied1 + implied2) / 2
            diff = jams - avg_implied
        elif self.symbol == "DJEMBES":
            implied = basket1 * 1 / 10  
            diff = djembes - implied

        # Thresholds from CSV analysis (2 std dev wide around mean diff)
        long_threshold, short_threshold = {
            "CROISSANTS": (-23420.47, -23397.54),
            "JAMS": (-11615.67, -11578.34),
            "DJEMBES": (-3265.23, -3241.41),
            "PICNIC_BASKET1": (-109.24, 103.47),
            "PICNIC_BASKET2": (-63.87, 64.92),
        }[self.symbol]

        if diff < long_threshold:
            self.go_long(state)
        elif diff > short_threshold:
            self.go_short(state)
        
        return self.orders

    def get_mid_price(self, state: TradingState, symbol: str) -> float:
        order_depth = state.order_depths[symbol]
        buy_orders = sorted(order_depth.buy_orders.items(), reverse=True)
        sell_orders = sorted(order_depth.sell_orders.items())

        popular_buy_price = max(buy_orders, key=lambda tup: tup[1])[0]
        popular_sell_price = min(sell_orders, key=lambda tup: tup[1])[0]

        return (popular_buy_price + popular_sell_price) / 2

    def go_long(self, state: TradingState) -> None:
        order_depth = state.order_depths[self.symbol]
        price = max(order_depth.sell_orders.keys())

        position = state.position.get(self.symbol, 0)
        available_qty = self.limit - position
        scaled_qty = max(1, min(10 + int(abs(position) * 0.5), available_qty))

        self.buy(price, scaled_qty)

    def go_short(self, state: TradingState) -> None:
        order_depth = state.order_depths[self.symbol]
        price = min(order_depth.buy_orders.keys())

        position = state.position.get(self.symbol, 0)
        available_qty = self.limit + position
        scaled_qty = max(1, min(10 + int(abs(position) * 0.5), available_qty))

        self.sell(price, scaled_qty)





#main 
class Trader:
    
    def __init__(self) -> None:
    
      # rr is stable while kelp is volatile
      self.limits = { 
          "RAINFOREST_RESIN" : 50,
          "KELP" : 50,  
          #"SQUID_INK" : 50,
          "CROISSANTS" : 250,
          "JAMS" : 50,
          "DJEMBES" : 60,
          "PICNIC_BASKET1" : 60,
          "PICNIC_BASKET2" : 100,
      }

      strategy_classes = {
          "RAINFOREST_RESIN" : ResinStrategy,
          "KELP" : KelpStrategy,
          #"SQUID_INK" : SquidInkStrategy,
          "CROISSANTS" : BasketStrategy,
          "JAMS" : BasketStrategy,
          "DJEMBES" : BasketStrategy,
          "PICNIC_BASKET1" : BasketStrategy,
          "PICNIC_BASKET2" : BasketStrategy,
    
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
    
        
  
                

