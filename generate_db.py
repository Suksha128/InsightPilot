import sqlite3
import random
from datetime import datetime, timedelta

def create_db(db_name="business_data.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            join_date DATE,
            segment TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL,
            cost REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date DATE,
            status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price REAL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            plan_name TEXT,
            start_date DATE,
            end_date DATE,
            is_active BOOLEAN,
            monthly_fee REAL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    ''')

    conn.commit()

    # Create semantic business views
    cursor.execute('''
        CREATE VIEW IF NOT EXISTS sales_summary AS
        SELECT 
            strftime('%Y-%m', o.order_date) as month,
            p.category,
            SUM(oi.quantity * oi.unit_price) as total_revenue,
            SUM(oi.quantity) as total_items_sold
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE o.status = 'Completed'
        GROUP BY month, p.category
    ''')

    cursor.execute('''
        CREATE VIEW IF NOT EXISTS customer_health AS
        SELECT 
            c.customer_id,
            c.name,
            c.segment,
            COUNT(DISTINCT o.order_id) as total_orders,
            SUM(oi.quantity * oi.unit_price) as lifetime_value,
            COALESCE(MAX(s.is_active), 0) as has_active_subscription
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status = 'Completed'
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        LEFT JOIN subscriptions s ON c.customer_id = s.customer_id
        GROUP BY c.customer_id
    ''')

    cursor.execute('''
        CREATE VIEW IF NOT EXISTS product_profitability AS
        SELECT 
            p.product_id,
            p.name,
            p.category,
            SUM(oi.quantity * oi.unit_price) as total_revenue,
            SUM(oi.quantity * p.cost) as total_cost,
            SUM(oi.quantity * (oi.unit_price - p.cost)) as total_margin
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        JOIN orders o ON oi.order_id = o.order_id AND o.status = 'Completed'
        GROUP BY p.product_id
    ''')

    conn.commit()
    # Populate data if empty
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] == 0:
        print("Populating database with synthetic data...")
        
        # Customers
        segments = ['Retail', 'Enterprise', 'SMB']
        for i in range(1, 101):
            join_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365))
            cursor.execute(
                "INSERT INTO customers (name, email, join_date, segment) VALUES (?, ?, ?, ?)",
                (f"Customer {i}", f"customer{i}@example.com", join_date.strftime('%Y-%m-%d'), random.choice(segments))
            )

        # Products
        categories = ['Software', 'Hardware', 'Services']
        products_data = [
            ('Analytics Pro', 'Software', 99.99, 10.00),
            ('Cloud Storage 1TB', 'Software', 19.99, 2.00),
            ('Server Rack X1', 'Hardware', 4999.99, 3000.00),
            ('Consulting Hour', 'Services', 150.00, 50.00),
            ('Enterprise Support', 'Services', 500.00, 100.00)
        ]
        for p in products_data:
            cursor.execute("INSERT INTO products (name, category, price, cost) VALUES (?, ?, ?, ?)", p)

        # Orders & Order Items
        for i in range(1, 301): # 300 orders
            customer_id = random.randint(1, 100)
            order_date = datetime(2023, 6, 1) + timedelta(days=random.randint(0, 365))
            status = random.choice(['Completed', 'Completed', 'Completed', 'Pending', 'Cancelled'])
            
            cursor.execute(
                "INSERT INTO orders (customer_id, order_date, status) VALUES (?, ?, ?)",
                (customer_id, order_date.strftime('%Y-%m-%d'), status)
            )
            order_id = cursor.lastrowid
            
            # 1 to 3 items per order
            for _ in range(random.randint(1, 3)):
                product_id = random.randint(1, len(products_data))
                quantity = random.randint(1, 5)
                # Get current price
                cursor.execute("SELECT price FROM products WHERE product_id = ?", (product_id,))
                price = cursor.fetchone()[0]
                
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (order_id, product_id, quantity, price)
                )

        # Subscriptions
        for i in range(1, 51): # 50 subscriptions
            customer_id = random.randint(1, 100)
            plans = [('Basic', 9.99), ('Pro', 29.99), ('Enterprise', 99.99)]
            plan = random.choice(plans)
            start_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 180))
            is_active = random.choice([True, True, False]) # More likely to be active
            end_date = (start_date + timedelta(days=365)).strftime('%Y-%m-%d') if not is_active else None
            
            cursor.execute(
                "INSERT INTO subscriptions (customer_id, plan_name, start_date, end_date, is_active, monthly_fee) VALUES (?, ?, ?, ?, ?, ?)",
                (customer_id, plan[0], start_date.strftime('%Y-%m-%d'), end_date, is_active, plan[1])
            )

        conn.commit()
        print("Database populated successfully.")
    else:
        print("Database already contains data.")

    conn.close()

if __name__ == "__main__":
    create_db()
