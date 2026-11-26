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

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'top_secret_quarktwin_key_2026')

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    return pymysql.connect(host='localhost', user='appuser', password='Bta3456789', database='quarktwin_crm', charset='utf8mb4')

@app.route('/')
def index():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session['captcha_answer'] = num1 + num2
    return render_template('index.html', num1=num1, num2=num2, error=None)

@app.route('/submit', methods=['POST'])
def submit():
    try:
        user_answer = request.form.get('captcha', type=int)
        if user_answer != session.get('captcha_answer'):
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            session['captcha_answer'] = num1 + num2
            return render_template('index.html', num1=num1, num2=num2, error="Security Check Failed! Please try again.")
            
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        
        image_url = ""
        if 'chip_image' in request.files:
            file = request.files['chip_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = str(int(time.time())) + "_" + filename
                save_path = os.path.join('/var/www/html/static/uploads', filename)
                file.save(save_path)
                image_url = f"/static/uploads/{filename}"
                
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT username FROM users WHERE role = 'sales' ORDER BY id")
        sales_users = [u[0] for u in cursor.fetchall()]
        
        assigned_to = 'Unassigned'
        if sales_users:
            cursor.execute("SELECT COUNT(*) FROM customers")
            total = cursor.fetchone()[0]
            assigned_to = sales_users[total % len(sales_users)]
            
        cursor.execute("INSERT INTO customers (name, email, message, assigned_to, image_url) VALUES (%s, %s, %s, %s, %s)", (name, email, message, assigned_to, image_url))
        db.commit()
        db.close()

        if WEBHOOK_URL:
            try:
                alert_data = {"msgtype": "markdown", "markdown": {"content": f"### 🚨 新询盘！\n> **客户**：{name}\n> **邮箱**：{email}\n> **需求**：{message}"}}
                requests.post(WEBHOOK_URL, json=alert_data)
            except: pass

        return "<div style='text-align:center; margin-top:100px;'><h2 style='color:green;'>Thank you! Inquiry received.</h2><a href='/'>Home</a></div>"
    except Exception as e:
        return f"<h2>Oops! Error: {str(e)}</h2>", 500

# ==========================================
# 🚀 购物车核心逻辑
# ==========================================
@app.route('/shop')
def shop():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, model, price, stock, description FROM shop_products")
        products = cursor.fetchall()
        db.close()
        return render_template('shop.html', products=products)
    except Exception as e:
        return f"<h2>Shop Error: {str(e)}</h2>", 500

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    return redirect(url_for('shop'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    if not cart:
        return "<h3>Your cart is empty. <a href='/shop'>Go Shopping</a></h3>"
    
    db = get_db()
    cursor = db.cursor()
    items = []
    total = 0
    for pid, qty in cart.items():
        cursor.execute("SELECT id, name, price FROM shop_products WHERE id = %s", (pid,))
        product = cursor.fetchone()
        if product:
            subtotal = product[2] * qty
            total += subtotal
            items.append({'id': product[0], 'name': product[1], 'price': product[2], 'qty': qty, 'subtotal': subtotal})
    db.close()
    return render_template('cart.html', items=items, total=total)

@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('shop'))
    
    email = request.form['email']
    db = get_db()
    cursor = db.cursor()
    
    # 计算总价
    total_amount = 0
    for pid, qty in cart.items():
        cursor.execute("SELECT price FROM shop_products WHERE id = %s", (pid,))
        price = cursor.fetchone()[0]
        total_amount += price * qty
        
    # 插入主订单
    cursor.execute("INSERT INTO shop_orders (customer_email, total_amount) VALUES (%s, %s)", (email, total_amount))
    order_id = cursor.lastrowid
    
    # 插入订单明细
    for pid, qty in cart.items():
        cursor.execute("SELECT price FROM shop_products WHERE id = %s", (pid,))
        price = cursor.fetchone()[0]
        cursor.execute("INSERT INTO shop_order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)", (order_id, pid, qty, price))
        
    db.commit()
    db.close()
    
    session.pop('cart', None) # 清空购物车
    return f"<div style='text-align:center; margin-top:100px;'><h2 style='color:green;'>Order Placed Successfully!</h2><p>Order ID: #{order_id}</p><a href='/shop'>Continue Shopping</a></div>"

# ... (保留你原来的登录、后台、导出等代码，这里为了省空间就不全贴了，只要你原有代码不要删就行)