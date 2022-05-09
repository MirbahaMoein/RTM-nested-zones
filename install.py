import subprocess
import sys


def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


install('binance-connector')
install('pandas')
install('mplfinance')
install('matplotlib')
