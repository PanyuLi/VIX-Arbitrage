# -*- coding: utf-8 -*-
"""
Created on Sun Feb 21 12:31:51 2021

@author: cherry
"""
from abc import ABCMeta, abstractmethod
from Event import SignalEvent, OrderEvent, FillEvent
from copy import deepcopy
import pandas as pd

class strategy(object, metaclass=ABCMeta):
    
    @abstractmethod
    def on_bar(self):
        raise NotImplementedError('未完成on_bar()函数！')
        
    @abstractmethod
    def on_signal(self):
        raise NotImplementedError('未完成on_signal()函数！')
        
    @abstractmethod
    def on_order(self):
        raise NotImplementedError('未完成on_order()函数！')
        
    @abstractmethod
    def on_fill(self):
        raise NotImplementedError('未完成on_fill()函数！')
    

class VixStrategy(strategy):
    def __init__(self, vix_data_handler, event, order_cost, start_date, initial_cash=1e7):
        self.vix_data_handler = vix_data_handler
        self.event = event
        self.positions = {}
        self.order_cost = order_cost
        self.flag_first_tradeday = True
        self.start_date = start_date
        self.initial_cash = initial_cash
        
        
        self.current_trades = {}
        self.all_trades = []
        self.all_trades_df = None
        
        self.current_composites = {}
        self.all_composites = []
        self.all_composites_df = None
        
        self.current_positions = {}
        self.all_positions = []
        self.all_positions_df = None
        
        self.current_holdings = self._generate_initial_holdings(self.start_date)
        self.all_holdings = []
        self.all_holdings_df = None
        
        
    def _order_quantity(self, symbol, dt, price, adj_factor, quantity, direction_str, signal_type=None):
        """

        Parameters
        ----------
        direction: {1: 多头；0：空头}
        action：{1：开仓；0：平仓}

        """
        if direction_str.lower() == 'long':
            direction = 1
            action = 1 if quantity > 0 else -1
        elif direction_str.lower() == 'short':
            direction = -1
            action = -1 if quantity > 0 else 1
        else:
            raise ValueError('请输入正确的下单参数！')
        adj_price = price * adj_factor
        
        # 触发signal事件
        signal_event = SignalEvent(dt, symbol, direction, action, abs(quantity), 
                                   price, adj_price, adj_factor, signal_type, 
                                   margin_rate=1, multiplier=1)
        self.event.put(signal_event)
        
    
    def on_bar(self, event):
        if event.type != 'Bar':
            return None
        
        dt = event.dt
        
        pos_dict = self.vix_data_handler.positions_df.loc[dt, 'positions'][0]
        
        while len(self.positions) > 0:
            ((symbol, direction), quantity) = self.positions.popitem()
            bar_dict = self.vix_data_handler.get_latest_bars(symbol)
            # print(bar_dict)
            close, adj_factor = bar_dict['close'], bar_dict['adj_factor']
            if direction == 1:
                self._order_quantity(symbol, dt, close, adj_factor, -quantity, 
                                 direction_str='long', signal_type='L_C')
                print('>>> {}：多头平仓，卖出【{}】{}股'.format(dt, symbol, quantity))
            else:
                self._order_quantity(symbol, dt, close, adj_factor, quantity, 
                                     direction_str='short', signal_type='S_C')
                print('>>> {}：空头平仓，买入【{}】{}股'.format(dt, symbol, quantity))
               
        amount = self.current_holdings['net_asset']
        for symbol in pos_dict.keys():
            bar_dict = self.vix_data_handler.get_latest_bars(symbol)
            # print(bar_dict)
            # if bar_dict['datetime'] != dt:
            #     return None
            close, adj_factor = bar_dict['close'], bar_dict['adj_factor']
            quantity = int(amount * abs(pos_dict[symbol]) / 100 / close)
            # print(amount, close, pos_dict[symbol], quantity)
            if abs(pos_dict[symbol]) < 1e-4:
                continue
            elif pos_dict[symbol] > 0:
                # 多头买入
                key = (symbol, 1)
                if key not in self.positions.keys():
                    self.positions[key] = quantity
                else:
                    self.positions[key] += quantity
                self._order_quantity(symbol, dt, close, adj_factor, quantity, 
                                     direction_str='long', signal_type='L_O')
                print('>>> {}：多头开仓，买入【{}】{}股'.format(dt, symbol, quantity))
            else:
                # 空头卖出
                key = (symbol, -1)
                if key not in self.positions.keys():
                    self.positions[key] = quantity
                else:
                    self.positions[key] += quantity
                self._order_quantity(symbol, dt, close, adj_factor, -quantity, 
                                     direction_str='short', signal_type='S_O')
                print('>>> {}：空头开仓，卖出【{}】{}股'.format(dt, symbol, quantity))
                
            
    
    def on_signal(self, event):
        if event.type != 'Signal':
            return None
        
        order_event = OrderEvent(event.dt, 
                                 event.symbol, 
                                 event.direction, 
                                 event.action, 
                                 event.quantity, 
                                 event.price, 
                                 event.adj_price, 
                                 event.adj_factor,
                                 event.margin_rate,
                                 event.multiplier) 
        self.event.put(order_event)
        
    
    def on_order(self, event):
        """
        确定执行价格、执行数量、佣金
        """
        if event.type != 'Order':
            return None
        
        if event.action > 0:   
            if event.direction > 0:
                # 多头开仓
                fill_price = (1 + self.order_cost.open_slippage) * event.price
            else:
                # 空头开仓
                fill_price = (1 - self.order_cost.open_slippage) * event.price
            adj_quantity = event.quantity / event.adj_factor
            adj_fill_price = fill_price * event.adj_factor
            amount = adj_fill_price * adj_quantity * event.multiplier
            fee_commission = amount * self.order_cost.open_commission
            fee_tax = amount * self.order_cost.open_tax
            if fee_commission < self.order_cost.min_commission:
                fee_commission = self.order_cost.min_commission
            fee = fee_commission + fee_tax
            
        elif event.action < 0:
            # 获取当前的仓位：有仓位才能平仓
            key = (event.symbol, event.direction)
            holdnum_now = self.current_positions.get(key, {}).get('holdnum_now', 0)
            if event.quantity > holdnum_now:
                print('({} , {})可平仓数目不足, 现有：{}, 拟平仓: {}'.format(event.symbol, event.direction, holdnum_now, event.quantity))
                return None
            else:
                adj_holdnum_now = self.current_positions[key]['adj_holdnum_now']
                adj_quantity = event.quantity * adj_holdnum_now / holdnum_now
                
            if event.direction > 0:
                # 多头平仓
                fill_price = (1 - self.order_cost.close_slippage) * event.price
            else:
                # 空头平仓
                fill_price = (1 + self.order_cost.close_slippage) * event.price
                
            adj_fill_price = fill_price * event.adj_factor
            amount = adj_fill_price * adj_quantity * event.multiplier
            fee_commission = amount * self.order_cost.close_commission
            fee_tax = amount * self.order_cost.close_tax
            if fee_commission < self.order_cost.min_commission:
                fee_commission = self.order_cost.min_commission
            fee = fee_commission + fee_tax
        else:
            raise ValueError('请输入正确的开平仓动作action!')
        
            
        
        fill_event = FillEvent(event.dt, event.symbol, event.direction, event.action, 
                               event.quantity, adj_quantity, event.price, event.adj_price, 
                               fill_price, adj_fill_price, event.adj_factor, amount, fee,
                               event.margin_rate, event.multiplier)
        self.event.put(fill_event)
   
    def on_fill(self, event):
        if event.type != 'Fill':
            return None
        
        self._update_trades_from_fill(event)
        self._update_composite_from_fill(event)
        self._update_positions_from_fill(event)
        self._update_holdings_from_fill(event)
    
    
    def _update_trades_from_fill(self, event):
        margin = event.amount * event.margin_rate
        if (event.direction > 0 and event.action > 0) or (event.direction < 0 and event.action < 0):
            # 买入
            buy_amount = event.amount
            sell_amount = 0.
        elif (event.direction > 0 and event.action < 0) or (event.direction < 0 and event.action > 0):
            # 卖出
            buy_amount = 0.
            sell_amount = event.amount
        else:
            raise ValueError('%s[%s].请输入正确的direction和action值' % (event.dt, event.symbol))
        trade_dict = {
            'datetime': event.dt,
            'symbol': event.symbol,
            'direction': event.direction,
            'action': event.action,
            'quantity': event.quantity,
            'price': event.price,
            'fill_price': event.fill_price,
            'adj_quantity': event.adj_quantity,
            'adj_price': event.adj_price,
            'adj_fill_price': event.adj_fill_price,
            'adj_factor': event.adj_factor,
            'amount': event.amount,
            'buy_amount': buy_amount,
            'sell_amount': sell_amount,
            'fee': event.fee,
            'margin': margin,
            'margin_rate': event.margin_rate,
            'multiplier': event.multiplier,          
            }
        key = (event.symbol, event.direction)
        self.current_trades[key] = trade_dict
        # if key not in self.current_trades.keys():
        #     self.current_trades[key] = []
        # self.current_trades[key].append(trade_dict)
    
    def _update_composite_from_fill(self, event):
        key = (event.symbol, event.direction)
        trade_dict = self.current_trades[key]
        # trade_dict = self.current_trades[key][-1]
        if event.dt != trade_dict['datetime']:
            return None
        
        adj_close = self.vix_data_handler.get_latest_bar_value(event.symbol, 'adj_close')
        if key not in self.current_composites.keys():
            mkt_val_now = adj_close * trade_dict['adj_quantity'] * event.multiplier
            margin_now = mkt_val_now * event.margin_rate
            self.current_composites[key] = {
                'datetime': event.dt,  # 日期
                'symbol': event.symbol,  # 证券代码
                'direction': event.direction,  # 方向
                'holdnum_now': trade_dict['quantity'],  # 现持有数目
                'holdnum_pre': 0.,
                'adj_holdnum_now': trade_dict['adj_quantity'],
                'adj_holdnum_pre': 0.,
                'mkt_val_now': mkt_val_now,
                'mkt_val_pre': 0.,
                'buy_amount': trade_dict['buy_amount'],
                'sell_amount': trade_dict['sell_amount'],
                'fee': trade_dict['fee'],
                'pnl': 0,
                'margin_now': margin_now,
                'margin_pre': 0.,
                'cost': trade_dict['amount'],
                'cost_price': event.fill_price,
                'adj_cost_price': event.adj_fill_price,
                'chg': 0,  # 浮动盈亏(与成本价比)
                'chg_pct': 0,  # 浮盈率(与成本价比)
                'margin_rate': event.margin_rate,  # 保证金率
                'multiplier': event.multiplier  # 乘数
                }
        else:
            self.current_composites[key]['datetime'] = event.dt
            # self.current_composites[key]['holdnum_pre'] = self.current_composites[key]['holdnum_now']
            # self.current_composites[key]['adj_holdnum_pre'] = self.current_composites[key]['adj_holdnum_now']
            # self.current_composites[key]['mkt_val_pre'] = self.current_composites[key]['mkt_val_now']
            
            if event.action > 0:
                self.current_composites[key]['holdnum_now'] += trade_dict['quantity']
                self.current_composites[key]['adj_holdnum_now'] += trade_dict['adj_quantity']
                self.current_composites[key]['cost'] += trade_dict['amount']
                self.current_composites[key]['cost_price'] = (self.current_composites[key]['cost'] / (self.current_composites[key]['holdnum_now'] * event.multiplier))
                self.current_composites[key]['adj_cost_price'] = (self.current_composites[key]['cost'] / (self.current_composites[key]['adj_holdnum_now'] * event.multiplier))
                
            elif event.action < 0:
                self.current_composites[key]['holdnum_now'] -= trade_dict['quantity']
                self.current_composites[key]['adj_holdnum_now'] -= trade_dict['adj_quantity']
                self.current_composites[key]['cost'] = self.current_composites[key]['holdnum_now'] * self.current_composites[key]['cost_price'] * event.multiplier
                # self.current_composites[key]['cost'] -= trade_dict['amount']
            else:
                raise ValueError('%s[%s].请输入正确的action值' % (event.dt, event.symbol))
                
            # self.current_composites[key]['cost_price'] = self.current_composites[key]['cost'] / self.current_composites[key]['holdnum_now'] * event.multiplier
            # self.current_composites[key]['adj_cost_price'] = self.current_composites[key]['cost'] / self.current_composites[key]['adj_holdnum_now'] * event.multiplier 
            self.current_composites[key]['mkt_val_now'] = adj_close * self.current_composites[key]['holdnum_now'] * event.multiplier
            self.current_composites[key]['margin_now'] = self.current_composites[key]['mkt_val_now'] * event.margin_rate
            self.current_composites[key]['buy_amount'] += trade_dict['buy_amount']
            self.current_composites[key]['sell_amount'] += trade_dict['sell_amount']
            self.current_composites[key]['fee'] += trade_dict['fee']
        
        # 当日盈亏 = 卖出金额 – 买入金额 + 市值变动 - 费用
        self.current_composites[key]['pnl'] = (self.current_composites[key]['sell_amount'] - self.current_composites[key]['buy_amount'] + event.direction * (self.current_composites[key]['mkt_val_now'] - self.current_composites[key]['mkt_val_pre']) - self.current_composites[key]['fee'])
            
        if abs(self.current_composites[key]['holdnum_now']) < 1e-4:
            self.current_composites[key]['chg'] = 0
            self.current_composites[key]['chg_pct'] = event.direction * (event.fill_price / self.current_composites[key]['cost_price'] - 1)
        else:
            self.current_composites[key]['chg'] = event.direction * (self.current_composites[key]['mkt_val_now'] - self.current_composites[key]['cost'])
            self.current_composites[key]['chg_pct'] = self.current_composites[key]['chg'] / self.current_composites[key]['cost']
            
    
    def _update_positions_from_fill(self, event):
        current_composites = deepcopy(self.current_composites)
        for key in self.current_composites.keys():
            if current_composites[key]['holdnum_now'] < 1e-4:
                current_composites.pop(key)
        self.current_positions = current_composites
    
    def _update_holdings_from_fill(self, event): 
        total_pnl = 0
        total_mkt_val = 0
        total_margin = 0
        for key in self.current_positions.keys():
            total_mkt_val += self.current_positions[key]['mkt_val_now']
            total_margin += self.current_positions[key]['margin_now']
            total_pnl += self.current_positions[key]['pnl']

        self.current_holdings['mkt_val'] = total_mkt_val
        self.current_holdings['margin'] = total_margin
        self.current_holdings['pnl'] = total_pnl
        self.current_holdings['datetime'] = event.dt    
        self.current_holdings['net_asset'] = self.all_holdings[-1]['net_asset'] + self.current_holdings['pnl']
        self.current_holdings['cash'] = self.current_holdings['net_asset'] - self.current_holdings['margin']
            
    
    def update_after_on_bar(self, event):
        if event.type != 'Bar':
            return None
        if self.flag_first_tradeday:
            self.current_holdings = self._generate_initial_holdings(event.dt)
            self.all_holdings.append(self.current_holdings)
            self.flag_first_tradeday = False
        else:
            self._update_trades_from_bar(event)
            self._update_composite_from_bar(event)
            self._update_positions_from_bar(event)
            self._update_holdings_from_bar(event)
            
    
    def _generate_initial_holdings(self, dt):
        initial_holdings = {
            'datetime': dt,
            'mkt_val': 0.,
            'margin': 0.,
            'pnl': 0.,
            'net_asset': self.initial_cash,
            'cash': self.initial_cash,
            }
        return initial_holdings
        
    
    def _update_trades_from_bar(self, event):
        if len(self.current_trades) > 0:
            self.all_trades.append(deepcopy(self.current_trades))
        self.current_trades = {}
        
    def _update_composite_from_bar(self, event):
        if len(self.current_composites) > 0:
            self.all_composites.append(deepcopy(self.current_composites))
        
        
        if len(self.current_positions) > 0:
            self.current_composites = deepcopy(self.current_positions)
            for key in self.current_composites.keys():
                symbol, direction = key[0], key[1]
                adj_close = self.vix_data_handler.get_latest_bar_value(symbol, 'adj_close')
                self.current_composites[key]['datetime'] = event.dt
                self.current_composites[key]['holdnum_pre'] = self.current_composites[key]['holdnum_now']
                self.current_composites[key]['adj_holdnum_pre'] = self.current_composites[key]['adj_holdnum_now']
                self.current_composites[key]['mkt_val_pre'] = self.current_composites[key]['mkt_val_now']
                self.current_composites[key]['mkt_val_now'] = adj_close * self.current_composites[key]['holdnum_now'] * self.current_composites[key]['multiplier']
                self.current_composites[key]['buy_amount'] = 0
                self.current_composites[key]['sell_amount'] = 0
                self.current_composites[key]['fee'] = 0
                self.current_composites[key]['margin_pre'] = (self.current_composites[key]['margin_now'])
                self.current_composites[key]['margin_now'] = (self.current_composites[key]['mkt_val_now'] * self.current_composites[key]['margin_rate'])
                self.current_composites[key]['pnl'] = (direction * (self.current_composites[key]['mkt_val_now'] - self.current_composites[key]['mkt_val_pre']))
                self.current_composites[key]['chg'] = (direction * (self.current_composites[key]['mkt_val_now'] - self.current_composites[key]['cost']))
                self.current_composites[key]['chg_pct'] = (self.current_composites[key]['chg'] / self.current_composites[key]['cost'])
        else:
            self.current_composites = {}
            
            
    def _update_positions_from_bar(self, event):
        if len(self.current_positions) > 0:
            self.all_positions.append(deepcopy(self.current_positions))
        if len(self.current_composites) > 0:
            self.current_positions = deepcopy(self.current_composites)
        else:
            self.current_positions = {}
            
            
    def _update_holdings_from_bar(self, event):
        if len(self.current_holdings) > 0:
            self.all_holdings.append(deepcopy(self.current_holdings))
        
        if len(self.current_positions) > 0:
            total_pnl = 0
            total_mkt_val = 0
            total_margin = 0
            for key in self.current_positions.keys():
                total_mkt_val += self.current_positions[key]['mkt_val_now']
                total_margin += self.current_positions[key]['margin_now']
                total_pnl += self.current_positions[key]['pnl']
            
            self.current_holdings['mkt_val'] = total_mkt_val
            self.current_holdings['margin'] = total_margin
            self.current_holdings['pnl'] = total_pnl
            
            self.current_holdings['datetime'] = event.dt    
            self.current_holdings['net_asset'] = self.all_holdings[-1]['net_asset'] + self.current_holdings['pnl']
            self.current_holdings['cash'] = self.current_holdings['net_asset'] - self.current_holdings['margin']
        else: 
            self.current_holdings['datetime'] = event.dt 
            self.current_holdings['pnl'] = 0.0
    
    def update_lastday_after_bar(self):
        if len(self.current_trades) > 0:
            self.all_trades.append(deepcopy(self.current_trades))
        self.all_trades_df = self._list2dataframe(self.all_trades)
        
        if len(self.current_composites) > 0:
            self.all_composites.append(deepcopy(self.current_composites))
        self.all_composites_df = self._list2dataframe(self.all_composites)
        
        if len(self.current_positions) > 0:
            self.all_positions.append(deepcopy(self.current_positions))
        self.all_positions_df = self._list2dataframe(self.all_positions)
            
        if len(self.current_holdings) > 0:
            self.all_holdings.append(deepcopy(self.current_holdings))
        self.all_holdings_df = pd.DataFrame(self.all_holdings).sort_values('datetime')
    
    def _list2dataframe(self, data):
        data_list = []
        for sub_data in data:
            for key in sub_data.keys():
                data_list.append(sub_data[key])
        
        df_data = pd.DataFrame(data_list)
        df_data = df_data.sort_values(by=['datetime', 'symbol'])
        return df_data
        
        
    
        
    
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
        