from flask import Flask, request, render_template_string, redirect
import pymysql
from functools import wraps

app = Flask(__name__)

def get_db():
    return pymysql.connect(host='localhost', user='appuser', password='Bta3456789', database='quarktwin_crm')

# 前台主页
@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>QuarkTwin</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f4f6f9; font-family: 'Arial', sans-serif; }
            .hero { background: linear-gradient(135deg, #0B1F3A 0%, #1A467A 100%); color: white; padding: 100px 0; text-align: center; }
            .card-form { background: white; border-radius: 12px; box-shadow: 0 10px 20px rgba(0,0,0,0.1); padding: 40px; margin-top: -50px; }
        </style>
    </head>
    <body>
        <div class="hero">
            <h1 class="display-4 fw-bold">QuarkTwin</h1>
            <p class="lead mt-3">Your Trusted Partner in Electronic Components</p>
        </div>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-6 card-form">
                    <h3 class="mb-4 text-center">Get a Quote</h3>
                    <form action="/submit" method="POST">
                        <div class="mb-3">
                            <label class="form-label">Name</label>
                            <input type="text" class="form-control" name="name" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-control" name="email" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Message</label>
                            <textarea class="form-control" name="message" rows="4" required></textarea>
                        </div>
                        <button type="submit" class="btn btn-primary w-100 py-2">Send Inquiry</button>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# 提交表单
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    
    db = get_db()
    cursor = db.cursor()
    sql = "INSERT INTO customers (name, email, message) VALUES (%s, %s, %s)"
    cursor.execute(sql, (name, email, message))
    db.commit()
    db.close()
    
    return "<div style='text-align:center; margin-top:100px;'><h2 style='color:green;'>BOSS VINCENT IS IN THE OFFICE! (From Company PC) IS AWESOME!</h2><p>Your inquiry has been received.</p><a href='/'>Home</a></div>"

# 后台管理（必须账号：boss，密码：88888888）
@app.route('/admin')
def admin():
    # 极简密码锁
    auth = request.authorization
    if not auth or auth.username != 'boss' or auth.password != '88888888':
        return '<h1>Access Denied</h1>', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}
        
    db = get_db()
    cursor = db.cursor()
    # 顺便查一下时间
    cursor.execute("SELECT id, name, email, message, status, created_at FROM customers")
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
            <h2 class="mb-4">Customer Inquiries</h2>
            <table class="table table-bordered table-hover bg-white">
                <thead class="table-dark">
                    <tr>
                        <th>ID</th>
                        <th>Date</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Message</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    """
    for row in rows:
        # 给没处理的加个红色标签，已处理的加绿色
        badge = 'bg-warning text-dark' if row[4] == 'Pending' else 'bg-success'
        html += f"""
        <tr>
            <td>{row[0]}</td>
            <td>{str(row[5])[:16]}</td>
            <td>{row[1]}</td>
            <td>{row[2]}</td>
            <td>{row[3]}</td>
            <td><span class="badge {badge}">{row[4]}</span></td>
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

if __name__ == '__main__':
    app.run()