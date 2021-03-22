# -*- coding: utf-8 -*-
"""
Created on Sun Feb 21 18:13:07 2021

@author: cherry
"""
import pandas as pd
import queue
from DataProcessing import VixDataHandler
from Strategy import VixStrategy
import warnings
from Performance import BktPerformance
from Common import OrderCost

warnings.filterwarnings('ignore')


if __name__ == '__main__':
    start_date = '2007-01-04'
    end_date = '2020-09-30'
    datapath = "VIX_output.csv"
    adj_factor = 1
    event = queue.Queue()
    order_cost = OrderCost()
    
    df = pd.read_csv(datapath)
    symbol_list = [x for x in df.columns if x[:2] == 'UX']
    
    vix_data_handler = VixDataHandler(datapath, start_date, end_date, adj_factor, 
                              symbol_list, 'SPX500', event)
    vix_strategy = VixStrategy(vix_data_handler, event, order_cost, start_date)
    
    vix_data_handler.get_history_data()
    vix_data_handler.get_history_positions()

    while True:
        if vix_data_handler.flag_backtest_continue:
            vix_data_handler.update_bars()
        else:
            vix_strategy.update_lastday_after_bar()
            print('>>> 回测结束！\n')
            break
        
        while True:
            try:
                e = event.get(block=False)
            except queue.Empty:
                break
            else:
                if e.type == 'Bar':
                    vix_strategy.on_bar(e)
                    vix_strategy.update_after_on_bar(e)
                if e.type == 'Signal':
                    # print(e)
                    vix_strategy.on_signal(e)
                if e.type == 'Order':
                    # print(e)
                    vix_strategy.on_order(e)
                if e.type == 'Fill':   
                    print(e)
                    vix_strategy.on_fill(e)
    
    portfolio = vix_strategy.all_holdings_df
    benchmark = vix_data_handler.get_benchmark_data()
    bkt_perform = BktPerformance(portfolio, benchmark)
    bkt_perform.cal_params()
    bkt_perform.plot_strategy_curves()
        

