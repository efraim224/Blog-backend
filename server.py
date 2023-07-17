from flask import Flask, request, abort, make_response, jsonify
from flask_cors import CORS, cross_origin
import mysql.connector as mysql
import json
from settings import dbpwd
import bcrypt
import uuid
import datetime

app = Flask(__name__, static_folder="./build", static_url_path="/")
CORS(
    app,
    supports_credentials=True,
    origins=["http://localhost:3000"],
    expose_headers="Set-Cookie",
)

db = mysql.connect(host="localhost", user="root", passwd="123456", database="blog")

@app.route("/")
def index():
    return app.send_static_file("index.html")



@app.route("/posts/", methods=["GET", "POST"])
def managePosts():
    if request.method == "GET":
        return getAllPosts()
    else:
        return createOrUpdatePost()


def createOrUpdatePost():
    data = request.get_json()
    if "postId" in data:
        return update_post(data["postId"])
    else:
        return createPost()


@app.route("/myposts", methods=["POST"])
def getMyPosts():
    # if request.method == 'OPTIONS':
    #     # This is a preflight request. Respond accordingly.
    #     return _build_cors_preflight_response()
    user_id = get_user_id()
    query = "SELECT id, title, content, status FROM posts WHERE writer_id=%s"
    values = (user_id,)
    mycursor = db.cursor()
    mycursor.execute(query, values)
    myresult = mycursor.fetchall()
    row_headers = [x[0] for x in mycursor.description]
    mycursor.close()
    json_data = []
    for result in myresult:
        json_data.append(dict(zip(row_headers, result)))
    res = make_response()
    res.response = json.dumps(json_data)
    return res


@app.route("/posts/<id>", methods=["GET"])
def getPost(id):
    query = "select id, title, content from posts where id = %s and status = %s"
    values = (id,"publish")
    cursor = db.cursor()
    cursor.execute(query, values)
    record = cursor.fetchone()
    row_headers = [x[0] for x in cursor.description]
    cursor.close()
    return json.dumps(dict(zip(row_headers, record)))


def getAllPosts():
    query = "SELECT writer_id, id, title, content, created_at FROM posts where status=%s"
    mycursor = db.cursor()
    mycursor.execute(query, ("publish",))
    myresult = mycursor.fetchall()
    ids = list(map(lambda x: str(x[0]), myresult))
    users_id_dict = get_users_by_ids(ids)
    row_headers = ["name"] + [x[0] for x in mycursor.description]
    mycursor.close()
    date_format = r'%d-%m-%Y'
    json_data = []
    for result in myresult:
        date = result[-1].strftime(date_format)
        name = users_id_dict[result[0]]
        json_data.append(dict(zip(row_headers, (name, *result[0:-1], date))))
    return json.dumps(json_data)


def createPost():
    data = request.get_json()
    query = "INSERT INTO posts (title, content, writer_id, status) VALUES (%s, %s, %s, %s)"
    values = (data["title"], data["content"], get_user_id(), 'publish')
    mycursor = db.cursor()
    mycursor.execute(query, values)
    new_city_id = mycursor.lastrowid
    mycursor.close()
    db.commit()
    return make_response(jsonify({"id": new_city_id}), 201)


def createUser():
    data = request.get_json()
    query = "INSERT INTO users (username, password) VALUES (%s, %s)"
    values = (data["username"], data["password"])
    mycursor = db.cursor()
    mycursor.execute(query, values)
    new_city_id = mycursor.lastrowid
    mycursor.close()
    db.commit()
    return getUser(new_city_id)


def getUser(id):
    query = "SELECT * from users where id=%s"
    mycursor = db.cursor()
    mycursor.execute(query)
    myresult = mycursor.fetchall()
    mycursor.close()
    return myresult

def get_user_id():
    session_id = request.cookies.get("session_id")
    if not session_id:
        abort(401)
    query = "select user_id from sessions where session_id = %s"
    values = (session_id,)
    cursor = db.cursor()
    cursor.execute(query, values)
    record = cursor.fetchone()
    cursor.close()
    if not record:
        abort(401)
    else:
        return record[0]


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if "username" not in data or "password" not in data:
        return jsonify({"error": "Missing username or password"}), 400

    query = "SELECT id, username, password FROM users WHERE username = %s"
    values = (data["username"],)

    try:
        with db.cursor() as cursor:
            cursor.execute(query, values)
            record = cursor.fetchone()

        if not record or bcrypt.hashpw(
            data["password"].encode("utf-8"), record[2].encode("utf-8")
        ) != record[2].encode("utf-8"):
            return jsonify({"error": "Unauthorized"}), 401

        query = "INSERT INTO sessions (user_id, session_id) VALUES (%s, %s)"
        session_id = str(uuid.uuid4())
        values = (record[0], session_id)

        with db.cursor() as cursor:
            cursor.execute(query, values)
            db.commit()

        resp = make_response(jsonify({"status": "Success"}), 200)
        resp.set_cookie(
            "session_id",
            value=session_id,
            max_age=None,
            expires=None,
            path="/",
            domain=None,
            secure=None,
            httponly=False,
            samesite=None,
        )
        return resp

    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500


