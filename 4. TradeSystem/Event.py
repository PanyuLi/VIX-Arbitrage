# -*- coding: utf-8 -*-
"""
Created on Sun Feb 21 12:49:26 2021

@author: cherry
"""

from abc import ABCMeta


class Event(object, metaclass=ABCMeta):
    pass


class BarEvent(Event):
    def __init__(self, dt):
        self.type = 'Bar'
        self.dt = dt


class SignalEvent(Event):
    def __init__(self, dt, symbol, direction, action, quantity, price, 
                 adj_price, adj_factor, signal_type=None, margin_rate=0.5, multiplier=1):
        self.type = 'Signal'
        self.dt = dt
        self.symbol = symbol
        self.direction = direction
        self.action = action
        self.quantity = quantity
        self.price = price
        self.adj_price = adj_price
        self.adj_factor = adj_factor
        self.signal_type = signal_type  # 型号类型
        self.margin_rate = margin_rate  # 保证金率，0~1.0，股票默认是1.0
        self.multiplier = multiplier  # 合约乘数，股票默认是1.0，IF默认300
        
    def __str__(self):
        return 'SignalEvent【{}】,数量:{},方向:{},动作:{},日期:{}'.format( self.symbol, self.quantity, self.direction, self.action, self.dt)
        
        

class OrderEvent(Event):
    def __init__(self, dt, symbol, direction, action, quantity, price, 
                 adj_price, adj_factor, order_type=None, margin_rate=0.5, multiplier=1):
        self.type = 'Order'
        self.dt = dt
        self.symbol = symbol
        self.direction = direction
        self.action = action
        self.quantity = quantity
        self.price = price
        self.adj_price = adj_price
        self.adj_factor = adj_factor
        self.margin_rate = margin_rate  # 保证金率，0~1.0，股票默认是1.0
        self.multiplier = multiplier  # 合约乘数，股票默认是1.0，IF默认300
        
    def __str__(self):
        return 'OrderEvent【{}】,数量:{},方向:{},动作:{},日期:{}'.format( self.symbol, self.quantity, self.direction, self.action, self.dt)

class FillEvent(Event):
    def __init__(self, dt, symbol, direction, action, quantity, adj_quantity, price, 
                 adj_price, fill_price, adj_fill_price, adj_factor, amount, fee, 
                 fill_type=None, margin_rate=0.5, multiplier=1):
        self.type = 'Fill'
        self.dt = dt
        self.symbol = symbol
        self.direction = direction
        self.action = action
        self.quantity = quantity
        self.adj_quantity = adj_quantity  # 复权数量
        self.price = price
        self.adj_price = adj_price
        self.fill_price = fill_price
        self.adj_fill_price = adj_fill_price  # 复权成交价格
        self.adj_factor = adj_factor
        self.amount = amount  # 成交金额
        self.fee = abs(fee)  # 手续费等费用
        self.margin_rate = margin_rate  # 保证金率，0~1.0，股票默认是1.0
        self.multiplier = multiplier  # 合约乘数，股票默认是1.0，IF默认300
    
    def __str__(self):
        out = 'FillEvent【{}】, 数量:{}, 方向:{}, 动作:{},日期:{}, 成交价:{},费用:{}'.format(self.symbol, 
            self.quantity, self.direction, self.action, self.dt, self.fill_price, abs(self.fee))
        return out
        
        
        
        
        
        
        
        
        
        
        
    