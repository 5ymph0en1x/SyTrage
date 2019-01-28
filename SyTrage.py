# Configuration
# pip3 install oandapyV20
# pip3 install pyTelegramBotAPI
# Execution
# python SyTrage.py

import json
from datetime import *
from dateutil import parser
import multiprocessing as mp
import oandapyV20
from oandapyV20 import API
from oandapyV20.contrib.requests import MarketOrderRequest
from oandapyV20.contrib.requests import TakeProfitDetails, StopLossDetails
from oandapyV20.contrib.requests import TrailingStopLossOrderRequest
from oandapyV20.endpoints.pricing import PricingInfo
from oandapyV20.endpoints.pricing import PricingStream
from oandapyV20.exceptions import V20Error
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders
import telebot

# Bot Parameters
sigma = 0.00060
sl_tp_prc = 0.005
trail_point = 10
spread_limit = 3.5
Multi_Threading = True
Tgr_Verbose = True

# OANDA Config
accountID = "<Account ID>"
access_token = "<Account Token>"

# Telegram Config
TOKEN = "<Telegram Token>"
chatid = "<Chat ID>"
tb = telebot.TeleBot(TOKEN)

# Do Not Touch
pairs_traded = 'EUR_USD,GBP_USD,EUR_GBP,EUR_JPY,USD_JPY,GBP_JPY'

api = API(access_token=access_token, environment="practice")

stream = PricingStream(accountID=accountID, params={"instruments": pairs_traded})
orders_list = orders.OrderList(accountID)

CEU = instruments.InstrumentsCandles(instrument='EUR_USD', params={"count": 1, "granularity": "M1"})
CGU = instruments.InstrumentsCandles(instrument='GBP_USD', params={"count": 1, "granularity": "M1"})
CEG = instruments.InstrumentsCandles(instrument='EUR_GBP', params={"count": 1, "granularity": "M1"})
CEJ = instruments.InstrumentsCandles(instrument='EUR_JPY', params={"count": 1, "granularity": "M1"})
CUJ = instruments.InstrumentsCandles(instrument='USD_JPY', params={"count": 1, "granularity": "M1"})
CGJ = instruments.InstrumentsCandles(instrument='GBP_JPY', params={"count": 1, "granularity": "M1"})


def spreadcheck(pairs_checked):

    for i in pairs_checked:
        info = PricingInfo(accountID=accountID, params={"instruments": i})
        value = api.request(info)
        bid = float(value['prices'][0]['bids'][0]['price'])
        ask = float(value['prices'][0]['asks'][0]['price'])
        decim = str(bid)[::-1].find('.')
        spread = (ask - bid) * (10 ** (decim - 1))
        if spread > spread_limit:
            print("Spread Limit Exceeded !")
            return False

    return True


def orderlaunch(args):

    pair_targeted, direction = args

    info = PricingInfo(accountID=accountID, params={"instruments": pair_targeted})
    mkt_order = None

    if direction is 0:
        return False

    elif direction is 1:
        raw_current_price = api.request(info)
        bid_current = float(raw_current_price['prices'][0]['bids'][0]['price'])
        decim = str(bid_current)[::-1].find('.')
        stop_loss = round(bid_current - bid_current * sl_tp_prc, decim)
        take_profit = round(bid_current + bid_current * sl_tp_prc, decim)

        mkt_order = MarketOrderRequest(
            instrument=pair_targeted,
            units=1000,
            takeProfitOnFill=TakeProfitDetails(price=take_profit).data,
            stopLossOnFill=StopLossDetails(price=stop_loss).data)

    elif direction is -1:
        raw_current_price = api.request(info)
        ask_current = float(raw_current_price['prices'][0]['asks'][0]['price'])
        decim = str(ask_current)[::-1].find('.')
        stop_loss = round(ask_current + ask_current * sl_tp_prc, decim)
        take_profit = round(ask_current - ask_current * sl_tp_prc, decim)

        mkt_order = MarketOrderRequest(
            instrument=pair_targeted,
            units=-1000,
            takeProfitOnFill=TakeProfitDetails(price=take_profit).data,
            stopLossOnFill=StopLossDetails(price=stop_loss).data)

    # create the OrderCreate request
    r = orders.OrderCreate(accountID, data=mkt_order.data)

    try:
        # create the OrderCreate request
        rv = api.request(r)
    except oandapyV20.exceptions.V20Error as err:
        print(r.status_code, err)
        return False
    else:
        print(json.dumps(rv, indent=2))
        try:
            trade_id = rv['tradeOpenedID']
            ordr = TrailingStopLossOrderRequest(tradeID=trade_id, distance=trail_point)
            r = orders.OrderCreate(accountID, data=ordr.data)
            rv = api.request(r)
        except oandapyV20.exceptions.V20Error as err:
            print(r.status_code, err)
            return False
        else:
            print(json.dumps(rv, indent=2))
            return True


