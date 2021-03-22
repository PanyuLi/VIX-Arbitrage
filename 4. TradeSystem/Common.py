# -*- coding: utf-8 -*-
"""
Created on Sun Feb 21 23:15:27 2021

@author: cherry
"""

class OrderCost(object):
    """
    订单交易费率和滑点设置
    """
    def __init__(self):
        self.open_commission = 0.0  # 开仓费率
        self.close_commission = 0.0  # 平仓费率
        self.open_tax = 0.0  # 开仓税金
        self.close_tax = 0.0  # 平仓税金
        self.open_slippage = 0.0  # 开仓滑点
        self.close_slippage = 0.0  # 平仓滑点
        self.min_commission = 0.0  # 最低佣金