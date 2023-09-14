from flask import Flask, request, abort, make_response, jsonify
from flask_cors import CORS, cross_origin
import mysql.connector as mysql
import json
from settings import dbpwd
import bcrypt
import uuid
import datetime
import os
import mysql.connector, mysql.connector.pooling
from dotenv import load_dotenv
from tags import *
from users import *
from posts import *


app = Flask(__name__, static_folder="./build", static_url_path="/")

CORS(
    app,
    supports_credentials=True,
    origins=["http://localhost:3000"],
    expose_headers="Set-Cookie",
)

load_dotenv()

pool = mysql.connector.pooling.MySQLConnectionPool(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    database=os.getenv("DB_NAME"),
    buffered=True,
    pool_size=3,
    pool_name="mypool",
)



# @app.route("/")
# def index():
#     return app.send_static_file("index.html")


# @app.route('/', defaults={'path': ''})
# @app.route('/<path:path>')
# def catch_all(path):
#     return app.send_static_file("index.html")

@app.route("/search/<search_term>", methods=["GET"])
def search(search_term):
    search_type = request.args.get('type', 'all')  # default to 'all' if no 'type' param is given

    if search_type == 'tag':
        return get_posts_by_tag(search_term)

    elif search_type == 'title':
        return get_search_posts_by_title(search_term)

    elif not search_type or search_type == 'all':
        return get_posts_by_tag_and_title(search_term)

    else:
        return jsonify({"error": "Invalid type parameter"}), 400

def get_posts_by_tag_and_title(search_term):
    # Search posts by tag
    posts_by_tag = []
    posts_by_tag = get_posts_by_tag(search_term)

    # Search posts by title
    posts_by_title = get_search_posts_by_title(search_term)

    # Combine the two lists, eliminating duplicates based on post IDs
    combined_posts = {}
    for post in posts_by_tag + posts_by_title:
        post_id = post.get("id", None)
        if post_id is not None:
            combined_posts[post_id] = post

    return jsonify(list(combined_posts.values()))

# @app.route("/search/<search_term>", methods=["GET"])
# def get_search_results(search_term):
#     if search_term[0] == "#":
#         return get_post_by_tag(search_term)
#     else:
#         return get_search_posts_by_title(search_term)
    
def get_posts_by_tag(search_term):
    post_ids = get_post_ids_by_tag_content(search_term)
    post_ids = [x[0] for x in post_ids]
    post_ids = list(set(post_ids))
    posts = getPostsByIds(post_ids)
    return posts

def get_search_posts_by_title(search_term):
    post_query = "SELECT id, title, content, created_at FROM posts where status=%s and title like %s"
    like = "%" + search_term + "%"
    post_values = ("publish", like)

    connection = pool.get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(post_query, post_values)
        results = cursor.fetchall()
        row_headers = [x[0] for x in cursor.description]

        json_data = [dict(zip(row_headers, result)) for result in results]

    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500

    finally:
        cursor.close()
        connection.close()

    return json_data


@app.route("/comments/<id>", methods=["GET"])
def get_comments_by_post_id(id):
    query = "SELECT user_id, content, created_at FROM comments where post_id= %s"
    values = (id,)
    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, values)
        records = cursor.fetchall()
        row_headers = ["name", "content", "created_at"]
        json_data = []
        date_format = r"%d-%m-%Y %H:%M"
        for result in records:
            date = result[2].strftime(date_format)
            current_name = get_users_full_name_by_id(result[0])
            result = list(result)
            result[0] = current_name
            result[2] = date
            json_data.append(dict(zip(row_headers, result)))
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        connection.close()

    return jsonify(json_data), 200


@app.route("/comments/<post_id>", methods=["POST"])
def create_comment(post_id):
    query = "INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)"
    values = (post_id, get_user_id_by_session(), request.get_json()["commentData"])
    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, values)
        new_comment_id = cursor.lastrowid
        connection.commit()
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        connection.close()
    
    return make_response(jsonify({"status": "success"}), 201)

# region tags

@app.route('/tags/<int:postId>', methods=['GET'])
def get_tags(postId):
    tags = query_tags_by_postId(postId)
    return jsonify(tags)

