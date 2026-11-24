from flask import Flask, request, render_template
import pymysql

app = Flask(__name__)

# 企业级配置：数据库连接池配置
def get_db():
    return pymysql.connect(
        host='localhost', 
        user='appuser', 
        password='Bta3456789', 
        database='quarktwin_crm',
        charset='utf8mb4'
    )

# ==========================================
# 前台路由：展示页面
# ==========================================
@app.route('/')
def index():
    # 直接自动读取 templates 文件夹里的 index.html
    return render_template('index.html')

# ==========================================
# 后台路由：处理表单提交（带防弹衣）
# ==========================================
@app.route('/submit', methods=['POST'])
def submit():
    try:
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        
        db = get_db()
        cursor = db.cursor()
        
        # 🛡️ 护甲核心：参数化查询！
        # 绝对不能用 f"INSERT INTO ... {name}" 这种写法，那就是给黑客留后门！
        sql = "INSERT INTO customers (name, email, message) VALUES (%s, %s, %s)"
        
        # 把变量作为元组传给 execute，pymysql 会自动帮你处理特殊字符，彻底杜绝 SQL 注入
        cursor.execute(sql, (name, email, message))
        db.commit()
        db.close()
        
        # 成功页面我也做了一点美化
        return """
        <div style='text-align:center; margin-top:100px; font-family: sans-serif;'>
            <h2 style='color:#28a745;'>Thank you! Your inquiry has been received.</h2>
            <p>Our team will contact you shortly.</p>
            <a href='/' style='display:inline-block; margin-top:20px; padding:10px 20px; background:#0B1F3A; color:white; text-decoration:none; border-radius:5px;'>Go back to Home</a>
        </div>
        """
    except Exception as e:
        # 🛡️ 防崩溃机制：如果服务器或数据库出问题，不让老外看到乱码报错
        return "<h2>Oops! Something went wrong. Please try again later.</h2>", 500

# ==========================================
# 后台管理：查看询盘
# ==========================================
@app.route('/admin')
def admin():
    auth = request.authorization
    if not auth or auth.username != 'boss' or auth.password != '88888888':
        return '<h1>Access Denied</h1>', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}
        
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, message FROM customers ORDER BY id DESC")
        rows = cursor.fetchall()
        db.close()
        
        # 后台页面也帮你重写了，用了现代一点点的样式
        html = """
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
                    <a href="/logout" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🔒 LOG OUT</a>
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