@app.route("/signup", methods=["POST"])
def user_signup():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    first_name = data["firstName"]
    last_name = data["lastName"]
    # check if user exists
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    if cursor.fetchone() is not None:
        cursor.close()
        return jsonify({"message": "User already exists"}), 401  

    query = "insert into users (username, password, first_name, last_name) values (%s, %s, %s, %s)"
    bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(bytes, salt)
    values = (username, hash, first_name, last_name)
    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()
    cursor.close()
    return login()


@app.route("/delete_post/<id>", methods=["POST"])
def delete_post(id):
    user_id = get_user_id()
    query = "delete from posts where id = %s and writer_id = %s"
    values = (id, user_id)
    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()
    cursor.close()
    return jsonify({"status": "Success"}), 200


def update_post(id):
    user_id = get_user_id()
    data = request.get_json()
    query = "update posts set title = %s, content = %s where id = %s and writer_id = %s"
    values = (data["title"], data["content"], id, user_id)
    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()
    cursor.close()
    return jsonify({"status": "Success"}), 200


@app.route("/logout", methods=["POST"])
def logout():
    resp = make_response()
    resp.set_cookie(
        "session_id",
        value="",
        max_age=0,
        expires=0,
        path="/",
        domain=None,
        secure=None,
        httponly=False,
        samesite=None,
    )
    session_id = request.cookies.get("session_id")
    if not session_id:
        resp.data = json.dumps({"error": "Unauthorized"})
        resp.status_code = 401
        return resp

    try:
        cursor = db.cursor()
        query = "DELETE FROM sessions WHERE session_id = %s"
        cursor.execute(query, (session_id,))
        db.commit()
        if cursor.rowcount == 0:
            cursor.close()
            resp.data = json.dumps({"error": "Unauthorized"})
            resp.status_code = 401
            return resp

        cursor.close()

        resp.data = json.dumps({"status": "Success"})
        resp.status_code = 200
        return resp
    except Exception as e:
        if cursor:  # Check if cursor exists before attempting to close it
            cursor.close()

        resp.data = json.dumps({"error": "Internal Server Error"})
        resp.status_code = 500
        return resp


@app.route("/comments/<id>", methods=["GET"])
def get_comments_by_post_id(id):
    query = "SELECT user_id, content, created_at FROM comments where post_id= %s"
    values = (id,)
    cursor = db.cursor()
    cursor.execute(query, values)
    records = cursor.fetchall()
    row_headers = ["name", "content", "created_at"]
    cursor.close()
    json_data = []
    date_format = r'%d-%m-%Y %H:%M'


    for result in records:
        date = result[2].strftime(date_format)
        current_name = get_full_name_by_id(result[0])
        result = list(result)
        result[0] = current_name
        result[2] = date

        json_data.append(dict(zip(row_headers, result)))

    return json_data


@app.route("/comments/<post_id>", methods=["POST"])
def create_comment(post_id):
    query = "INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)"
    values = (post_id, get_user_id(), request.get_json()["commentData"])
    cursor = db.cursor()
    cursor.execute(query, values)
    new_comment_id = cursor.lastrowid
    cursor.close()
    db.commit()
    return make_response(jsonify({"status": "success"}), 201)


@app.route("/get_posts", methods=["POST"])
def get_posts():
    login = get_user_id()
    if not login:
        abort(401)
    query = "select * from posts where writer_id = %s"
    values = (login,)
    cursor = db.cursor()
    cursor.execute(query, values)
    myresult = cursor.fetchall()
    cursor.close()
    return myresult


@app.route("/update_status", methods=["POST"])
def update_post_status():
    data = request.get_json()
    post_id = data["post_id"]
    status = data["status"]
    if status not in ["publish", "draft"]:
        abort(400)
    query = "update posts set status = %s where id = %s"
    values = (status, post_id)
    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()
    cursor.close()
    return jsonify({"status": "Success"}), 200


@app.route("/save_post", methods=["POST"])
def save_post():
    data = request.get_json()
    session_id = request.cookies.get("session_id")
    if not session_id:
        abort(401)

    query = "select user_id from sessions where session_id = %s"
    values = (session_id,)
    cursor = db.cursor()
    cursor.execute(query, values)
    record = cursor.fetchone()
    if record is None:
        abort(401)

    user_id = record[0]
    post_id = str(uuid.uuid4())  # Generate a new UUID for the post

    # Assuming your data includes 'title' and 'content'
    save_post_user_id_to_post_id(user_id, post_id, data["title"], data["content"])
    cursor.close()
    return {"status": "success"}, 200


def save_post_user_id_to_post_id(user_id, post_id, title, content):
    query = "INSERT INTO saved_posts (post_id, user_id) VALUES(%s, %s)"
    values = (post_id, user_id)
    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()
    cursor.close()


def get_users_by_ids(ids):
    # Use Python's string formatting to generate the correct amount of placeholders (%s).
    placeholders = ", ".join(["%s"] * len(ids))
    query = f"SELECT id, first_name, last_name FROM users WHERE id IN ({placeholders})"
    cursor = db.cursor()
    cursor.execute(query, ids)
    records = cursor.fetchall()
    cursor.close()
    users_dict = {record[0]: record[1] + record[2] for record in records}
    return users_dict


def get_full_name_by_id(id):
    query = "select first_name, last_name from users where id = %s"
    values = (id,)
    cursor = db.cursor()
    cursor.execute(query, values)
    record = cursor.fetchone()
    cursor.close()
    return record[0] + " " + record[1]


if __name__ == "__main__":
    app.run()
