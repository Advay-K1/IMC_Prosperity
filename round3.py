from datamodel import Order, TradingState
import numpy as np
import math
from collections import defaultdict, deque
import statistics
from statistics import NormalDist
from statistics import stdev
from math import log, sqrt, exp
from collections import deque






# inherited common methods
class Strategy:
    def __init__(self, symbol: str, limit: int) -> None:
        self.symbol = symbol
        self.limit = limit
        self.state = {}
        self.hedge_targets = defaultdict(int) 


    def run(self, state: TradingState) -> list[Order]:
        self.orders = []
        return self.act(state)

    def buy(self, price: int, quantity: int) -> None:
        print(f"[BUY] {self.symbol}: {quantity} @ {price}")
        self.orders.append(Order(self.symbol, int(price), quantity))

    def sell(self, price: int, quantity: int) -> None:
        print(f"[SELL] {self.symbol}: {quantity} @ {price}")
        self.orders.append(Order(self.symbol, int(price), -quantity))
    
    def get_mid_price(self, state: TradingState, sym: str):
        od = state.order_depths.get(sym)
        if not od or not od.buy_orders or not od.sell_orders:
            return None
        return (max(od.buy_orders) + min(od.sell_orders)) / 2







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
    def __init__(self, symbol: str, limit: int):
        super().__init__(symbol, limit)

    def act(self, state: TradingState) -> list[Order]:
        return self.orders




class BasketStrategy(Strategy):
    def __init__(self, symbol: str, limit: int):
        super().__init__(symbol, limit)
        self.component_recipes = {
            "PICNIC_BASKET1": {"CROISSANTS": 6, "JAMS": 3, "DJEMBES": 1},
            "PICNIC_BASKET2": {"CROISSANTS": 4, "JAMS": 2},
        }
        self.threshold = 20

    def act(self, state: TradingState) -> list[Order]:
        self.orders = []
        if self.symbol not in self.component_recipes:
            return []

        components = self.component_recipes[self.symbol]
        od = state.order_depths.get(self.symbol)
        if not od:
            return []

        basket_mid = self.get_mid_price(state, self.symbol)
        if basket_mid is None:
            return []

        component_value = 0
        for sym, qty in components.items():
            comp_mid = self.get_mid_price(state, sym)
            if comp_mid is None:
                return []
            component_value += qty * comp_mid

        diff = basket_mid - component_value
        position = state.position.get(self.symbol, 0)

        if diff > self.threshold:
            price = max(od.buy_orders)  
            qty = min(abs(od.buy_orders.get(price, 0)), self.limit + position)
            if qty > 0:
                self.sell(price, qty)

        elif diff < -self.threshold:
            price = min(od.sell_orders)  
            qty = min(abs(-od.sell_orders.get(price, 0)), self.limit - position)
            if qty > 0:
                self.buy(price, qty)

        return self.orders








    






class CroissantStrategy(Strategy):
    def __init__(self, symbol: str, limit: int):
        super().__init__(symbol, limit)

    def act(self, state: TradingState) -> list[Order]:
       

        return self.orders



# ---------- Component Strategy for JAMS ----------
class JamStrategy(Strategy):
    def __init__(self, symbol: str, limit: int):
        super().__init__(symbol, limit)
        self.window = deque(maxlen=30)
        self.threshold = 1.5
        self.buffer = 10

    def act(self, state: TradingState) -> list[Order]:
        order_depth = state.order_depths[self.symbol]
        position = state.position.get(self.symbol, 0)

        if not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        best_bid = max(order_depth.buy_orders)
        best_ask = min(order_depth.sell_orders)
        mid_price = (best_bid + best_ask) / 2

        def mid(sym):
            d = state.order_depths.get(sym, None)
            if not d or not d.buy_orders or not d.sell_orders:
                return None
            return (max(d.buy_orders) + min(d.sell_orders)) / 2

        b1 = mid("PICNIC_BASKET1")
        b2 = mid("PICNIC_BASKET2")
        c = mid("CROISSANTS")
        d = mid("DJEMBES")

        if None in [b1, b2, c, d]:
            return []

        synth_jam_1 = (b1 - 6 * c - d) / 3
        synth_jam_2 = (b2 - 4 * c) / 2
        spread1 = synth_jam_1 - mid_price
        spread2 = synth_jam_2 - mid_price

        if not (spread1 * spread2 > 20):  
            return []



        spread = ((synth_jam_1 + synth_jam_2) / 2) - mid_price
        self.window.append(spread)

        if len(self.window) < self.window.maxlen:
            return []

        mean = statistics.mean(self.window)
        stdev = statistics.stdev(self.window)
        if stdev == 0:
            return []

        zscore = (spread - mean) / stdev

        if zscore > self.threshold:
            vol = min(order_depth.buy_orders.get(best_bid, 0), self.limit - position - self.buffer)
            if vol > 0:
                self.sell(best_bid, vol)
        elif zscore < -self.threshold:
            vol = min(-order_depth.sell_orders.get(best_ask, 0), self.limit + position - self.buffer)
            if vol > 0:
                self.buy(best_ask, vol)

        return self.orders



