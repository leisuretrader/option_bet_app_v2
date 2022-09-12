import streamlit as st
import pandas as pd
import numpy as np
import os
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
pd.options.mode.chained_assignment = None  # default='warn'

def bet_logic():
    """
    Sidebar filter input:
    """
    ticker = st.sidebar.text_input("Ticker: ", value='spy')
    period = st.sidebar.text_input("Period: ", value='2y')
    interval = st.sidebar.text_input("Interval: ", value='1d')

    if_use_open_price = st.sidebar.selectbox(label = "If Use Open Price (otherwise use current price)", options = [True,False])  #otherwise use current market price
    if_adjust_close = st.sidebar.selectbox(label = "If Adjust Close for Historical Data", options = [True,False]) 

    # For prod:
    chose_expiry_date = st.sidebar.date_input("Choose Expiry Date", date(2022, 9, 16)) #'2022-09-16'
    chose_expiry_date = chose_expiry_date.strftime("%Y-%m-%d")
    

    if_incl_cur_day = st.sidebar.selectbox(label = "If Include Current Date when deteremine days to expiry", options = [True,False]) # if use current day Open, better to include the current day in historical horizon.
    override_pct_change_horizon = st.sidebar.text_input("If Override Pct Change Horizon (If not False, put a number): ", value='False') # if not False, put a number
    # if override_pct_change_horizon == 'False':
    #     override_pct_change_horizon = bool(override_pct_change_horizon)
    # For backtest: 
    percentile = 10
    select_percentile = str(percentile) + "%"  #['10%','15%','20%','25%','50%','75%','80%','85%','90%']
    pct_change_horizon = 5 #for each historical data point calculation, if use Monday Close, we can change it to 4

    if_print_detail = False #st.sidebar.selectbox(label = "If Print Backtest Result (Default False): ", options = [False, True])


    def nearest_value(input_list, find_value):
        difference = lambda input_list : abs(input_list - find_value)
        res = min(input_list, key=difference)
        return res

    def weekdays_calculator(end_str):
        today = datetime.today().date()
        end = datetime.strptime(end_str, '%Y-%m-%d').date()
        return np.busday_count(today, end)

    # print (chose_expiry_date)
    # print (weekdays_calculator(chose_expiry_date))

    def split_list(input_list, n):  #this will return generater, add list() to output as list
        for i in range(0, len(input_list), n): 
            yield input_list[i:i + n] 
            
    def yf_info(ticker):
        return yf.Ticker(ticker)

    def current_price(ticker):  #can use current price or open price
        if if_use_open_price == True:
            return yf_info(ticker).info['open']
        else: #use current market price
            return yf_info(ticker).info['regularMarketPrice']

    def historical_data(ticker): # need to define format
        hist_price = yf.download(ticker, 
                            period=period,
                            interval=interval,
                            auto_adjust=if_adjust_close)[['Open','Close']]
        
        return hist_price

    def perc_change(df, ticker, horizon):
        # print ('-----------',horizon)
        horizon = horizon-1
        df['return_perc'] = df.pct_change(periods=horizon,fill_method='ffill').round(decimals=4)['Close']
        return df.dropna()

    def latest_perc_change(ticker,horizon, past_days):
        historical = perc_change(historical_data(ticker),ticker,horizon)
        r = historical.return_perc.values.tolist()
        return r[-past_days:]

    def describe_perc_change(df, select_price):
    #     cur_price = current_price(ticker)
    #     perc_change(ticker,horizon)
        describe = df.describe(percentiles = [.001,.01,.05,.1,.15,.25,.5,.75,.85,.90,.95,.99,.999])
        
        describe['Close'] = select_price
        describe['price'] = select_price * (1+describe['return_perc'])
        describe['return_perc'] = describe['return_perc'] * 100
        describe['price_int'] = describe['price'].astype(int)
        return describe

    def option_expiry_dates(ticker):
        return yf_info(ticker).options  #return expiry dates

    def option_chain(ticker, expiry_date, call_or_put=None, in_or_out=None):
        result = yf_info(ticker).option_chain(expiry_date)
        if call_or_put is None:
            call = result.calls
            put = result.puts
            result = call.append(put, ignore_index=True)
        elif call_or_put not in ['call','put']:
            return 'please input call or put'
        else:
            result = result.calls if call_or_put=='call' else result.puts if call_or_put=='put' else result
            
        result = result.loc[result['inTheMoney'] == True] if in_or_out == 'in' else result.loc[result['inTheMoney'] == False] if in_or_out == 'out' else result
        return result
        
    def perc_change_with_option(ticker, horizon, expiry_date, call_or_put=None, in_or_out=None):
        perc_change_data = describe_perc_change(df = perc_change(historical_data(ticker),ticker,horizon),
                                                select_price = current_price(ticker))
        
        price_int_l = perc_change_data['price_int'].values.tolist()
        opt_data = option_chain(ticker, expiry_date, call_or_put, in_or_out)
        all_strikes = opt_data.strike.tolist()
        
        chose_strike = []
        last_price = []
        for i in price_int_l:
            if i in all_strikes:
                lp = opt_data.loc[opt_data['strike']==i].lastPrice.values
                chose_strike.append(int(i))
                last_price.append(lp)
            else:
                nearest_strike = nearest_value(all_strikes, i)
                lp = opt_data.loc[opt_data['strike']==nearest_strike].lastPrice.values
                chose_strike.append(int(nearest_strike))
                last_price.append(lp)
        last_price = [i[0] for i in last_price]
        
        perc_change_data['chose_strike'] = chose_strike
        perc_change_data['last_price'] = last_price
        
        perc_change_data.loc['count','return_perc'] = perc_change_data.loc['count','return_perc']/100
        
        perc_change_data.loc['count','price'] = 0
        perc_change_data.loc['count','price_int'] = 0
        perc_change_data.loc['count','chose_strike'] = 0
        perc_change_data.loc['count','last_price'] = 0
        
        perc_change_data.loc['std','price'] = 0
        perc_change_data.loc['std','price_int'] = 0
        perc_change_data.loc['std','chose_strike'] = 0
        perc_change_data.loc['std','last_price'] = 0
        
        perc_change_data.loc['mean','price'] = 0
        perc_change_data.loc['mean','price_int'] = 0
        perc_change_data.loc['mean','chose_strike'] = 0
        perc_change_data.loc['mean','last_price'] = 0
        
        perc_change_data = perc_change_data.drop(['Open'], axis=1)
        return perc_change_data
        
    def plot_histogram(ticker, horizon, latest_horizon):
        # print ('---------------', horizon)
        fig = go.Figure()
        historical = perc_change(historical_data(ticker),ticker,horizon)
        all_perc_change_l = historical.return_perc.values.tolist()  
        latest_perc_change_l = all_perc_change_l[-latest_horizon:]
        cur_per_change = all_perc_change_l[-1:]
        fig.add_trace(go.Histogram(x=all_perc_change_l,
                                        name = 'all records',
                                        marker_color='#330C73',
                                        opacity=0.75,
                                        ))
        
        fig.add_trace(go.Histogram(x=latest_perc_change_l,
                                        name = 'latest {} trading days'.format(latest_horizon),
                                        marker_color='#EB89B5',
                                        opacity=0.9,
                                        ))
        
        fig.add_trace(go.Histogram(x=cur_per_change,
                                    name = 'current',
                                    marker_color='#FF0000',
                                    opacity=1,
                                    ))

        fig.update_layout(
            barmode='overlay',
            title_text='% Change Distribution Count - ({} days)'.format(horizon), # title of plot
            xaxis_title_text='% Change', # xaxis label
            yaxis_title_text='Count', # yaxis label
        )
        return fig #.show()

    # days_to_expiry = weekdays_calculator(chose_expiry_date)
    if override_pct_change_horizon == 'False':
        if if_incl_cur_day == True:
            days_to_expiry = weekdays_calculator(chose_expiry_date) + 1
        elif if_incl_cur_day == False:
            days_to_expiry = weekdays_calculator(chose_expiry_date)
        else:
            raise
    else:
        days_to_expiry = override_pct_change_horizon

        
    ############################################# Backtesting section
    def backtest_data(ticker):
        data = historical_data(ticker)
        data['future_fri'] = data.Close.shift(-4)
        return data

    def backtest_mondays_list(df, ticker):
    #     data = backtest_data(ticker)
        mondays = df[df.index.weekday==0] #all Mondays
        monday_list = mondays.index.to_list()
        return monday_list

    failed_delta = []
    def backtest(percentile, latest):
        backtest_df = backtest_data(ticker)
        monday_list = backtest_mondays_list(backtest_df, ticker)

        if latest == 'all':
            list_len = len(monday_list)-1
        else:
            list_len = latest
            
        result = []

        for i in monday_list[-list_len:]:
            data = backtest_df.loc[:i]
            open_price = data.tail(1).values[0][0]
            close_price = data.tail(1).values[0][1]
            
            def select_price(): # if if_use_open_price == 'yes' then use 'open price to calculate instead of current price
                if if_use_open_price == True:
                    return open_price
                else:
                    return close_price

            cur_price = select_price()
            perc_change_data = perc_change(df = data, ticker = ticker, horizon = pct_change_horizon)

            describe_result = describe_perc_change(df = perc_change_data,
                                                select_price=cur_price).drop(columns=['future_fri'])
            describe_result['fri'] = data.loc[i]['future_fri']
            selected_percentile_df = describe_result.loc[percentile]
            chose_strike = selected_percentile_df['price_int']
            selected_percentile_fri = selected_percentile_df['fri']
            
            def print_text(if_good):
                if if_print_detail == True:
                    print (i)
                    print ('Monday_price: ',round(cur_price,2))
                    print ('Selected_Strike:', chose_strike)
                    print('Friday_Close: ', round(selected_percentile_fri,2),if_good)
                    print ('----------------------------------')
                else:
                    pass

            if percentile in ['5%','10%','15%','20%','25%','50%']: # for short put
                if selected_percentile_fri > chose_strike:
                    print_text('Good')
                    result.append('good')
                elif selected_percentile_fri < chose_strike:
                    print_text('Fail')
                    failed_delta.append(selected_percentile_fri-chose_strike)
                    result.append('fail')

            elif percentile in ['75%','80%','85%','90%','95%']:  #for short call
                if selected_percentile_fri > chose_strike:
                    print_text('Fail')
                    result.append('fail')
                elif selected_percentile_fri < chose_strike:
                    print_text('Good')
                    failed_delta.append(selected_percentile_fri-chose_strike)
                    result.append('good')
            else:
                raise

        print (result)
        print ('length:', len(result))
        print ('Failed: ', result.count('fail'))
        print ('GOOD: ', result.count('good'))
        print ('Success Rate: ', result.count('good')/(result.count('fail')+result.count('good')))
    
    # print ('#################', ticker, days_to_expiry, chose_expiry_date)

    bet_result_df = perc_change_with_option(ticker, days_to_expiry, chose_expiry_date, call_or_put=None, in_or_out='out')
    result_plot =  plot_histogram(ticker, days_to_expiry, 50)

    col1, col2 = st.columns(2)
    try:
        with col1:
            st.dataframe(bet_result_df, width=1000, height=685)
        with col2:
            st.plotly_chart(result_plot)
    except:
        st.write('No data showing')

    # print ('---------------- Below is Backtest Section-------------')
    # print ('\n')

    # print (backtest(select_percentile, 'all'))  # remember, if the percentile is below 50%, success rate is correct. If chose percentail above 50%, use 1-success rate to get the correct success rate
    # print ('Failed Deltas: ', failed_delta,
    #     "\n",
    #     "Max Delta : ", max(failed_delta), 
    #     "\n",
    #     "Min Delta : ", min(failed_delta))