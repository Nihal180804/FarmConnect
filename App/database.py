"""
database.py
Utility functions to interact with MySQL using mysql-connector with pooling.
Wraps stored procedures and functions from your schema (see local SQL dump).
"""

import mysql.connector
from mysql.connector import pooling
from config import DB_CONFIG

pool = pooling.MySQLConnectionPool(
    pool_name="lfm_pool",
    pool_size=5,
    **DB_CONFIG
)

def get_conn():
    return pool.get_connection()

def fetchone(query, params=None):
    cnx = get_conn()
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(query, params or ())
    row = cursor.fetchone()
    cursor.close()
    cnx.close()
    return row

def fetchall(query, params=None):
    cnx = get_conn()
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    cnx.close()
    return rows

def execute(query, params=None):
    cnx = get_conn()
    cursor = cnx.cursor()
    cursor.execute(query, params or ())
    cnx.commit()
    lastrowid = cursor.lastrowid
    cursor.close()
    cnx.close()
    return lastrowid

def call_proc(procname, args=()):
    cnx = get_conn()
    cursor = cnx.cursor(dictionary=True)
    res = cursor.callproc(procname, args)
    # for stored procs returning result sets:
    results = []
    for result in cursor.stored_results():
        results.append(result.fetchall())
    cursor.close()
    cnx.close()
    return results or res

# Convenience wrappers for your DB functions / procs:

def calculate_order_total(order_id):
    cnx = get_conn()
    cursor = cnx.cursor()
    cursor.execute("SELECT CalculateOrderTotal(%s) AS total", (order_id,))
    r = cursor.fetchone()
    cursor.close()
    cnx.close()
    return r[0] if r else 0.0

def get_farmer_report(farmer_id):
    # Calls GetFarmerReport which returns 2 result sets.
    cnx = get_conn()
    cursor = cnx.cursor(dictionary=True)
    cursor.callproc('GetFarmerReport', (farmer_id,))
    reports = []
    for result in cursor.stored_results():
        reports.append(result.fetchall())
    cursor.close()
    cnx.close()
    return reports  # [overview_rows, product_rows]

def place_order_proc(customer_id, product_id, quantity):
    cnx = get_conn()
    cursor = cnx.cursor()
    # prepare out parameter
    # mysql-connector doesn't support OUT variables directly via callproc return; use work-around
    cursor.callproc('PlaceOrder', (customer_id, product_id, quantity, 0))
    # fetch order id from last insert
    cnx.commit()
    order_id = None
    cursor.execute("SELECT LAST_INSERT_ID()")
    order_id = cursor.fetchone()[0]
    cursor.close()
    cnx.close()
    return order_id

def add_product_review(customer_id, product_id, rating, comment):
    cnx = get_conn()
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.callproc('AddProductReview', (customer_id, product_id, rating, comment))
        # read any resultsets
        results = []
        for res in cursor.stored_results():
            results.append(res.fetchall())
        cnx.commit()
        return {'success': True, 'results': results}
    except mysql.connector.Error as e:
        cnx.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        cursor.close()
        cnx.close()

def get_customer_loyalty_points(customer_id):
    """Get loyalty points for a customer using GetCustomerLoyaltyPoints function"""
    cnx = get_conn()
    cursor = cnx.cursor()
    cursor.execute("SELECT GetCustomerLoyaltyPoints(%s) AS points", (customer_id,))
    r = cursor.fetchone()
    cursor.close()
    cnx.close()
    return r[0] if r else 0