# ---------- Component Strategy for DJEMBES ----------
class DjembeStrategy(Strategy):
    def __init__(self, symbol: str, limit: int):
        super().__init__(symbol, limit)

    def act(self, state: TradingState) -> list[Order]:

        return self.orders
    




class VoucherStrategy(Strategy):
     def __init__(self, symbol: str, limit: int):
         super().__init__(symbol, limit)
         self.rock_history = []
         self.max_order_size = 10
         self.max_position = 200
         self.band_width = 5


     def get_strike(self, product: str) -> int:
         return int(product.split("_")[-1])
     def get_mid_price(self, state, product: str) -> float | None:
         od = state.order_depths.get(product)
         if od and od.buy_orders and od.sell_orders:
             return (max(od.buy_orders) + min(od.sell_orders)) / 2
         return None
     
     def estimate_volatility(self, prices):
         if len(prices) < 2:
             return 0.01
         log_returns = np.diff(np.log(prices[-30:]))
         return max(0.01, np.std(log_returns))
     

     
     def black_scholes_call(self, S, K, T, r, sigma):
         if T <= 0 or sigma <= 0:
             return max(0, S - K)
         d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
         d2 = d1 - sigma * math.sqrt(T)
         return S * NormalDist().cdf(d1) - K * math.exp(-r * T) * NormalDist().cdf(d2)
     
     def act(self, state: TradingState) -> list[Order]:
         self.orders = []

         if "VOUCHER" not in self.symbol:
             return []
         
         rock_mid = self.get_mid_price(state, "VOLCANIC_ROCK")

         if rock_mid is None:
             return []
         
         self.rock_history.append(rock_mid)

         if len(self.rock_history) < 30:
             return []
         
         smooth_rock = np.mean(self.rock_history[-30:])
         sigma = self.estimate_volatility(self.rock_history)

         r = 0.0 
         round = state.timestamp
         rounds_left = max(1, 8 - round)

         T = rounds_left / 365

         strike = self.get_strike(self.symbol)
         fair_value = self.black_scholes_call(smooth_rock, strike, T, r, sigma)
         od = state.order_depths[self.symbol]

         best_bid = max(od.buy_orders.keys(), default=None)
         best_ask = min(od.sell_orders.keys(), default=None)
         position = state.position.get(self.symbol, 0)

         # --- BUY if market is undervalued ---
         if best_ask is not None and best_ask < fair_value - self.band_width:
             distance = fair_value - best_ask
             scale = min((distance / self.band_width) ** 1.5, 2)
             volume = int(scale * self.max_order_size)
             volume = min(volume, self.max_position - position)
             if volume > 0:
                 self.buy(best_ask, volume)

         # --- SELL if market is overvalued ---
         if best_bid is not None and best_bid > fair_value + self.band_width:
             distance = best_bid - fair_value
             scale = min((distance / self.band_width) ** 1.5, 2)
             volume = int(scale * self.max_order_size)
             volume = min(volume, self.max_position + position)
             if volume > 0:
                 self.sell(best_bid, volume)
                 
         return self.orders







class RockStrategy(Strategy):
    def __init__(self, symbol: str, limit: int):
        super().__init__(symbol, limit)

    def act(self, state: TradingState) -> list[Order]:

        return self.orders














#main 
class Trader:
    
    def __init__(self) -> None:

      self.limits = { 
          "RAINFOREST_RESIN" : 50,
          "KELP" : 50,  
          "SQUID_INK" : 50,
          "CROISSANTS" : 250,
          "JAMS" : 350,
          "DJEMBES" : 60,
          "PICNIC_BASKET1" : 60,
          "PICNIC_BASKET2" : 100,
          "VOLCANIC_ROCK" : 400,
          "VOLCANIC_ROCK_VOUCHER_9500" : 200,
          "VOLCANIC_ROCK_VOUCHER_9750" : 200,
          "VOLCANIC_ROCK_VOUCHER_10000" : 200,
          "VOLCANIC_ROCK_VOUCHER_10250" : 200,
          "VOLCANIC_ROCK_VOUCHER_10500" : 200,
      }



      strategy_classes = {
          "RAINFOREST_RESIN" : ResinStrategy,
          "KELP" : KelpStrategy,
          "SQUID_INK" : SquidInkStrategy,
          "CROISSANTS" : CroissantStrategy,
          "JAMS" : JamStrategy,
          "DJEMBES" : DjembeStrategy,
          "PICNIC_BASKET1" : BasketStrategy,
          "PICNIC_BASKET2" : BasketStrategy,
          "VOLCANIC_ROCK" : RockStrategy,
          "VOLCANIC_ROCK_VOUCHER_9500" : VoucherStrategy,
          "VOLCANIC_ROCK_VOUCHER_9750" : VoucherStrategy,
          "VOLCANIC_ROCK_VOUCHER_10000" :VoucherStrategy,
          "VOLCANIC_ROCK_VOUCHER_10250" :VoucherStrategy,
          "VOLCANIC_ROCK_VOUCHER_10500" :VoucherStrategy,
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
    
        
  
                


