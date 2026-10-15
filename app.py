from flask import Flask, request, jsonify
from flask_cors import CORS
import oracledb

# Oracle CLOB mətnlərinin (böyük mətnlərin) string kimi rahat oxunması üçün:
oracledb.defaults.fetch_lobs = False

app = Flask(__name__)
CORS(app)

# Verilənlər bazası qoşulma məlumatları
DB_USER = "nihadaliyev"
DB_PASSWORD = "19512009"
DB_DSN = "localhost:1521/XEPDB1"


def get_db_connection():
    return oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)


# --- 0. ANA SƏHİFƏ (Serverin işlədiyini yoxlamaq üçün) ---
@app.route('/')
def home():
    return "İmarət Blog API arxa planda uğurla işləyir!"


# --- 1. SIGN IN (Daxil ol) ---
@app.route('/login', methods=['POST'])
def login():
    user_email = request.form.get('email')
    user_password = request.form.get('password')

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT password FROM users WHERE email = :email", email=user_email)
        account = cursor.fetchone()

        cursor.close()
        connection.close()

        if account:
            db_password = account[0]
            if db_password == user_password:
                return jsonify({"status": "success", "message": "Uğurla daxil oldunuz!", "email": user_email})
            else:
                return jsonify({"status": "error", "message": "Şifrə yanlışdır!"})
        else:
            return jsonify({"status": "error", "message": "Belə bir email tapılmadı, zəhmət olmasa Sign Up edin."})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Baza xətası: {str(e)}"})


# --- 2. SIGN UP (Qeydiyyat) ---
@app.route('/signup', methods=['POST'])
def signup():
    user_email = request.form.get('email')
    user_password = request.form.get('password')

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT email FROM users WHERE email = :email", email=user_email)
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": "Bu email artıq qeydiyyatdan keçib!"})

        cursor.execute("""
                       INSERT INTO users (email, password)
                       VALUES (:email, :password)
                       """, email=user_email, password=user_password)

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({"status": "success", "message": "Uğurla qeydiyyatdan keçdiniz!"})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Baza xətası: {str(e)}"})


# --- 3. CREATE POST (Yeni Məqalə Əlavə Et) ---
@app.route('/create_post', methods=['POST'])
def create_post():
    title = request.form.get('title')
    content = request.form.get('content')
    author_email = request.form.get('author_email')

    if not title or not content or not author_email:
        return jsonify({"status": "error", "message": "Bütün xanaları doldurun!"})

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
                       INSERT INTO posts (title, content, author_email)
                       VALUES (:title, :content, :author_email)
                       """, title=title, content=content, author_email=author_email)

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({"status": "success", "message": "Məqaləniz uğurla paylaşıldı!"})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Baza xətası: {str(e)}"})


# --- 4. GET POSTS & COMMENTS (Məqalələri və Rəyləri Yüklə) ---
@app.route('/get_posts', methods=['GET'])
def get_posts():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Məqalələri son əlavə olunandan başlayaraq çəkirik
        cursor.execute("""
                       SELECT id, title, content, author_email, TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI')
                       FROM posts
                       ORDER BY id DESC
                       """)
        post_rows = cursor.fetchall()

        posts = []
        for p in post_rows:
            post_id = p[0]
            # Mətn LOB obyekti olarsa təhlükəsiz oxunması üçün
            content_text = p[2].read() if hasattr(p[2], 'read') else str(p[2]) if p[2] is not None else ""

            # Hər məqaləyə aid rəyləri çəkirik
            cursor.execute("""
                           SELECT author_email, content, TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI')
                           FROM comments
                           WHERE post_id = :post_id
                           ORDER BY id ASC
                           """, post_id=post_id)
            comment_rows = cursor.fetchall()

            comments = []
            for c in comment_rows:
                comment_text = c[1].read() if hasattr(c[1], 'read') else str(c[1]) if c[1] is not None else ""
                comments.append({
                    "author": c[0],
                    "content": comment_text,
                    "date": c[2]
                })

            posts.append({
                "id": post_id,
                "title": p[1],
                "content": content_text,
                "author": p[3],
                "date": p[4],
                "comments": comments
            })

        cursor.close()
        connection.close()

        return jsonify({"status": "success", "posts": posts})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Baza xətası: {str(e)}"})


# --- 5. ADD COMMENT (Yeni Rəy Əlavə Et) ---
@app.route('/add_comment', methods=['POST'])
def add_comment():
    post_id = request.form.get('post_id')
    content = request.form.get('content')
    author_email = request.form.get('author_email')

    if not post_id or not content or not author_email:
        return jsonify({"status": "error", "message": "Rəy boş ola bilməz!"})

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
                       INSERT INTO comments (post_id, author_email, content)
                       VALUES (:post_id, :author_email, :content)
                       """, post_id=post_id, author_email=author_email, content=content)

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({"status": "success", "message": "Rəyiniz əlavə olundu!"})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Baza xətası: {str(e)}"})


if __name__ == '__main__':
    app.run(debug=True)