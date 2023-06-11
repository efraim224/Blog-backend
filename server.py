from flask import Flask, request, abort, make_response, jsonify
from flask_cors import CORS, cross_origin
import mysql.connector as mysql
import json
from settings import dbpwd
# from db import db 
# from users import *
import bcrypt
import uuid

app = Flask(__name__)
CORS(app,supports_credentials=True,origins=["http://localhost:3000"], expose_headers='Set-Cookie')
# CORS(app, supports_credentials=True)

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


# @app.route('/login', methods=['POST'])
# def login():
# 	data = request.get_json()
# 	print(data)
# 	query = "select id, username, password from users where username = %s"
# 	values = (data['username'], )
# 	cursor = db.cursor()
# 	cursor.execute(query, values)
# 	record = cursor.fetchone()
# 	cursor.close()
	
# 	if not record:
# 		abort(401)


# 	user_id = record[0]
# 	hashed_pwd = record[2].encode('utf-8')

# 	encoded_pass = data['password'].encode('utf-8')

# 	if bcrypt.hashpw(encoded_pass, hashed_pwd) != hashed_pwd:
# 		abort(401)

# 	query = "insert into sessions (user_id, session_id) values (%s, %s)"
# 	session_id = str(uuid.uuid4())
# 	values = (record[0], session_id)
# 	cursor = db.cursor()
# 	cursor.execute(query, values)
# 	db.commit()
# 	cursor.close()
# 	resp = make_response()
# 	# resp.set_cookie("session_id", session_id)
# 	resp.set_cookie("session_id", value=session_id, max_age=None, expires=None, path='/', domain=None, secure=None, httponly=False, samesite=None)
# 	resp.status_code = 200
# 	return resp

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


# @app.route('/logout', methods=['POST'])
# def logout():
# 	try:
# 		session_id = request.cookies.get("session_id")
# 		if not session_id:
# 			abort(401)
# 		query = "delete from sessions where session_id = %s"
# 		values = (session_id,)
# 		cursor = db.cursor()
# 		cursor.execute(query, values)
# 		cursor.close()
# 		if cursor.rowcount == 0:
# 			abort(401)

# 		resp = make_response()
# 		resp.status_code = 200
# 		return resp
# 	except:
		
# 		resp = make_response()
# 		resp.status_code = 500
# 		return resp


@app.route('/logout', methods=['POST'])
def logout():
    session_id = request.cookies.get("session_id")
    if not session_id:
        return make_response(jsonify({'error': 'Unauthorized'}), 401)

    try:
        cursor = db.cursor()
        query = "DELETE FROM sessions WHERE session_id = %s"
        cursor.execute(query, (session_id,))
        db.commit()
        if cursor.rowcount == 0:
            cursor.close()
            return make_response(jsonify({'error': 'Unauthorized'}), 401)
        cursor.close()
        return jsonify({'status': 'Success'}), 200
    except Exception as e:
        if cursor:  # Check if cursor exists before attempting to close it
            cursor.close()
        return make_response(jsonify({'error': 'Internal Server Error'}), 500)

if __name__ == "__main__":
	app.run()