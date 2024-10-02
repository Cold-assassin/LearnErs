from flask import Flask, request, jsonify, render_template, send_file
import requests
from datetime import datetime, timedelta
from flask import jsonify, request
import traceback
import random
from io import BytesIO


app = Flask(__name__)

# Initialize a simple user account
user_account = {
    "username": "retail_investor",
    "cash": 100000,  # Start with $100,000 virtual money
    "portfolio": {}  # Dictionary to hold stock/option holdings
}

API_KEY = 'YOUR API KEY'
BASE_URL = 'https://www.alphavantage.co/query?'

def get_stock_price(symbol):
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': symbol,
        'apikey': API_KEY
    }
    try:
        print(f"Sending request to Alpha Vantage API for symbol: {symbol}")
        response = requests.get(BASE_URL, params=params)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        
        response.raise_for_status()  # Raises HTTPError for bad HTTP responses
        data = response.json()

        if 'Global Quote' in data and '05. price' in data['Global Quote']:
            price = float(data['Global Quote']['05. price'])
            return price
        else:
            print(f"Unexpected data format from API: {data}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching stock price: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing JSON: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buy', methods=['POST'])
def buy_stock():
    try:
        print("Received buy request. Form data:", request.form)
        symbol = request.form.get('symbol', '').upper().strip()
        quantity = request.form.get('quantity', '').strip()
        print(f"Extracted symbol: '{symbol}', quantity: '{quantity}'")

        if not symbol or not quantity.isdigit():
            print(f"Invalid input: symbol='{symbol}', quantity='{quantity}'")
            return jsonify({"error": "Invalid input. Ensure symbol is a valid stock symbol and quantity is a positive integer."}), 400
        
        quantity = int(quantity)
        print(f"Buying {quantity} shares of {symbol}")

        price = get_stock_price(symbol)
        if price is None:
            return jsonify({"error": f"Unable to fetch price for symbol: {symbol}. Please try again later."}), 400

        total_cost = price * quantity
        print(f"Total cost: {total_cost}, Available cash: {user_account['cash']}")

        if user_account['cash'] >= total_cost:
            user_account['cash'] -= total_cost
            user_account['portfolio'][symbol] = user_account['portfolio'].get(symbol, 0) + quantity
            return jsonify({"message": f"Bought {quantity} shares of {symbol} at ${price:.2f} each."})
        else:
            return jsonify({"error": "Not enough cash to complete this transaction."}), 400
    except Exception as e:
        print("Exception during buy_stock:", str(e))
        print("Full traceback:", traceback.format_exc())
        return jsonify({"error": "An error occurred during the transaction."}), 400

@app.route('/search', methods=['POST'])
def search_stock():
    try:
        print("Received search request. Form data:", request.form)
        symbol = request.form.get('symbol', '').upper().strip()
        print(f"Extracted symbol: '{symbol}'")

        if not symbol:
            print("Invalid input: empty symbol")
            return jsonify({"error": "Invalid stock symbol."}), 400

        price = get_stock_price(symbol)
        print(f"Price for {symbol}: {price}")
        if price is not None:
            return jsonify({"price": price})
        return jsonify({"error": f"Invalid stock symbol: {symbol}."}), 400
    except Exception as e:
        print("Exception during search_stock:", str(e))
        print("Full traceback:", traceback.format_exc())
        return jsonify({"error": "An error occurred during the search."}), 400


@app.route('/sell', methods=['POST'])
def sell_stock():
    try:
        symbol = request.form.get('symbol', '').upper().strip()
        quantity = request.form.get('quantity', '').strip()

        if not symbol or not quantity.isdigit():
            return jsonify({"error": "Invalid input. Ensure symbol is a valid stock symbol and quantity is a positive integer."}), 400

        quantity = int(quantity)

        if symbol not in user_account['portfolio'] or user_account['portfolio'][symbol] < quantity:
            return jsonify({"error": "Not enough shares or invalid stock symbol."}), 400

        price = get_stock_price(symbol)
        if price is None:
            return jsonify({"error": f"Invalid stock symbol: {symbol}."}), 400

        total_value = price * quantity
        user_account['cash'] += total_value
        user_account['portfolio'][symbol] -= quantity

        if user_account['portfolio'][symbol] == 0:
            del user_account['portfolio'][symbol]

        return jsonify({"message": f"Sold {quantity} shares of {symbol} at ${price:.2f} each."})
    except Exception as e:
        print("Exception during sell_stock:", str(e))
        return jsonify({"error": "An error occurred during the transaction."}), 400

@app.route('/portfolio')
def display_portfolio():
    total_value = user_account['cash']
    portfolio_data = []

    for symbol, stock_data in user_account['portfolio'].items():
        # `stock_data` would contain 'quantity', 'executions' (list of buy/sell data)
        quantity = stock_data['quantity']
        current_price = get_stock_price(symbol)
        
        if current_price is not None:
            # Calculate the total value of the holdings
            value = current_price * quantity
            total_value += value

            # Transaction details (assuming we track buys and sells separately)
            execution_details = []
            for execution in stock_data['executions']:
                execution_details.append({
                    "type": execution['type'],  # 'buy' or 'sell'
                    "price": execution['price'],  # price at which the stock was bought/sold
                    "quantity": execution['quantity'],  # number of stocks bought/sold
                    "date": execution['date']  # optional: date of the transaction
                })
            
            # Append the portfolio details including execution history
            portfolio_data.append({
                "symbol": symbol,
                "quantity": quantity,
                "current_price": current_price,
                "value": value,
                "executions": execution_details  # Transaction history for the stock
            })

    return jsonify({
        "cash": user_account['cash'],
        "portfolio": portfolio_data,
        "total_value": total_value
    })



@app.route('/live-stock-data/<symbol>')
def live_stock_data(symbol):
    now = datetime.now()
    data_points = 30  # Number of data points to simulate
    prices = [random.uniform(100, 200) for _ in range(data_points)]
    timestamps = [(now - timedelta(minutes=(data_points - i) * 5)).isoformat() for i in range(data_points)]
    
    return jsonify({
        "symbol": symbol,
        "data": list(zip(timestamps, prices))
    })

# ================== New Feature: Export Portfolio as DOCX ==================

@app.route('/export_portfolio_txt', methods=['GET'])
def export_portfolio_txt():
    try:
        # Generate portfolio content
        content_str = "Portfolio Report\n\n"
        content_str += f"Cash: ${user_account['cash']:.2f}\n\n"
        content_str += "Holdings:\n"
        for symbol, quantity in user_account['portfolio'].items():
            price = get_stock_price(symbol)
            if price is not None:
                value = price * quantity
                content_str += f"{symbol}: {quantity} shares, Current Price: ${price:.2f}, Value: ${value:.2f}\n"
        
        # Create BytesIO object
        txt_io = BytesIO()
        txt_io.write(content_str.encode('utf-8'))
        txt_io.seek(0)
        
        # Return the file
        return send_file(
            txt_io,
            as_attachment=True,
            download_name='portfolio_report.txt',
            mimetype='text/plain'
        )
    except Exception as e:
        print("Exception during export_portfolio_txt:", str(e))
        print("Full traceback:", traceback.format_exc())
        return jsonify({"error": "An error occurred while exporting the portfolio."}), 500




# =================================================================================

if __name__ == '__main__':
    app.run(debug=True)
