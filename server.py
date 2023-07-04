from flask import Flask, request, abort, make_response, jsonify
from flask_cors import CORS, cross_origin
import mysql.connector as mysql
import json
from settings import dbpwd
import bcrypt
import uuid

app = Flask(__name__)
CORS(app,supports_credentials=True,origins=["http://localhost:3000"], expose_headers='Set-Cookie')

db = mysql.connect(
	host = "localhost",
	user = "root",
	passwd = "123456",
	database = "blog")



@app.route('/posts/', methods=['GET', 'POST'])
def managePosts():
	if request.method == 'GET':
		return getAllPosts()
	else:
		return createPost()



@app.route("/posts/<id>",  methods=['GET'])
def getPost(id):
	query = "select id, title, content from posts where id = %s"
	values = (id,)
	cursor = db.cursor()
	cursor.execute(query, values)
	record = cursor.fetchone()
	row_headers=[x[0] for x in cursor.description]
	cursor.close()	
	return json.dumps(dict(zip(row_headers, record)))


def getAllPosts():
	query = "SELECT id, title, content FROM posts"
	mycursor = db.cursor()
	mycursor.execute(query)
	myresult = mycursor.fetchall()
	row_headers=[x[0] for x in mycursor.description]
	mycursor.close()
	json_data=[]
	for result in myresult:
		json_data.append(dict(zip(row_headers,result)))
	res = make_response()
	res.response = json.dumps(json_data)
	return res


def createPost():
	data = request.get_json()
	query = "INSERT INTO posts (title, content) VALUES (%s, %s)"
	values = (data['title'], data['content'])
	mycursor = db.cursor()
	mycursor.execute(query, values)
	new_city_id = mycursor.lastrowid
	mycursor.close()
	db.commit()
	return getPost(new_city_id)



def createUser():
	data = request.get_json()
	query = "INSERT INTO users (username, password) VALUES (%s, %s)"
	values = (data['username'], data['password'])
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


@app.route('/check_login', methods=['POST'])
def check_login():
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


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing username or password'}), 400

    query = "SELECT id, username, password FROM users WHERE username = %s"
    values = (data['username'], )

    try:
        with db.cursor() as cursor:
            cursor.execute(query, values)
            record = cursor.fetchone()
	    
        if not record or bcrypt.hashpw(data['password'].encode('utf-8'), record[2].encode('utf-8')) != record[2].encode('utf-8'):
            return jsonify({'error': 'Unauthorized'}), 401

        query = "INSERT INTO sessions (user_id, session_id) VALUES (%s, %s)"
        session_id = str(uuid.uuid4())
        values = (record[0], session_id)

        with db.cursor() as cursor:
            cursor.execute(query, values)
            db.commit()

        resp = make_response(jsonify({'status': 'Success'}), 200)
        resp.set_cookie("session_id", value=session_id, max_age=None, expires=None, path='/', domain=None, secure=None, httponly=False, samesite=None)
        return resp

    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500


@app.route('/signup', methods=['POST'])
def user_signup():
	data = request.get_json()
	username = data['username']
	password = data['password']
	query = "insert into users (username, password) values (%s, %s)"
	bytes = password.encode('utf-8')
	salt = bcrypt.gensalt()
	hash = bcrypt.hashpw(bytes, salt)
	values = (username, hash)
	cursor = db.cursor()
	cursor.execute(query, values)
	db.commit()
	cursor.close()
	return login()



@app.route('/logout', methods=['POST'])
def logout():
    resp = make_response()
    resp.set_cookie("session_id", value='', max_age=0, expires=0, path='/', domain=None, secure=None, httponly=False, samesite=None)
    session_id = request.cookies.get("session_id")
    if not session_id:
        resp.response = jsonify({'error': 'Unauthorized'}), 401
        return resp

    try:
        cursor = db.cursor()
        query = "DELETE FROM sessions WHERE session_id = %s"
        cursor.execute(query, (session_id,))
        db.commit()
        if cursor.rowcount == 0:
            cursor.close()
            resp.response = jsonify({'error': 'Unauthorized'}), 401
            return resp
        cursor.close()
        resp.response = jsonify({'status': 'Success'}), 200
        return resp
    except Exception as e:
        if cursor:  # Check if cursor exists before attempting to close it
            cursor.close()
        resp.response = jsonify({'error': 'Internal Server Error'}), 500
        return resp



@app.route('/save_post', methods=['POST'])
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
    save_post_user_id_to_post_id(user_id, post_id, data['title'], data['content'])
    cursor.close()
    return {"status": "success"}, 200

def save_post_user_id_to_post_id(user_id, post_id, title, content):
    query = "INSERT INTO saved_posts (post_id, user_id) VALUES(%s, %s)"
    values = (post_id, user_id)
    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()
    cursor.close()


if __name__ == "__main__":
	app.run()