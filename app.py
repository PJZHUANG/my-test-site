from flask import Flask, request, render_template, redirect, url_for, session, make_response
import pymysql
import os
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'top_secret_quarktwin_key_2026')

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

# ==========================================
# 🚀 新增：一键导出 Excel 路由
# ==========================================
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
        
        # 用 pandas 把数据库数据转换成 Excel
        df = pd.DataFrame(rows, columns=['ID', 'Name', 'Email', 'Message'])
        output = BytesIO()
        # 用 xlsxwriter 引擎导出带格式的 Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Inquiries')
        
        output.seek(0)
        
        # 生成下载响应
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=customer_inquiries.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    except Exception as e:
        return f"<h2>Export Error: {str(e)}</h2>", 500

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
                        <a href="/export" style="background-color: #198754; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; margin-right: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">📥 EXPORT EXCEL</a>
                        <a href="/logout" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🔒 LOG OUT</a>
                    </div>
                </div>
                <table class="table table-bordered table-hover bg-white shadow-sm">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>Name</th><th>Email</th><th>Message</th></tr>
                    </thead>
                    <tbody>
        """
        for row in rows:
            html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>"
            
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