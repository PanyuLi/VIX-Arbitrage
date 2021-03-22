# -*- coding: utf-8 -*-
"""
Created on Sat Feb 20 19:53:57 2021

@author: cherry
"""
import pandas as pd
import numpy as np
from abc import ABCMeta, abstractmethod
import matplotlib.pyplot as plt
import queue
from Event import BarEvent
import warnings

warnings.filterwarnings('ignore')


class DataHandler(object, metaclass=ABCMeta):
    
    @abstractmethod
    def update_bars(self):
        raise NotImplementedError('未实现update_bars()函数！')
    
    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        raise NotImplementedError('未实现get_latest_bars()函数！')
        
        
class VixDataHandler(DataHandler):
    def __init__(self, datapath, start_date, end_date, adj_factor, symbol_list, benchmark_code, event):
        self.datapath = datapath
        self.start_date = start_date
        self.end_date = end_date
        self.adj_factor = adj_factor
        self.symbol_data = {}
        self.symbol_list = symbol_list
        self.lastest_symbol_data = {}
        self.flag_backtest_continue = True
        self.benchmark_code = benchmark_code
        self.positions_df = self.get_history_positions()
        self.event = event
        
    def _load_initial_data(self):
        rename_dict = {'Date': 'datetime'}
        df = pd.read_csv(self.datapath)
        df = df.rename(columns=rename_dict)
        df = df.dropna(axis=[0, 1], how='all')
        df = df.fillna(0)
        df.datetime = df.datetime.apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d')) 
        df = df[(df.datetime >= self.start_date) & (df.datetime <= self.end_date)]
        df = df.set_index('datetime')
        return df
    
    def get_benchmark_data(self):
        df = self._load_initial_data()
        
        df = df[[self.benchmark_code]].rename(columns={self.benchmark_code: 'close'})
        df['return'] = df['close'].pct_change().fillna(0)
        df['net_value'] = (1 + df['return']).cumprod()
        return df
        
        
    def get_history_data(self):
        """
        covert dataframe to dict: 
            {'key1': df1.iterrows(datetime, close, adj_close, adj_factor)}
        """
        df = self._load_initial_data()
        
        for symbol in self.symbol_list:
            df_symbol = df[[symbol]].rename(columns={symbol: 'close'})
            df_symbol['datetime'] = df_symbol.index
            df_symbol['adj_close'] = df_symbol.close
            df_symbol['adj_factor'] = self.adj_factor
            self.symbol_data[symbol] = df_symbol.iterrows()
            self.lastest_symbol_data[symbol] = []
    
    def get_history_positions(self):
        """
        1. 获取每一天所交易的合约
        2. 获取每天每个合约的剩余期限
        3. 获取剩余期限分别为1、2、3个月的合约的持仓

        """
        df = self._load_initial_data()
        
        positions_df = pd.DataFrame(columns=['positions'])
        for dt in df.index:
            contract_series = df.loc[dt, self.symbol_list].dropna()
            due_series = self._get_contract_duration(contract_series, dt)
            
            one_month = due_series[due_series==1].index[0]
            two_month = due_series[due_series==2].index[0]
            three_month = due_series[due_series==3].index[0]
            
            pos = {
                one_month: -df.loc[dt, 'SHORT_1'],
                two_month: df.loc[dt, 'LONG_2'] - df.loc[dt, 'SHORT_2'],
                three_month: df.loc[dt, 'LONG_3'],
                }
            
            positions_df.loc[dt, 'positions'] = [pos]
            
        return positions_df                 
            
            
            
    def _get_contract_duration(self, contract_series, dt):
        month = {
            "F": 1,
            "G": 2,
            "H": 3,
            "J": 4,
            "K": 5,
            "M": 6,
            "N": 7,
            "Q": 8,
            "U": 9,
            "V": 10,
            "X": 11,
            "Z": 12,
        }
        duration_dict = {}
        for con in contract_series.index:
            # print(con[-2:], dt[2:4], month[con[2]])
            if len(con) == 5:
                duration_dict[con] = (int(con[-2:]) - int(dt[2:4])) * 12 + month[con[2]] - int(dt[5: 7])
            if len(con) == 4:
                duration_dict[con] = (int(con[-1]) + 20 - int(dt[2:4])) * 12 + month[con[2]] - int(dt[5: 7])
        duration_series = pd.Series(duration_dict)
        return duration_series
                
        
            
    def _get_new_bar(self, symbol):
        index, row = next(self.symbol_data[symbol])
        bar = row.to_dict()
   
        return bar
            
    def update_bars(self):
        for symbol in self.symbol_list:
            try:
                new_bar = self._get_new_bar(symbol)
                new_bar['symbol'] = symbol
            except StopIteration:
                self.flag_backtest_continue = False
            else: 
                if new_bar is not None:
                    self.lastest_symbol_data[symbol].append(new_bar)
        if self.flag_backtest_continue:
            # print('new_bar_time: ', new_bar['datetime'])
            self.event.put(BarEvent(new_bar['datetime']))
            
    
    def get_latest_bars(self, symbol, N=1):
        if not isinstance(N, int):
            raise ValueError('请输入整数N！')
        else:
            try:
                bar_list = self.lastest_symbol_data[symbol]
            except KeyError:
                print('不存在%s的bar数据' % symbol)
            else:
                if N == -1:
                    return bar_list
                elif N > 0:
                    if N == 1:
                        return bar_list[-N] 
                    else:
                        return bar_list[-N:]
                else:
                    return None
    
    def get_latest_bar_value(self, symbol, field='close'):
        latest_bar = self.get_latest_bars(symbol)
        value = np.nan
        if latest_bar is not None:
            value = latest_bar.get(field, np.nan)
        return value
    
    
        
            
if __name__ == '__main__':
    start_date = '2007-01-03'
    end_date = '2020-09-30'
    datapath = "VIX_output.csv"
    adj_factor = 1
    event = queue.Queue()
    
    df = pd.read_csv(datapath)
    symbol_list = [x for x in df.columns if x[:2] == 'UX']
    
    vix_Data = VixDataHandler(datapath, start_date, end_date, adj_factor, 
                              symbol_list, 'SPX500', event)
    
    vix_Data.get_history_data()
    for i in range(15):
        vix_Data.update_bars()
        print(event.get().dt)
    vix_Data.get_latest_bars('UXF07')
    bmk_df = vix_Data.get_benchmark_data()
    
    positions_df = vix_Data.get_history_positions()
    








