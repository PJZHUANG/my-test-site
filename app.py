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

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'top_secret_quarktwin_key_2026')

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', '') # 新增：视觉模型API

# 限制只能传图片
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        
        image_url = ""
        # 🛡️ 处理图片上传（带安全校验）
        if 'chip_image' in request.files:
            file = request.files['chip_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # 防止同名文件覆盖，加上时间戳
                import time
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
            
        cursor.execute("INSERT INTO customers (name, email, message, assigned_to, image_url) VALUES (%s, %s, %s, %s, %s)", 
                       (name, email, message, assigned_to, image_url))
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
            session['role'] = user[2]
            return redirect(url_for('admin'))
        return "<h3>Invalid credentials! <a href='/login'>Try again</a></h3>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/export')
def export_excel():
    if not session.get('logged_in') or session.get('role') != 'boss':
        return "Access Denied", 403
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, message, status, assigned_to FROM customers ORDER BY id DESC")
        rows = cursor.fetchall()
        db.close()
        df = pd.DataFrame(rows, columns=['ID', 'Name', 'Email', 'Message', 'Status', 'Assigned To'])
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
        cursor.execute("SELECT name, email, message, image_url FROM customers WHERE id = %s", (customer_id,))
        row = cursor.fetchone()
        db.close()
        
        if not row:
            return "Customer not found", 404
            
        customer_name, customer_email, customer_message, image_url = row
        
        image_context = ""
        # 🚀 如果有图片，先用视觉大模型分析
        if image_url:
            image_path = "/var/www/html" + image_url
            if os.path.exists(image_path):
                with open(image_path, "rb") as img_file:
                    base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                
                headers_vision = {"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"}
                data_vision = {
                    "model": "glm-4v",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "仔细看这张图片，如果里面是电子元器件或电路板，请提取出图中的芯片型号、品牌丝印。直接输出识别结果，不要废话。"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }]
                }
                # 调用智谱视觉模型
                res_vision = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers_vision, json=data_vision)
                vision_result = res_vision.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                if vision_result:
                    image_context = f"\n(注意：客户还上传了图片，AI识别图片中的芯片型号为：{vision_result})"

        # 然后让 DeepSeek 结合文字和图片识别结果写回复
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        prompt = f"你是一家深圳顶尖电子元器件供应商（QuarkTwin）的外贸销售总监。客户留言：'{customer_message}'。{image_context}。请据此写一封英文回复邮件，体现我们的专业度，并顺便给个大概报价区间。直接输出邮件正文。"
        data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
        
        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data)
        ai_content = response.json()['choices'][0]['message']['content']
        
        return f"""
        <div style="font-family: Arial; padding: 50px; max-width: 800px; margin: 0 auto;">
            <h3>AI 生成的回复草稿 (发给 {customer_email})：</h3>
            {f'<p><strong>客户上传的图片：</strong><br><img src="{image_url}" style="max-width: 300px; border-radius: 8px;"></p>' if image_url else ''}
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
        cursor.execute("UPDATE customers SET status = 'Contacted' WHERE id = %s", (customer_id,))
        db.commit()
        db.close()
        return redirect(url_for('admin'))
    except Exception as e:
        return f"<h2>Email Send Error: {str(e)}</h2>", 500

@app.route('/assign/<int:customer_id>/<username>')
def assign(customer_id, username):
    if not session.get('logged_in') or session.get('role') != 'boss':
        return "Only Boss can assign", 403
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE customers SET assigned_to = %s WHERE id = %s", (username, customer_id))
    db.commit()
    db.close()
    return redirect(url_for('admin'))

@app.route('/update_status/<int:customer_id>/<status>')
def update_status(customer_id, status):
    if not session.get('logged_in'):
        return "Access Denied", 403
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE customers SET status = %s WHERE id = %s", (status, customer_id))
    db.commit()
    db.close()
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    try:
        db = get_db()
        cursor = db.cursor()
        
        if session.get('role') == 'boss':
            cursor.execute("SELECT id, name, email, message, status, assigned_to, image_url FROM customers ORDER BY id DESC")
        else:
            cursor.execute("SELECT id, name, email, message, status, assigned_to, image_url FROM customers WHERE assigned_to = %s ORDER BY id DESC", (session.get('username'),))
            
        rows = cursor.fetchall()
        
        cursor.execute("SELECT status, COUNT(*) FROM customers GROUP BY status")
        status_counts = dict(cursor.fetchall())
        pending_count = status_counts.get('Pending', 0)
        contacted_count = status_counts.get('Contacted', 0)
        quoted_count = status_counts.get('Quoted', 0)
        closed_count = status_counts.get('Closed', 0)
        total_count = len(rows)
        
        cursor.execute("SELECT username FROM users WHERE role = 'sales'")
        sales_users = [u[0] for u in cursor.fetchall()]
        db.close()
        
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
                
                <div class="row mb-4">
                    <div class="col-md-2"><div class="card bg-primary text-white text-center p-3 shadow-sm"><h5>总询盘</h5><h2 class="mb-0">{total_count}</h2></div></div>
                    <div class="col-md-2"><div class="card bg-warning text-dark text-center p-3 shadow-sm"><h5>待处理</h5><h2 class="mb-0">{pending_count}</h2></div></div>
                    <div class="col-md-2"><div class="card bg-info text-dark text-center p-3 shadow-sm"><h5>已联系</h5><h2 class="mb-0">{contacted_count}</h2></div></div>
                    <div class="col-md-2"><div class="card bg-secondary text-white text-center p-3 shadow-sm"><h5>已报价</h5><h2 class="mb-0">{quoted_count}</h2></div></div>
                    <div class="col-md-2"><div class="card bg-success text-white text-center p-3 shadow-sm"><h5>已成交</h5><h2 class="mb-0">{closed_count}</h2></div></div>
                </div>

                <table class="table table-bordered table-hover bg-white shadow-sm align-middle">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>Name</th><th>Email</th><th>Message & Image</th><th>负责人</th><th>状态流转</th><th>AI 操作</th></tr>
                    </thead>
                    <tbody>
        """
        for row in rows:
            status = row[4]
            status_html = f"""
            <select onchange="window.location.href='/update_status/{row[0]}/'+this.value" class="form-select form-select-sm">
                <option value="Pending" {'selected' if status=='Pending' else ''}>Pending</option>
                <option value="Contacted" {'selected' if status=='Contacted' else ''}>Contacted</option>
                <option value="Quoted" {'selected' if status=='Quoted' else ''}>Quoted</option>
                <option value="Closed" {'selected' if status=='Closed' else ''}>Closed</option>
            </select>
            """
            
            assigned = row[5]
            if session.get('role') == 'boss':
                options = ''.join([f"<option value='{u}' {'selected' if assigned==u else ''}>{u}</option>" for u in sales_users])
                assigned_html = f"""
                <select onchange="window.location.href='/assign/{row[0]}/'+this.value" class="form-select form-select-sm">
                    <option value="Unassigned" {'selected' if assigned=='Unassigned' else ''}>Unassigned</option>
                    {options}
                </select>
                """
            else:
                assigned_html = f"<span class='badge bg-info text-dark'>{assigned}</span>"

            action_btn = f'<a href="/ai_reply/{row[0]}" style="background-color: #6f42c1; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-size: 14px; white-space: nowrap; display: inline-block;">🤖 AI 写回复</a>'
            
            # 如果有图片，就在留言下面显示一个小缩略图
            image_thumb = f'<br><a href="{row[6]}" target="_blank"><img src="{row[6]}" style="max-height: 50px; border-radius: 4px; margin-top: 5px;"></a>' if row[6] else ''
            
            html += f"""
            <tr>
                <td>{row[0]}</td>
                <td>{row[1]}</td>
                <td>{row[2]}</td>
                <td>{row[3]} {image_thumb}</td>
                <td>{assigned_html}</td>
                <td>{status_html}</td>
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