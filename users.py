from flask import Flask, request, abort, make_response, jsonify
import mysql.connector as mysql
import json
from settings import dbpwd
import bcrypt
import uuid
import mysql.connector, mysql.connector.pooling
from db import pool



def createUser():
    data = request.get_json()
    query = "INSERT INTO users (username, password) VALUES (%s, %s)"
    values = (data["username"], data["password"])

    connection = pool.get_connection()

    mycursor = connection.cursor()
    mycursor.execute(query, values)
    new_city_id = mycursor.lastrowid
    mycursor.close()
    pool.commit()
    return getUser(new_city_id)


def getUser(id):
    query = "SELECT * from users where id=%s"

    connection = pool.get_connection()
    mycursor = connection.cursor()
    mycursor.execute(query)
    myresult = mycursor.fetchall()
    mycursor.close()
    return myresult


def get_user_id_by_session():
    session_id = request.cookies.get("session_id")
    if not session_id:
        abort(401)
    query = "select user_id from sessions where session_id = %s"
    values = (session_id,)
    connection = pool.get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        record = cursor.fetchone()
        if not record:
            abort(401)
        else:
            return record[0]
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        connection.close()


def get_users_by_ids(ids):
    placeholders = ", ".join(["%s"] * len(ids))
    query = f"SELECT id, first_name, last_name FROM users WHERE id IN ({placeholders})"

    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, ids)
        records = cursor.fetchall()
        users_dict = {record[0]: record[1] + " " + record[2] for record in records}
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        connection.close()

    return users_dict


def get_users_full_name_by_id(id):
    query = "select first_name, last_name from users where id = %s"
    values = (id,)

    connection = pool.get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, values)
        record = cursor.fetchone()
        if record is None:
            return None
        full_name = record[0] + " " + record[1]
    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        connection.close()

    return full_name
