import stripe
import os
from flask import Flask, request, render_template, redirect, url_for, session, make_response
import pymysql
import pandas as pd
from io import BytesIO
import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from werkzeug.utils import secure_filename
import base64
import ssl
import time
import json
import random
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'top_secret_quarktwin_key_2026')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
stripe.api_key = STRIPE_SECRET_KEY
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'top_secret_quarktwin_key_2026')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

# 🚀 这才是读取 Stripe 密钥的正确方式
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
stripe.api_key = STRIPE_SECRET_KEY
import pymysql
import os
import pandas as pd
from io import BytesIO
import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from werkzeug.utils import secure_filename
import base64
import ssl
import time
import json
import random
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
# 🚀 读取 Stripe Key
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
stripe.api_key = STRIPE_SECRET_KEY

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    return pymysql.connect(host='localhost', user='appuser', password='Bta3456789', database='quarktwin_crm', charset='utf8mb4')

# ... (这里省略上面那些没变的：首页、询盘、后台、AI、购物车代码，直接复制我之前发你的“终极完全体”代码即可) ...
# 注意：把旧的 checkout 路由删掉，替换成下面的！

# ==========================================
# 🚀 修改结算路由：跳转 Stripe 支付
# ==========================================
from flask import Flask, request, render_template, redirect, url_for, session, make_response
import pymysql
import os
import pandas as pd
from io import BytesIO
import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from werkzeug.utils import secure_filename
import base64
import ssl
import time
import json
import random
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
# 🚀 读取 Stripe Key
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
stripe.api_key = STRIPE_SECRET_KEY

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    return pymysql.connect(host='localhost', user='appuser', password='Bta3456789', database='quarktwin_crm', charset='utf8mb4')

# ... (这里省略上面那些没变的：首页、询盘、后台、AI、购物车代码，直接复制我之前发你的“终极完全体”代码即可) ...
# 注意：把旧的 checkout 路由删掉，替换成下面的！

# ==========================================
# 🚀 修改结算路由：跳转 Stripe 支付
# ==========================================
@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('shop'))
    
    email = request.form['email']
    db = get_db()
    cursor = db.cursor()
    
    total_amount = 0
    line_items = []
    
    # 计算总价并准备 Stripe 所需的商品列表
    for pid, qty in cart.items():
        cursor.execute("SELECT name, price FROM shop_products WHERE id = %s", (pid,))
        product = cursor.fetchone()
        if product:
            price = product[1]
            total_amount += price * qty
            # 转换为 Stripe 格式（单位是美分）
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': product[0]},
                    'unit_amount': int(float(price) * 100),
                },
                'quantity': qty,
            })
            
    # 插入一条 Pending 订单
    cursor.execute("INSERT INTO shop_orders (customer_email, total_amount, status) VALUES (%s, %s, 'Pending Payment')", (email, total_amount))
    order_id = cursor.lastrowid
    
    # 插入订单明细
    for pid, qty in cart.items():
        cursor.execute("SELECT price FROM shop_products WHERE id = %s", (pid,))
        price = cursor.fetchone()[0]
        cursor.execute("INSERT INTO shop_order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)", (order_id, pid, qty, price))
        
    db.commit()
    db.close()
    
    try:
        # 调用 Stripe 生成支付链接
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=email,
            success_url=url_for('success', order_id=order_id, _external=True),
            cancel_url=url_for('cart', _external=True),
            client_reference_id=str(order_id)
        )
        # 跳转到 Stripe 支付页面
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return f"<h2>Stripe Error: {str(e)}</h2>"

# 支付成功回调页面
@app.route('/success')
def success():
    order_id = request.args.get('order_id')
    # 实际业务中这里应该通过 Webhook 确认支付状态，为了演示，我们直接改状态
    if order_id:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE shop_orders SET status = 'Paid' WHERE id = %s", (order_id,))
        db.commit()
        db.close()
        session.pop('cart', None) # 清空购物车
        
    return f"<div style='text-align:center; margin-top:100px;'><h2 style='color:green;'>🎉 Payment Successful!</h2><p>Your order has been received. We will ship it soon.</p><a href='/shop'>Back to Shop</a></div>"
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('shop'))
    
    email = request.form['email']
    db = get_db()
    cursor = db.cursor()
    
    total_amount = 0
    line_items = []
    
    # 计算总价并准备 Stripe 所需的商品列表
    for pid, qty in cart.items():
        cursor.execute("SELECT name, price FROM shop_products WHERE id = %s", (pid,))
        product = cursor.fetchone()
        if product:
            price = product[1]
            total_amount += price * qty
            # 转换为 Stripe 格式（单位是美分）
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': product[0]},
                    'unit_amount': int(float(price) * 100),
                },
                'quantity': qty,
            })
            
    # 插入一条 Pending 订单
    cursor.execute("INSERT INTO shop_orders (customer_email, total_amount, status) VALUES (%s, %s, 'Pending Payment')", (email, total_amount))
    order_id = cursor.lastrowid
    
    # 插入订单明细
    for pid, qty in cart.items():
        cursor.execute("SELECT price FROM shop_products WHERE id = %s", (pid,))
        price = cursor.fetchone()[0]
        cursor.execute("INSERT INTO shop_order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)", (order_id, pid, qty, price))
        
    db.commit()
    db.close()
    
    try:
        # 调用 Stripe 生成支付链接
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=email,
            success_url=url_for('success', order_id=order_id, _external=True),
            cancel_url=url_for('cart', _external=True),
            client_reference_id=str(order_id)
        )
        # 跳转到 Stripe 支付页面
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return f"<h2>Stripe Error: {str(e)}</h2>"

# 支付成功回调页面
@app.route('/success')
def success():
    order_id = request.args.get('order_id')
    # 实际业务中这里应该通过 Webhook 确认支付状态，为了演示，我们直接改状态
    if order_id:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE shop_orders SET status = 'Paid' WHERE id = %s", (order_id,))
        db.commit()
        db.close()
        session.pop('cart', None) # 清空购物车
        
    return f"<div style='text-align:center; margin-top:100px;'><h2 style='color:green;'>🎉 Payment Successful!</h2><p>Your order has been received. We will ship it soon.</p><a href='/shop'>Back to Shop</a></div>"