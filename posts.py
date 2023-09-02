from flask import Flask, request, abort, make_response, jsonify
import mysql.connector as mysql
import json
from settings import dbpwd
import bcrypt
import uuid
import mysql.connector, mysql.connector.pooling
from db import pool
from users import get_user_id_by_session, get_users_by_ids
from tags import create_tags


def update_post(id):
    user_id = get_user_id_by_session()
    data = request.get_json()
    query = "update posts set title = %s, content = %s where id = %s and writer_id = %s"
    values = (data["title"], data["content"], id, user_id)
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




def createOrUpdatePost():
    data = request.get_json()
    if "postId" in data:
        return update_post(data["postId"])
    else:
        return createPost()
    



def getAllPosts():
    query = (
        "SELECT writer_id, id, title, content, created_at FROM posts where status=%s"
    )
    values = ("publish",)

    connection = pool.get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        results = cursor.fetchall()
        ids = list(map(lambda x: str(x[0]), results))
        users_id_dict = get_users_by_ids(ids)
        row_headers = ["name"] + [x[0] for x in cursor.description]

        date_format = r"%d-%m-%Y"
        json_data = []
        for result in results:
            date = result[-1].strftime(date_format)
            name = users_id_dict[result[0]]
            json_data.append(dict(zip(row_headers, (name, *result[0:-1], date))))

    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500

    finally:
        cursor.close()
        connection.close()

    return jsonify(json_data)


def createPost():
    data = request.get_json()
    query = (
        "INSERT INTO posts (title, content, writer_id, status) VALUES (%s, %s, %s, %s)"
    )
    values = (data["title"], data["content"], get_user_id_by_session(), "publish")
    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, values)
        connection.commit()
        new_post_id = cursor.lastrowid
        create_tags(data["tags"], new_post_id)
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        connection.close()

    return make_response(jsonify({"id": new_post_id}), 201)


def save_post_user_id_to_post_id(user_id, post_id, title, content):
    query = "INSERT INTO saved_posts (post_id, user_id) VALUES(%s, %s)"
    values = (post_id, user_id)
    cursor = pool.get_connection()
    cursor.execute(query, values)
    pool.commit()
    cursor.close()