def main():

    diff_EU = 0
    diff_UE = 0
    diff_GU = 0
    diff_UG = 0
    diff_EG = 0
    diff_GE = 0
    diff_EJ = 0
    diff_JE = 0
    diff_UJ = 0
    diff_JU = 0
    diff_GJ = 0
    diff_JG = 0

    close_EU = 0
    close_GU = 0
    close_EG = 0
    close_EJ = 0
    close_UJ = 0
    close_GJ = 0

    minute_cached = 0
    in_action = False

    listing = api.request(orders_list)
    if len(listing['orders']) is not 0 and in_action is False:
        in_action = True

    try:
        R = api.request(stream)

        for i in R:

            EUR = 0
            GBP = 0
            USD = 0
            JPY = 0

            if minute_cached is not datetime.now().time().minute:
                listing = api.request(orders_list)
                if in_action is True and len(listing['orders']) is 0:
                    if Tgr_Verbose is True:
                        report = accounts.AccountSummary(accountID)
                        api.request(report)
                        account_details = report.response
                        balance = str(round(float(account_details['account']['balance']), 2)) + ' ' + \
                                  account_details['account']['currency']
                        txt_msg = "Positions Closed...\nBalance: " + balance
                        tb.send_message(chatid, txt_msg)
                    in_action = False
                candle_EU = api.request(CEU)
                candle_GU = api.request(CGU)
                candle_EG = api.request(CEG)
                candle_EJ = api.request(CEJ)
                candle_UJ = api.request(CUJ)
                candle_GJ = api.request(CGJ)
                actual_minute = datetime.now().time().minute
                candle_EU_minute = parser.parse(candle_EU['candles'][0]['time']).minute
                candle_GU_minute = parser.parse(candle_GU['candles'][0]['time']).minute
                candle_EG_minute = parser.parse(candle_EG['candles'][0]['time']).minute
                candle_EJ_minute = parser.parse(candle_EJ['candles'][0]['time']).minute
                candle_UJ_minute = parser.parse(candle_UJ['candles'][0]['time']).minute
                candle_GJ_minute = parser.parse(candle_GJ['candles'][0]['time']).minute
                if candle_EU['candles'][0]['complete'] is False and candle_EU_minute == actual_minute:
                    close_EU = candle_EU['candles'][0]['mid']['o']
                if candle_GU['candles'][0]['complete'] is False and candle_GU_minute == actual_minute:
                    close_GU = candle_GU['candles'][0]['mid']['o']
                if candle_EG['candles'][0]['complete'] is False and candle_EG_minute == actual_minute:
                    close_EG = candle_EG['candles'][0]['mid']['o']
                if candle_EJ['candles'][0]['complete'] is False and candle_EJ_minute == actual_minute:
                    close_EJ = candle_EJ['candles'][0]['mid']['o']
                if candle_UJ['candles'][0]['complete'] is False and candle_UJ_minute == actual_minute:
                    close_UJ = candle_UJ['candles'][0]['mid']['o']
                if candle_GJ['candles'][0]['complete'] is False and candle_GJ_minute == actual_minute:
                    close_GJ = candle_GJ['candles'][0]['mid']['o']
                if (float(close_EU) == 0 or float(close_EG) == 0 or float(close_EJ) == 0
                        or float(close_GJ) == 0 or float(close_GU) == 0 or float(close_UJ) == 0):
                    print("Warming Up...")
                    continue
                if(candle_EU_minute == actual_minute and candle_GU_minute == actual_minute
                        and candle_EG_minute == actual_minute and candle_EJ_minute == actual_minute
                        and candle_UJ_minute == actual_minute and candle_GJ_minute == actual_minute):
                    minute_cached = datetime.now().time().minute
                    print("Minute Data Updated")

            if i['type'] == 'PRICE':
                pair = i['instrument']
                value = i['bids']
                price = value[0]['price']
                if pair == 'EUR_USD':
                    diff_EU = (float(price) - float(close_EU)) / float(close_EU)
                    diff_UE = diff_EU * -1
                if pair == 'GBP_USD':
                    diff_GU = (float(price) - float(close_GU)) / float(close_GU)
                    diff_UG = diff_GU * -1
                if pair == 'EUR_GBP':
                    diff_EG = (float(price) - float(close_EG)) / float(close_EG)
                    diff_GE = diff_EG * -1
                if pair == 'EUR_JPY':
                    diff_EJ = (float(price) - float(close_EJ)) / float(close_EJ)
                    diff_JE = diff_EJ * -1
                if pair == 'USD_JPY':
                    diff_UJ = (float(price) - float(close_UJ)) / float(close_UJ)
                    diff_JU = diff_UJ * -1
                if pair == 'GBP_JPY':
                    diff_GJ = (float(price) - float(close_GJ)) / float(close_GJ)
                    diff_JG = diff_GJ * -1

            var_EU = 2 * diff_EU + diff_EG + diff_EJ
            var_EG = 2 * diff_EG + diff_EU + diff_EJ
            var_EJ = 2 * diff_EJ + diff_EU + diff_EG
            var_E = (var_EU + var_EG + var_EJ) / 3

            if var_E > sigma:
                EUR = 1
                print('EUR: UP')
            if var_E < -sigma:
                EUR = -1
                print('EUR: DOWN')

            var_GE = 2 * diff_GE + diff_GU + diff_GJ
            var_GU = 2 * diff_GU + diff_GE + diff_GJ
            var_GJ = 2 * diff_GJ + diff_GU + diff_GE
            var_G = (var_GE + var_GU + var_GJ) / 3

            if var_G > sigma:
                GBP = 1
                print('GBP: UP')
            if var_G < -sigma:
                GBP = -1
                print('GBP: DOWN')

            var_UE = 2 * diff_UE + diff_UG + diff_UJ
            var_UG = 2 * diff_UG + diff_UE + diff_UJ
            var_UJ = 2 * diff_UJ + diff_UG + diff_UE
            var_U = (var_UE + var_UG + var_UJ) / 3

            if var_U > sigma:
                USD = 1
                print('USD: UP')
            if var_U < -sigma:
                USD = -1
                print('USD: DOWN')

            var_JE = 2 * diff_JE + diff_JG + diff_JU
            var_JG = 2 * diff_JG + diff_JE + diff_JU
            var_JU = 2 * diff_JU + diff_JG + diff_JE
            var_J = (var_JE + var_JG + var_JU) / 3

            if var_J > sigma:
                JPY = 1
                print('JPY: UP')
            if var_J < -sigma:
                JPY = -1
                print('JPY: DOWN')

            if EUR == -1 and GBP == 1 and USD == -1 and JPY == -1:
                if spreadcheck({'EUR_GBP', 'GBP_USD', 'GBP_JPY'}) is True:
                    listing = api.request(orders_list)
                    if len(listing['orders']) is 0 and Multi_Threading is True:
                        p = mp.Pool(3)
                        data = (['EUR_GBP', 1], ['GBP_USD', -1], ['GBP_JPY', -1])
                        threads = p.map_async(orderlaunch, data)
                        threads.get()
                        p.close()
                        p.join()
                        p.terminate()
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened via MT..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                    elif len(listing['orders']) is 0:
                        orderlaunch(['EUR_GBP', 1])
                        orderlaunch(['GBP_USD', -1])
                        orderlaunch(['GBP_JPY', -1])
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                # print('BUY: EUR/GBP')
                # print('SELL: GBP/USD')
                # print('SELL: GBP/JPY')

            if EUR == 1 and GBP == -1 and USD == 1 and JPY == 1:
                if spreadcheck({'EUR_GBP', 'GBP_USD', 'GBP_JPY'}) is True:
                    listing = api.request(orders_list)
                    if len(listing['orders']) is 0 and Multi_Threading is True:
                        p = mp.Pool(3)
                        data = (['EUR_GBP', -1], ['GBP_USD', 1], ['GBP_JPY', 1])
                        threads = p.map_async(orderlaunch, data)
                        threads.get()
                        p.close()
                        p.join()
                        p.terminate()
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened via MT..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                    elif len(listing['orders']) is 0:
                        orderlaunch(['EUR_GBP', -1])
                        orderlaunch(['GBP_USD', 1])
                        orderlaunch(['GBP_JPY', 1])
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                # print('SELL: EUR/GBP')
                # print('BUY: GBP/USD')
                # print('BUY: GBP/JPY')

            if EUR == 1 and GBP == -1 and USD == -1 and JPY == -1:
                if spreadcheck({'EUR_GBP', 'EUR_USD', 'EUR_JPY'}) is True:
                    listing = api.request(orders_list)
                    if len(listing['orders']) is 0 and Multi_Threading is True:
                        p = mp.Pool(3)
                        data = (['EUR_GBP', -1], ['EUR_USD', -1], ['EUR_JPY', -1])
                        threads = p.map_async(orderlaunch, data)
                        threads.get()
                        p.close()
                        p.join()
                        p.terminate()
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened via MT..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                    elif len(listing['orders']) is 0:
                        orderlaunch(['EUR_GBP', -1])
                        orderlaunch(['EUR_USD', -1])
                        orderlaunch(['EUR_JPY', -1])
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                # print('SELL: EUR/GBP')
                # print('SELL: EUR/USD')
                # print('SELL: EUR/JPY')

            if EUR == -1 and GBP == 1 and USD == 1 and JPY == 1:
                if spreadcheck({'EUR_GBP', 'EUR_USD', 'EUR_JPY'}) is True:
                    listing = api.request(orders_list)
                    if len(listing['orders']) is 0 and Multi_Threading is True:
                        p = mp.Pool(3)
                        data = (['EUR_GBP', 1], ['EUR_USD', 1], ['EUR_JPY', 1])
                        threads = p.map_async(orderlaunch, data)
                        threads.get()
                        p.close()
                        p.join()
                        p.terminate()
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened via MT..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                    elif len(listing['orders']) is 0:
                        orderlaunch(['EUR_GBP', 1])
                        orderlaunch(['EUR_USD', 1])
                        orderlaunch(['EUR_JPY', 1])
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                # print('BUY: EUR/GBP')
                # print('BUY: EUR/USD')
                # print('BUY: EUR/JPY')

            if EUR == -1 and GBP == -1 and USD == -1 and JPY == 1:
                if spreadcheck({'GBP_JPY', 'EUR_JPY', 'USD_JPY'}) is True:
                    listing = api.request(orders_list)
                    if len(listing['orders']) is 0 and Multi_Threading is True:
                        p = mp.Pool(3)
                        data = (['GBP_JPY', 1], ['EUR_JPY', 1], ['USD_JPY', 1])
                        threads = p.map_async(orderlaunch, data)
                        threads.get()
                        p.close()
                        p.join()
                        p.terminate()
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened via MT..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                    elif len(listing['orders']) is 0:
                        orderlaunch(['GBP_JPY', 1])
                        orderlaunch(['EUR_JPY', 1])
                        orderlaunch(['USD_JPY', 1])
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                # print('BUY: GBP/JPY')
                # print('BUY: EUR/JPY')
                # print('BUY: USD/JPY')

            if EUR == 1 and GBP == 1 and USD == 1 and JPY == -1:
                if spreadcheck({'GBP_JPY', 'EUR_JPY', 'USD_JPY'}) is True:
                    listing = api.request(orders_list)
                    if len(listing['orders']) is 0 and Multi_Threading is True:
                        p = mp.Pool(3)
                        data = (['GBP_JPY', -1], ['EUR_JPY', -1], ['USD_JPY', -1])
                        threads = p.map_async(orderlaunch, data)
                        threads.get()
                        p.close()
                        p.join()
                        p.terminate()
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened via MT..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                    elif len(listing['orders']) is 0:
                        orderlaunch(['GBP_JPY', -1])
                        orderlaunch(['EUR_JPY', -1])
                        orderlaunch(['USD_JPY', -1])
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                # print('SELL: GBP/JPY')
                # print('SELL: EUR/JPY')
                # print('SELL: USD/JPY')

            if EUR == -1 and GBP == -1 and USD == 1 and JPY == -1:
                if spreadcheck({'EUR_USD', 'GBP_USD', 'USD_JPY'}) is True:
                    listing = api.request(orders_list)
                    if len(listing['orders']) is 0 and Multi_Threading is True:
                        p = mp.Pool(3)
                        data = (['EUR_USD', 1], ['GBP_USD', 1], ['USD_JPY', -1])
                        threads = p.map_async(orderlaunch, data)
                        threads.get()
                        p.close()
                        p.join()
                        p.terminate()
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened via MT..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                    elif len(listing['orders']) is 0:
                        orderlaunch(['EUR_USD', 1])
                        orderlaunch(['GBP_USD', 1])
                        orderlaunch(['USD_JPY', -1])
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                # print('BUY: EUR/USD')
                # print('BUY: GBP/USD')
                # print('SELL: USD/JPY')

            if EUR == 1 and GBP == 1 and USD == -1 and JPY == 1:
                if spreadcheck({'EUR_USD', 'GBP_USD', 'USD_JPY'}) is True:
                    listing = api.request(orders_list)
                    if len(listing['orders']) is 0 and Multi_Threading is True:
                        p = mp.Pool(3)
                        data = (['EUR_USD', -1], ['GBP_USD', -1], ['USD_JPY', 1])
                        threads = p.map_async(orderlaunch, data)
                        threads.get()
                        p.close()
                        p.join()
                        p.terminate()
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened via MT..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                    elif len(listing['orders']) is 0:
                        orderlaunch(['EUR_USD', -1])
                        orderlaunch(['GBP_USD', -1])
                        orderlaunch(['USD_JPY', 1])
                        if Tgr_Verbose is True:
                            txt_msg = "Positions Opened..."
                            tb.send_message(chatid, txt_msg)
                        in_action = True
                        continue
                # print('SELL: EUR/USD')
                # print('SELL: GBP/USD')
                # print('BUY: USD/JPY')

    except V20Error as e:
        if Tgr_Verbose is True:
            txt_msg = "SyTrage crashed..."
            tb.send_message(chatid, txt_msg)
        print("Error: {}".format(e))


if __name__ == "__main__":
    try:
        if Tgr_Verbose is True:
            text_msg = "SyTrage ready..."
            tb.send_message(chatid, text_msg)
        main()
    except KeyboardInterrupt:
        if Tgr_Verbose is True:
            text_msg = "SyTrage stopped..."
            tb.send_message(chatid, text_msg)
        print("  ----- This is the end ! -----")
        pass
