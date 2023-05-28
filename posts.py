
class posts:

    def getAllPosts():
        query = "SELECT * FROM posts"
        mycursor.execute(query)
        myresult = mycursor.fetchall()
        return myresult

    def createPost(title, content):
        query = "INSERT INTO posts (title, content) VALUES (%s, %s)"
        vals = (title, content)
        mycursor.execute(query, vals)