@app.route('/tags', methods=['POST'])
def get_all_tags_by_post_ids():
    data = request.get_json()
    post_ids = data["post_ids"]
    tags = get_tags_by_post_ids_dict(post_ids)
    return jsonify(tags)

@app.route('/tags/<int:postId>', methods=['DELETE'])
def delete(tagId):
    delete_tag(tagId)
    return jsonify({'status': 'Tag deleted'})

# endregion



# region posts

@app.route("/delete_post/<id>", methods=["POST"])
def delete_post(id):
    user_id = get_user_id_by_session()
    query = "delete from posts where id = %s and writer_id = %s"
    values = (id, user_id)
    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, values)
        connection.commit()
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        connection.close()

    return jsonify({"status": "Success"}), 200


@app.route("/posts", methods=["GET", "POST"])
def posts_redirect():
    return managePosts()


@app.route("/posts/", methods=["GET", "POST"])
def managePosts():
    if request.method == "GET":
        return getAllPosts()
    else:
        return createOrUpdatePost()



@app.route("/posts/<id>", methods=["GET"])
def getPost(id):
    query = "select id, title, content from posts where id = %s and status = %s"
    values = (id, "publish")

    connection = pool.get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        record = cursor.fetchone()

        if record is None:
            return jsonify({"error": "No post found with the provided id"}), 404

        row_headers = [x[0] for x in cursor.description]
        result = dict(zip(row_headers, record))

    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500

    finally:
        cursor.close()
        connection.close()

    return jsonify(result)


@app.route("/myposts")
def getMyPosts_redirect():
    return getMyPosts()


@app.route("/myposts/", methods=["POST"])
def getMyPosts():
    user_id = get_user_id_by_session()
    query = "SELECT id, title, content, status FROM posts WHERE writer_id=%s"
    values = (user_id,)

    connection = pool.get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        results = cursor.fetchall()
        row_headers = [x[0] for x in cursor.description]

        json_data = [dict(zip(row_headers, result)) for result in results]

    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500

    finally:
        cursor.close()
        connection.close()

    return jsonify(json_data)


@app.route("/update_status", methods=["POST"])
def update_post_status():
    data = request.get_json()
    post_id = data["post_id"]
    status = data["status"]
    if status not in ["publish", "draft"]:
        abort(400)
    query = "update posts set status = %s where id = %s"
    values = (status, post_id)
    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, values)
        connection.commit()
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        connection.close()

    return jsonify({"status": "Success"}), 200



# endregion

# region user profile


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

    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        query = "DELETE FROM sessions WHERE session_id = %s"
        cursor.execute(query, (session_id,))
        connection.commit()
        if cursor.rowcount == 0:
            resp.data = json.dumps({"error": "Unauthorized"})
            resp.status_code = 401
        else:
            resp.data = json.dumps({"status": "Success"})
            resp.status_code = 200
    except Exception as e:
        resp.data = json.dumps({"error": "Internal Server Error"})
        resp.status_code = 500
    finally:
        cursor.close()
        connection.close()

    return resp


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if "username" not in data or "password" not in data:
        return jsonify({"error": "Missing username or password"}), 400

    query = "SELECT id, username, password FROM users WHERE username = %s"
    values = (data["username"],)

    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, values)
        record = cursor.fetchone()

        if not record or bcrypt.hashpw(
            data["password"].encode("utf-8"), record[2].encode("utf-8")
        ) != record[2].encode("utf-8"):
            return jsonify({"error": "Unauthorized"}), 401

        query = "INSERT INTO sessions (user_id, session_id) VALUES (%s, %s)"
        session_id = str(uuid.uuid4())
        values = (record[0], session_id)

        cursor.execute(query, values)
        connection.commit()

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

    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500
    except Exception as e:
        print("Exception: {}".format(e))
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route("/signup", methods=["POST"])
def user_signup():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    first_name = data["firstName"]
    last_name = data["lastName"]
    # check if user exists
    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        if cursor.fetchone() is not None:
            return jsonify({"message": "User already exists"}), 401

        query = "insert into users (username, password, first_name, last_name) values (%s, %s, %s, %s)"
        bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(bytes, salt)
        values = (username, hash, first_name, last_name)

        cursor.execute(query, values)
        connection.commit()
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        connection.close()

    return login()

# endregion

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
