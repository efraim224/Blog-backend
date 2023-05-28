from flask import Flask, request
from flask_cors import CORS, cross_origin
import mysql.connector as mysql
import json
from settings import dbpwd


app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

db = mysql.connect(
	host = "localhost",
	user = "root",
	passwd = "123456",
	database = "blog")

@app.route('/posts/', methods=['GET', 'POST'])
@cross_origin()
def managePosts():
	if request.method == 'GET':
		return getAllPosts()
	else:
		return createPost()



@app.route("/posts/:id")
def getPost():
	query = "select id, title, content from posts where id = %s"
	values = (id)
	cursor = db.cursor()
	cursor.execute(query, values)
	record = cursor.fetchone()
	cursor.close()	
	row_headers=[x[0] for x in cursor.description]

	return json.dumps(dict(zip(row_headers, record)))


def getAllPosts():
	query = "SELECT * FROM posts"
	mycursor = db.cursor()
	mycursor.execute(query)
	myresult = mycursor.fetchall()
	mycursor.close()
	row_headers=[x[0] for x in mycursor.description]
	json_data=[]
	for result in myresult:
		json_data.append(dict(zip(row_headers,result)))
	return json.dumps(json_data)


def createPost():
	data = request.get_json()
	query = "INSERT INTO posts (title, content) VALUES (%s, %s)"
	values = (data['title'], data['content'])
	mycursor = db.cursor()
	mycursor.execute(query, values)
	mycursor.close()
	db.commit()
	new_city_id = mycursor.lastrowid
	mycursor.close()
	return getPost(new_city_id)



def createUser():
	data = request.get_json()
	query = "INSERT INTO users (username, password) VALUES (%s, %s)"
	values = (data['username'], data['password'])
	mycursor = db.cursor()
	mycursor.execute(query, values)
	mycursor.close()
	db.commit()
	new_city_id = mycursor.lastrowid
	mycursor.close()
	return getUser(new_city_id)

def getUser(id):
	query = "SELECT * from users where id=%s"
	mycursor = db.cursor()
	mycursor.execute(query)
	myresult = mycursor.fetchall()
	mycursor.close()
	return myresult

if __name__ == "__main__":
	app.run()