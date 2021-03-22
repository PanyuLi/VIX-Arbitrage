# -*- coding: utf-8 -*-
"""
Created on Tue Feb 23 15:53:15 2021

@author: cherry
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('bmh')

class BktPerformance(object):
    def __init__(self, portfolio, benchmark=None, rf=0.0, num_tradedays=250):
        self.portfolio = portfolio
        self.benchmark = benchmark
        self.rf = rf
        self.num_tradedays = num_tradedays
    
    def _cal_annual_return(self, net_value_series, num_tradedays=250):
        annual_return = pow(net_value_series.iloc[-1] / net_value_series.iloc[0], num_tradedays/len(net_value_series)) - 1
        return annual_return
    
    def _cal_cum_return(self, net_value_series):
        cum_return = net_value_series.iloc[-1] / net_value_series.iloc[0] - 1
        return cum_return
    
    def _cal_annual_std(self, return_series, num_tradedays=250):
        annual_std = return_series.std() * np.sqrt(num_tradedays)
        return annual_std
    
    def _cal_sharpe_ratio(self, annual_return, annual_std, rf):
        sharpe_ratio = (annual_return - rf) / annual_std
        return sharpe_ratio
    
    def _cal_max_drawdown(self, net_value_series):
        drawdown = net_value_series / net_value_series.cummax() - 1
        max_drawdown = drawdown.min()
        return max_drawdown
    
    def _cal_alpha(self, index_a_return, bmk_a_return):
        alpha = index_a_return - bmk_a_return
        return alpha
    
    def _cal_beta(self, index_series, bmk_series):
        cov = np.cov(index_series, bmk_series)[0, 1]
        beta = cov / bmk_series.var()
        return beta
    
    def _cal_mar(self, annual_return, max_drawdown):
        mar = annual_return / abs(max_drawdown)
        return mar
    
    def _cal_win_rate(self, return_series):
        win_days = return_series.apply(lambda x: np.nan if x > 0 else 0).count()
        win_rate = win_days / len(return_series)
        return win_rate
        
        
    def cal_params(self):
        self.portfolio = self.portfolio.reset_index().set_index('datetime').sort_index()
        self.portfolio['net_value'] = self.portfolio['net_asset'] / self.portfolio['net_asset'].iloc[0]
        self.portfolio['return'] = self.portfolio['net_value'].pct_change().fillna(0)
        start_date = self.portfolio.index[0]
        end_date = self.portfolio.index[-1]

        portfolio_params = {} 
        portfolio_params['annual_return'] = self._cal_annual_return(self.portfolio['net_value'], self.num_tradedays)
        portfolio_params['cum_return'] = self._cal_cum_return(self.portfolio['net_value'])
        portfolio_params['annual_std'] = self._cal_annual_std(self.portfolio['return'], self.num_tradedays)
        portfolio_params['sharpe_ratio'] = self._cal_sharpe_ratio(portfolio_params['annual_return'], 
                                                                  portfolio_params['annual_std'], self.rf)  
        portfolio_params['max_drawdown'] = self._cal_max_drawdown(self.portfolio['net_value']) 
        portfolio_params['mar'] = self._cal_mar(portfolio_params['annual_return'],
                                                         portfolio_params['max_drawdown']) 
        portfolio_params['win_rate'] = self._cal_win_rate(self.portfolio['return']) 
        
        if self.benchmark is not None:
            df = pd.merge(self.portfolio[['net_value']], self.benchmark['net_value'],
                          how='inner', left_index=True, right_index=True, suffixes=('_stra', '_bmk'))
            bmk_params = {}
            bmk_params['annual_return'] = self._cal_annual_return(self.benchmark['net_value'], self.num_tradedays)
            bmk_params['cum_return'] = self._cal_cum_return(self.benchmark['net_value'])
            bmk_params['annual_std'] = self._cal_annual_std(self.benchmark['return'], self.num_tradedays)
            bmk_params['sharpe_ratio'] = self._cal_sharpe_ratio(bmk_params['annual_return'], 
                                                                bmk_params['annual_std'], self.rf)  
            bmk_params['max_drawdown'] = self._cal_max_drawdown(self.benchmark['net_value']) 
            
            portfolio_params['alpha'] = self._cal_alpha(portfolio_params['annual_return'], bmk_params['annual_return'])
            portfolio_params['beta'] = self._cal_beta(df['net_value_stra'], df['net_value_bmk'])
            
            print('*' * 31)
            print("回测时间从{}到{}".format(start_date, end_date))
            print('累计收益：%.2f%%' % (portfolio_params['cum_return'] * 100))
            print('年化收益：%.2f%%' % (portfolio_params['annual_return'] * 100))
            print('基准收益：%.2f%%' % (bmk_params['cum_return'] * 100))
            print('基准年化：%.2f%%' % (bmk_params['annual_return'] * 100))
            print('超额收益：%.2f%%' % (portfolio_params['alpha'] * 100))
            print('Beta系数：%.2f' % (portfolio_params['beta']))
            print('年化波动：%.2f%%' % (portfolio_params['annual_std'] * 100))
            print('夏普比率：%.2f' % portfolio_params['sharpe_ratio'])
            print('基准夏普：%.2f' % bmk_params['sharpe_ratio'])
            print('最大回撤：%.2f%%' % (abs(portfolio_params['max_drawdown']) * 100))
            print('基准回撤：%.2f%%' % (abs(bmk_params['max_drawdown']) * 100))
            print('MAR比率：%.2f' % portfolio_params['mar'])
            print('日胜率：%.2f%%' % (portfolio_params['win_rate'] * 100))
            print('*' * 31)
        else:
            print('*' * 31)
            print("回测时间从{}到{}".format(start_date, end_date))
            print('累计收益：%.2f%%' % (portfolio_params['cum_return'] * 100))
            print('年化收益：%.2f%%' % (portfolio_params['annual_return'] * 100))
            print('年化波动：%.2f%%' % (portfolio_params['annual_std'] * 100))
            print('夏普比率：%.2f' % portfolio_params['sharpe_ratio'])
            print('最大回撤：%.2f%%' % (abs(portfolio_params['max_drawdown']) * 100))
            print('MAR比率：%.2f' % portfolio_params['mar'])
            print('日胜率：%.2f%%' % (portfolio_params['win_rate'] * 100))
            print('*' * 31)
        
        return portfolio_params
    
    def plot_strategy_curves(self, show=True):
        self.portfolio = self.portfolio.reset_index().set_index('datetime').sort_index()
        start_date = self.portfolio.index[0]
        end_date = self.portfolio.index[-1]
        
        self.portfolio['drawdown'] = self.portfolio['net_value'] / self.portfolio['net_value'].cummax() - 1
        
        if self.benchmark is not None:
            self.benchmark['drawdown'] = self.benchmark['net_value'] / self.benchmark['net_value'].cummax() - 1
            
            df = pd.merge(self.portfolio[['net_value', 'drawdown']], 
                                  self.benchmark[['net_value', 'drawdown']], 
                                  how='inner', left_index=True, right_index=True, suffixes=('_stra', '_bmk'))
        else:
            df = self.portfolio[['net_value', 'drawdown']].rename(columns={'net_value': 'net_value_stra',
                                                                                   'drawdown': 'drawdown_stra'})
        
        df.index = pd.to_datetime(df.index)
        
        fig, axis = plt.subplots(2, 1, sharex=True)
        fig.set_size_inches(15, 8)
        ax1 = axis[0]
        ax2 = axis[1]
        
        if self.benchmark is not None: 
            p1, = ax1.plot(df.index, df['net_value_stra'], color='r', linewidth=2, alpha=0.8)
            p2, = ax1.plot(df.index, df['net_value_bmk'], color='steelblue', linewidth=2)
          
            title1 = 'Cumulative Return from %s to %s' % (start_date, end_date)
            ax1.set_title(title1)
            ax1.legend([p1, p2], ['strategy', 'benchmark'])
            ax1.grid(True)
            ax1.set_xlim(df.index[0], df.index[-1])
        
            f1 = ax2.fill_between(df.index, df['drawdown_stra'], 0, facecolor='r', alpha=0.3)
            f2 = ax2.fill_between(df.index, df['drawdown_bmk'], 0, facecolor='steelblue', alpha=0.3)
            title2 = 'Drawdown from %s to %s' % (start_date, end_date)
            ax2.legend([f1, f2], ['strategy', 'benchmark'], loc=3)
            ax2.set_title(title2)
            ax2.grid(True)
            ax2.set_xlim(df.index[0], df.index[-1])
        else:
            p1, = ax1.plot(df.index, df['net_value_stra'], color='r', linewidth=2, alpha=0.8)
          
            title1 = 'Cumulative Return from %s to %s' % (start_date, end_date)
            ax1.set_title(title1)
            ax1.legend([p1], ['strategy'])
            ax1.grid(True)
            ax1.set_xlim(df.index[0], df.index[-1])
        
            f1 = ax2.fill_between(df.index, df['drawdown_stra'], 0, facecolor='r', alpha=0.3)
            title2 = 'Drawdown from %s to %s' % (start_date, end_date)
            ax2.legend([f1], ['strategy'], loc=3)
            ax2.set_title(title2)
            ax2.grid(True)
            ax2.set_xlim(df.index[0], df.index[-1])
            
        if show == True:
            plt.show()
                
        
            
            
            
            
        
            
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        

