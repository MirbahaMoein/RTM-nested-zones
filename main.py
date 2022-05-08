import binance.spot  # pip install binance-connector
import pandas as pd
from datetime import *
import mplfinance as mpf  # pip install mplfinance
from matplotlib import pyplot as plt

# Makes a binance spot api client
client = binance.spot.Spot()


def get_table(symbol: str, timeframe: str, lasttime: datetime):
    # Gets list-based table for a week and Creates pandas dataframe with table
    lasttimestamp = lasttime.timestamp()*1000

    if timeframe[-1:] == 'h':
        starttime = lasttime + 365 * timedelta(hours=-int(timeframe[:-1]))
    elif timeframe[-1:] == 'm':
        starttime = lasttime + 365 * timedelta(minutes=-int(timeframe[:-1]))
    elif timeframe[-1:] == 'd':
        starttime = lasttime + 365 * timedelta(days=-int(timeframe[:-1]))
    elif timeframe[-1:] == 'w':
        starttime = lasttime + 365 * timedelta(weeks=-int(timeframe[:-1]))
    elif timeframe[-1:] == 'M':
        starttime = lasttime + 365 * timedelta(months=-int(timeframe[:-1]))

    starttimestamp = starttime.timestamp()*1000
    print(starttimestamp)

    table = client.klines(symbol, timeframe, startTime=int(
        starttimestamp), endTime=int(lasttimestamp), limit=365)

    df = pd.DataFrame(table)

    df.columns = ['open_date', 'Open', 'High', 'Low', 'Close', 'Volume', 'close_date',
                  'qvolume', 'trades_number', 'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore']
    return df


def add_momentum(df):
    # adds momentum to dataframe and removes extra data
    momentums = []
    for i in range(len(df)):
        df['open_date'][i] = datetime.fromtimestamp(
            float(df['open_date'][i])/1000)
        df['close_date'][i] = datetime.fromtimestamp(
            float(df['close_date'][i])/1000)
        df['Open'][i] = float(df['Open'][i])
        df['High'][i] = float(df['High'][i])
        df['Low'][i] = float(df['Low'][i])
        df['Close'][i] = float(df['Close'][i])
        df['Volume'][i] = float(df['Volume'][i])
        if df['Open'][i] > df['Close'][i]:
            momentums.append(df['Open'][i] - df['Close'][i])
        else:
            momentums.append(df['Close'][i] - df['Open'][i])
    df['momentum'] = momentums
    return df


def modify(df):
    # modifies table
    df.sort_values(by='open_date')

    df.index = df['open_date']
    df.index.name = 'Date'

    df = df.drop(['open_date', 'close_date', 'qvolume', 'trades_number',
                 'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'], axis=1)
    df = df.astype(float)
    return df


def find_zones(df):
    # finds base candles and saves their highs and lows in zones dataframe
    zones = pd.DataFrame(columns=['date', 'top', 'bottom', 'TB'])
    for i in range(3, len(df) - 3):
        momentumbefore = df['momentum'][i-3] + \
            df['momentum'][i-2] + df['momentum'][i-1]
        momentumafter = df['momentum'][i+3] + \
            df['momentum'][i+2] + df['momentum'][i+1]
        if abs(df['momentum'][i]) < 1/20 * (abs(momentumbefore) + abs(momentumafter)):
            zones = zones.append(
                {'date': df.index[i], 'top': df['High'][i], 'bottom': df['Low'][i], 'TB': 0}, ignore_index=True)

    # counts the number of candles that overlap every zone and save in zones dataframe
    maxtb = 4
    for zindex in range(len(zones)):
        for dfindex in range(len(df)):
            if df.index[dfindex] > zones['date'][zindex]:
                if df['High'][dfindex] > zones['bottom'][zindex] and df['Low'][dfindex] < zones['top'][zindex]:
                    zones['TB'][zindex] += 1
                    if zones['TB'][zindex] > maxtb:
                        break

    # deletes zones that have more than 4 candles overlapping
    zones = zones[zones['TB'] <= 4].reset_index(drop=True)
    return zones


