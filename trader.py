from collections import deque
from datamodel import Order, TradingState
from typing import List
import numpy as np
import math

class Strategy:
    def __init__(self, symbol: str, limit: int) -> None:
        self.symbol = symbol
        self.limit = limit

    def run(self, state: TradingState) -> list[Order]:
        self.orders = []
        return self.act(state)

    def buy(self, price: int, quantity: int) -> None:
        self.orders.append(Order(self.symbol, int(price), quantity))

    def sell(self, price: int, quantity: int) -> None:
        self.orders.append(Order(self.symbol, int(price), -quantity))


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


#volatile
class KelpStrategy(Strategy):
    def __init__(self, symbol: str, limit: int) -> None:
        super().__init__(symbol, limit)
        self.window = deque()
        self.window_size = 10

    def get_true_value(self, state: TradingState) -> int:
        order_depth = state.order_depths[self.symbol]
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return round((best_bid + best_ask) / 2)

    def act(self, state: TradingState) -> list[Order]:
        order_depth = state.order_depths[self.symbol]
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        true_value = self.get_true_value(state)

        buy_orders = sorted(order_depth.buy_orders.items(), reverse=True)
        sell_orders = sorted(order_depth.sell_orders.items())

        position = state.position.get(self.symbol, 0)
        potential_buy = self.limit - position
        potential_sell = self.limit + position

        self.window.append(abs(position) == self.limit)
        if len(self.window) > self.window_size:
            self.window.popleft()

        max_buy_price = true_value - 1 if position > self.limit * 0.5 else true_value
        min_sell_price = true_value + 1 if position < self.limit * -0.5 else true_value


        soft_liquidate = (
            len(self.window) == self.window_size and
            sum(self.window) >= self.window_size / 2 and
            self.window[-1]
        )
        hard_liquidate = (
            len(self.window) == self.window_size and
            all(self.window)
        )




        # buy logic
        for price, volume in sell_orders:
            if potential_buy > 0 and price <= max_buy_price:
                quantity = min(potential_buy, volume)
                self.buy(price, quantity)
                potential_buy -= quantity

     
        # liquidate buy if we're doing nothing
        if potential_buy > 0 and hard_liquidate:
            self.buy(true_value, potential_buy // 2)
            potential_buy -= potential_buy // 2

        if potential_buy > 0 and soft_liquidate:
            self.buy(true_value - 2, potential_buy // 2)
            potential_buy -= potential_buy // 2

        if potential_buy > 0:
            popular_buy_price = max(buy_orders, key=lambda tup: tup[1])[0]
            price = min(max_buy_price, popular_buy_price + 1)
            self.buy(price, potential_buy)


        # sell logic
        for price, volume in buy_orders:
            if potential_sell > 0 and price >= min_sell_price:
                quantity = min(potential_sell, volume)
                self.sell(price, quantity)
                potential_sell -= quantity

        # liquidate sell if we've been doing nothing
        if potential_sell > 0 and hard_liquidate:
            self.sell(true_value, potential_sell // 2)
            potential_sell -= potential_sell // 2

        if potential_sell > 0 and soft_liquidate:
            self.sell(true_value + 2, potential_sell // 2)
            potential_sell -= potential_sell // 2
        
        if potential_sell > 0:
            popular_sell_price = min(sell_orders, key=lambda tup: tup[1])[0]
            price = max(min_sell_price, popular_sell_price - 1)
            self.sell(price, potential_sell)


        return self.orders


class Trader:
    
    def __init__(self) -> None:
    
      # rr is stable while kelp is volatile
      self.limits = { 
          "RAINFOREST_RESIN" : 50,
          "KELP" : 50,  
      }

      strategy_classes = {
          "RAINFOREST_RESIN" : ResinStrategy,
          "KELP" : KelpStrategy,
    
      }

      self.strategies = {
            symbol: strategy_class(symbol, self.limits[symbol])
            for symbol, strategy_class in strategy_classes.items()
      }

    
    
    def run(self, state: TradingState):
        
        result = {}
        # NO CONVERSIONS FIRST ROUND
        CONVERSIONS = 0
        traderData = ""

        for symbol, strategy in self.strategies.items():
            if symbol in state.order_depths:
                orders = strategy.run(state)
                result[symbol] = orders
        return result, CONVERSIONS, traderData

  
                

