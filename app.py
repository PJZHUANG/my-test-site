from flask import Flask, request, render_template, redirect, url_for, session, make_response
import pymysql
import os
import pandas as pd
from io import BytesIO
import requests # 新增：用来调 AI 接口

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'top_secret_quarktwin_key_2026')

# ⚠️ 把这里换成你刚才去 DeepSeek 申请的 sk- 开头的 API Key
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

def get_db():
    return pymysql.connect(
        host='localhost', user='appuser', password='Bta3456789', database='quarktwin_crm', charset='utf8mb4'
    )

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
        sql = "INSERT INTO customers (name, email, message) VALUES (%s, %s, %s)"
        cursor.execute(sql, (name, email, message))
        db.commit()
        db.close()
        return "<div style='text-align:center; margin-top:100px;'><h2 style='color:green;'>Thank you! Inquiry received.</h2><a href='/'>Home</a></div>"
    except Exception as e:
        return f"<h2>Oops! Error: {str(e)}</h2>", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'boss' and request.form['password'] == '88888888':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return "<h3>Invalid credentials! <a href='/login'>Try again</a></h3>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/export')
def export_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, message FROM customers ORDER BY id DESC")
        rows = cursor.fetchall()
        db.close()
        df = pd.DataFrame(rows, columns=['ID', 'Name', 'Email', 'Message'])
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

# ==========================================
# 🚀 新增：AI 自动生成回复路由
# ==========================================
@app.route('/ai_reply/<int:customer_id>')
def ai_reply(customer_id):
    if not session.get('logged_in'):
        return "Access Denied", 403
        
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT name, message FROM customers WHERE id = %s", (customer_id,))
        row = cursor.fetchone()
        db.close()
        
        if not row:
            return "Customer not found", 404
            
        customer_name, customer_message = row
        
        # 调用 DeepSeek AI
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = f"你是一家深圳顶尖电子元器件供应商（QuarkTwin）的外贸销售总监。请根据以下客户的询盘，写一封极其专业、热情的英文回复邮件。客户的留言是：'{customer_message}'。请直接输出邮件正文，不要任何废话。"
        
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data)
        ai_content = response.json()['choices'][0]['message']['content']
        
        return f"""
        <div style="font-family: Arial; padding: 50px;">
            <h3>AI 生成的回复草稿 (给 {customer_name})：</h3>
            <textarea style="width: 100%; height: 300px; padding: 20px; font-size: 16px;">{ai_content}</textarea>
            <br><br>
            <a href="/admin" style="padding: 10px 20px; background: #0d6efd; color: white; text-decoration: none; border-radius: 5px;">返回后台</a>
        </div>
        """
    except Exception as e:
        return f"<h2>AI Error: {str(e)}</h2>", 500

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, message FROM customers ORDER BY id DESC")
        rows = cursor.fetchall()
        db.close()
        
        html = """
        <html>
        <head>
            <title>QuarkTwin Admin</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="p-5 bg-light">
            <div class="container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0;">Customer Inquiries</h2>
                    <div>
                        <a href="/export" style="background-color: #198754; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; margin-right: 10px;">📥 EXPORT EXCEL</a>
                        <a href="/logout" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">🔒 LOG OUT</a>
                    </div>
                </div>
                <table class="table table-bordered table-hover bg-white shadow-sm">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>Name</th><th>Email</th><th>Message</th><th>操作</th></tr>
                    </thead>
                    <tbody>
        """
        for row in rows:
            # 在表格最后加一个 AI 按钮
            html += f"""
            <tr>
                <td>{row[0]}</td>
                <td>{row[1]}</td>
                <td>{row[2]}</td>
                <td>{row[3]}</td>
                <td><a href="/ai_reply/{row[0]}" style="background-color: #6f42c1; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; font-size: 14px;">🤖 AI 写回复</a></td>
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