def lines(zones):
    # makes a list of price levels representing zones' tops and bottoms
    zonelines = []
    for zindex in range(len(zones)):
        zonelines.append(zones['top'][zindex])
        zonelines.append(zones['bottom'][zindex])
    return zonelines


def multi_timeframes(symbol: str, HTF: str, ITF: str, LTF: str, lastdate: datetime):

    # gets and modifies ohclv datasets for three timeframes
    df1 = modify(add_momentum(get_table(symbol, HTF, lastdate)))
    df2 = modify(add_momentum(get_table(symbol, ITF, lastdate)))
    df3 = modify(add_momentum(get_table(symbol, LTF, lastdate)))

    # finds valid zones in three timeframes and store them in three dataframes
    allzones1 = find_zones(df1)
    allzones2 = find_zones(df2)
    allzones3 = find_zones(df3)

    # finds nested zones tops and bottoms
    nestedzones1 = allzones1
    nestedzones2 = pd.DataFrame(columns=['date', 'top', 'bottom', 'TB'])
    nestedzones3 = pd.DataFrame(columns=['date', 'top', 'bottom', 'TB'])
    for i in range(len(allzones2)):
        for j in range(len(allzones1)):
            if allzones2['top'][i] <= allzones1['top'][j] and allzones2['bottom'][i] >= allzones1['bottom'][j]:
                nestedzones2 = nestedzones2.append(
                    {'date': allzones2['date'][i], 'top': allzones2['top'][i], 'bottom': allzones2['bottom'][i], 'TB': allzones2['TB'][i]}, ignore_index=True)
                break
    nestedzones2 = nestedzones2.drop_duplicates(ignore_index=True)
    for i in range(len(allzones3)):
        for j in range(len(nestedzones2)):
            if allzones3['top'][i] <= nestedzones2['top'][j] and allzones3['bottom'][i] >= nestedzones2['bottom'][j]:
                nestedzones3 = nestedzones3.append(
                    {'date': allzones3['date'][i], 'top': allzones3['top'][i], 'bottom': allzones3['bottom'][i], 'TB': allzones3['TB'][i]}, ignore_index=True)
                break
    nestedzones3 = nestedzones3.drop_duplicates(ignore_index=True)

    nestedzonelines1 = lines(nestedzones1)
    nestedzonelines2 = lines(nestedzones2)
    nestedzonelines3 = lines(nestedzones3)
    nestedzonelines = nestedzonelines1 + nestedzonelines2 + nestedzonelines3

    linecolors = []
    for i in range(len(nestedzonelines1)):
        linecolors.append('r')
    for i in range(len(nestedzonelines2)):
        linecolors.append('g')
    for i in range(len(nestedzonelines3)):
        linecolors.append('b')

    fig1, axlist1 = mpf.plot(df1, type='candle', volume=True, hlines=dict(
        hlines=nestedzonelines, colors=linecolors, linewidths=1, alpha=0.4), returnfig=True)
    fig2, axlist2 = mpf.plot(df2, type='candle', volume=True, hlines=dict(
        hlines=nestedzonelines, colors=linecolors, linewidths=1, alpha=0.4), returnfig=True)
    fig3, axlist3 = mpf.plot(df3, type='candle', volume=True, hlines=dict(
        hlines=nestedzonelines, colors=linecolors, linewidths=1, alpha=0.4), returnfig=True)

    ax = axlist1[0]
    ax.set_yscale('log')
    ax = axlist2[0]
    ax.set_yscale('log')
    ax = axlist3[0]
    ax.set_yscale('log')
    plt.show()


multi_timeframes('FILUSDT', '1d', '4h', '1h', datetime(2022, 5, 7, 9, 59))
