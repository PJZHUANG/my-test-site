from flask import Flask, request, render_template, redirect, url_for, session, make_response
import pymysql
import os
import pandas as pd
from io import BytesIO
import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'top_secret_quarktwin_key_2026')

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')

def get_db():
    return pymysql.connect(host='localhost', user='appuser', password='Bta3456789', database='quarktwin_crm', charset='utf8mb4')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO customers (name, email, message) VALUES (%s, %s, %s)", (name, email, message))
        db.commit()
        db.close()
        return "<div style='text-align:center; margin-top:100px;'><h2 style='color:green;'>Thank you! Inquiry received.</h2><a href='/'>Home</a></div>"
    except Exception as e:
        return f"<h2>Oops! Error: {str(e)}</h2>", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, username, role FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        db.close()
        
        if user:
            session['logged_in'] = True
            session['username'] = user[1]
            session['role'] = user[2]  # 记录角色
            return redirect(url_for('admin'))
        return "<h3>Invalid credentials! <a href='/login'>Try again</a></h3>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 权限装饰器：只有老板能导出
@app.route('/export')
def export_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    # 🛡️ 核心安全拦截
    if session.get('role') != 'boss':
        return "<h2 style='color:red; text-align:center; margin-top:50px;'>Access Denied! Only the Boss can export data.</h2>", 403
        
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, message, status FROM customers ORDER BY id DESC")
        rows = cursor.fetchall()
        db.close()
        df = pd.DataFrame(rows, columns=['ID', 'Name', 'Email', 'Message', 'Status'])
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Inquiries')
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=customer_inquiries.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    except Exception as e:
        return f"<h2>Export Error: {str(e)}</h2>", 500

@app.route('/ai_reply/<int:customer_id>')
def ai_reply(customer_id):
    if not session.get('logged_in'):
        return "Access Denied", 403
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT name, email, message FROM customers WHERE id = %s", (customer_id,))
        row = cursor.fetchone()
        db.close()
        
        if not row:
            return "Customer not found", 404
            
        customer_name, customer_email, customer_message = row
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        prompt = f"你是一家深圳顶尖电子元器件供应商（QuarkTwin）的外贸销售总监。请针对客户的留言写一封英文回复邮件。客户留言：'{customer_message}'。请直接输出邮件正文，不要任何废话。"
        data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
        
        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data)
        ai_content = response.json()['choices'][0]['message']['content']
        
        return f"""
        <div style="font-family: Arial; padding: 50px; max-width: 800px; margin: 0 auto;">
            <h3>AI 生成的回复草稿 (发给 {customer_email})：</h3>
            <form action="/send_email/{customer_id}" method="POST">
                <textarea name="email_content" style="width: 100%; height: 300px; padding: 20px; font-size: 16px; border-radius: 8px; border: 1px solid #ccc;">{ai_content}</textarea>
                <br><br>
                <button type="submit" style="padding: 15px 30px; background: #198754; color: white; border: none; border-radius: 5px; font-size: 18px; cursor: pointer;">📤 确认发送邮件</button>
                <a href="/admin" style="padding: 15px 30px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; font-size: 18px; margin-left: 10px;">取消</a>
            </form>
        </div>
        """
    except Exception as e:
        return f"<h2>AI Error: {str(e)}</h2>", 500

@app.route('/send_email/<int:customer_id>', methods=['POST'])
def send_email(customer_id):
    if not session.get('logged_in'):
        return "Access Denied", 403
    try:
        email_content = request.form['email_content']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT email FROM customers WHERE id = %s", (customer_id,))
        row = cursor.fetchone()
        
        if not row:
            return "Customer not found", 404
            
        customer_email = row[0]
        msg = MIMEText(email_content, 'plain', 'utf-8')
        msg['Subject'] = Header('QuarkTwin - Regarding your inquiry', 'utf-8')
        msg['From'] = SMTP_USER
        msg['To'] = customer_email
        
        server = smtplib.SMTP_SSL('smtp.qq.com', 465)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [customer_email], msg.as_string())
        server.quit()
        
        cursor.execute("UPDATE customers SET status = 'Replied' WHERE id = %s", (customer_id,))
        db.commit()
        db.close()
        return redirect(url_for('admin'))
    except Exception as e:
        return f"<h2>Email Send Error: {str(e)}</h2>", 500

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, message, status FROM customers ORDER BY id DESC")
        rows = cursor.fetchall()
        db.close()
        
        # 根据登录用户的角色，动态生成顶部按钮
        export_btn = '<a href="/export" style="background-color: #198754; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; margin-right: 10px;">📥 EXPORT EXCEL</a>' if session.get('role') == 'boss' else ''
        
        html = f"""
        <html>
        <head>
            <title>QuarkTwin Admin</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="p-5 bg-light">
            <div class="container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0;">Welcome, {session.get('username')} ({session.get('role')})</h2>
                    <div>
                        {export_btn}
                        <a href="/logout" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">🔒 LOG OUT</a>
                    </div>
                </div>
                <table class="table table-bordered table-hover bg-white shadow-sm">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>Name</th><th>Email</th><th>Message</th><th>状态</th><th>操作</th></tr>
                    </thead>
                    <tbody>
        """
        for row in rows:
            status_badge = '<span class="badge bg-success">Replied</span>' if row[4] == 'Replied' else '<span class="badge bg-warning text-dark">Pending</span>'
            action_btn = f'<a href="/ai_reply/{row[0]}" style="background-color: #6f42c1; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px; white-space: nowrap; display: inline-block;">🤖 AI 写回复</a>' if row[4] != 'Replied' else ''
            
            html += f"""
            <tr>
                <td>{row[0]}</td>
                <td>{row[1]}</td>
                <td>{row[2]}</td>
                <td>{row[3]}</td>
                <td>{status_badge}</td>
                <td>{action_btn}</td>
            </tr>
            """
            
        html += """
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return f"<h2>Database Error: {str(e)}</h2>", 500

if __name__ == '__main__':
    app.run()