import curses
import sqlite3
import yfinance as yf
import pandas as pd
import threading
import time

class StockViewer:
    def __init__(self):
        self.db_conn = sqlite3.connect('stocks.db', check_same_thread=False)
        self.cursor = self.db_conn.cursor()
        self.create_table()
        self.stocks = []
        self.current_index = 0
        self.refresh_interval = 60  # Refresh every 60 seconds
        self.stop_refresh = threading.Event()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                last_price REAL,
                change REAL,
                volume INTEGER
            )
        ''')
        self.db_conn.commit()

    def fetch_stock_data(self, symbol):
        stock = yf.Ticker(symbol)
        info = stock.info
        return {
            'symbol': symbol,
            'name': info.get('longName', 'N/A'),
            'last_price': info.get('currentPrice', 0),
            'change': info.get('regularMarketChangePercent', 0),
            'volume': info.get('volume', 0)
        }

    def add_stock(self, symbol):
        data = self.fetch_stock_data(symbol)
        self.cursor.execute('''
            INSERT OR REPLACE INTO stocks (symbol, name, last_price, change, volume)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['symbol'], data['name'], data['last_price'], data['change'], data['volume']))
        self.db_conn.commit()
        self.stocks.append(data)

    def load_stocks(self):
        self.cursor.execute('SELECT * FROM stocks')
        rows = self.cursor.fetchall()
        self.stocks = [{'symbol': row[0], 'name': row[1], 'last_price': row[2], 'change': row[3], 'volume': row[4]} for row in rows]

    def update_stock_prices(self):
        while not self.stop_refresh.is_set():
            for stock in self.stocks:
                updated_data = self.fetch_stock_data(stock['symbol'])
                self.cursor.execute('''
                    UPDATE stocks
                    SET last_price = ?, change = ?, volume = ?
                    WHERE symbol = ?
                ''', (updated_data['last_price'], updated_data['change'], updated_data['volume'], stock['symbol']))
                self.db_conn.commit()
                stock.update(updated_data)
            time.sleep(self.refresh_interval)

    def display(self, stdscr):
        curses.curs_set(0)
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Display header
        header = "Stock Viewer (Press 'q' to quit, 'a' to add stock)"
        stdscr.addstr(0, 0, header, curses.A_REVERSE)

        # Display stocks
        for idx, stock in enumerate(self.stocks):
            if idx >= height - 2:
                break
            if idx == self.current_index:
                mode = curses.A_REVERSE
            else:
                mode = curses.A_NORMAL
            stdscr.addstr(idx + 2, 0, f"{stock['symbol']: <10} {stock['name']: <30} ${stock['last_price']:.2f} ({stock['change']:.2f}%)", mode)

        stdscr.refresh()

    def run(self):
        curses.wrapper(self.main)

    def main(self, stdscr):
        self.load_stocks()
        refresh_thread = threading.Thread(target=self.update_stock_prices)
        refresh_thread.start()

        while True:
            self.display(stdscr)
            key = stdscr.getch()
            if key == ord('q'):
                self.stop_refresh.set()
                break
            elif key == ord('a'):
                curses.echo()
                stdscr.addstr(0, 0, "Enter stock symbol: ")
                symbol = stdscr.getstr().decode().strip().upper()
                curses.noecho()
                if symbol:
                    self.add_stock(symbol)
            elif key == curses.KEY_UP and self.current_index > 0:
                self.current_index -= 1
            elif key == curses.KEY_DOWN and self.current_index < len(self.stocks) - 1:
                self.current_index += 1

        refresh_thread.join()
        self.db_conn.close()

if __name__ == "__main__":
    viewer = StockViewer()
    viewer.run()

print("Stock viewer application with auto-refresh feature created successfully.")


