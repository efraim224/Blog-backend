from db import pool


def prepare_tags(tag_line: str):
    tags = tag_line.split(" ")
    tags = [tag.strip() for tag in tags]
    tags = [tag for tag in tags if tag != ""]
    tags = [tag for tag in tags if len(tag) <= 20]
    # tags = [tag[1:] for tag in tags if tag[0] == "#"]
    tags = [tag[1:] if tag[0] == "#" else tag for tag in tags]
    tags = [{"rank": i, "content": tag} for i, tag in enumerate(tags)]
    return tags
    


# Create multiple tags with a list of dictionaries containing postId, rank, and content
def create_tags(tags, postId):
    connection = pool.get_connection()
    tags = prepare_tags(tags)
    try:
        cursor = connection.cursor()
        sql = "INSERT INTO `tags` (`postId`, `rank`, `content`) VALUES (%s, %s, %s)"
        
        # Prepare the list of records to insert
        tag_values = [(postId, tag['rank'], tag['content']) for tag in tags]
        
        cursor.executemany(sql, tag_values)
        connection.commit()

    except mysql.connector.Error as err:
        print("Error: {}".format(err))
        connection.rollback()

    finally:
        connection.close()

# 1. Query all tags for a given postId, sorted by rank
def query_tags_by_postId(postId):
    connection = pool.get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT `id`, `postId`, `rank`, `content` FROM `tags` WHERE `postId` = %s ORDER BY `rank` ASC"
        cursor.execute(sql, (postId,))
        result = cursor.fetchall()
        return result
    finally:
        connection.close()

# 2. Create a tag with postId, rank, and content
def create_tag(postId, rank, content):
    connection = pool.get_connection()
    try:
        cursor = connection.cursor()
        sql = "INSERT INTO `tags` (`postId`, `rank`, `content`) VALUES (%s, %s, %s)"
        cursor.execute(sql, (postId, rank, content))
        connection.commit()
    finally:
        connection.close()

# 3. Delete a tag by tagId
def delete_tag(tagId: int):
    connection = pool.get_connection()
    try:
        cursor = connection.cursor()
        sql = "DELETE FROM `tags` WHERE `id` = %s"
        cursor.execute(sql, (tagId,))
        connection.commit()
    finally:
        connection.close()

def get_post_ids_by_tag_content(content: str):
    connection = pool.get_connection()
    try:
        cursor = connection.cursor()
        sql = "SELECT `postId` FROM `tags` WHERE `content` = %s"
        cursor.execute(sql, (content.strip(),))
        result = cursor.fetchall()
        return result
    finally:
        connection.close()


def get_tags_by_post_ids(post_ids):
    connection = pool.get_connection()
    try:
        cursor = connection.cursor()
        placeholders = ", ".join(["%s"] * len(post_ids))
        sql = f"SELECT `postId`, `content` FROM `tags` WHERE `postId` IN ({placeholders})"
        cursor.execute(sql, post_ids)
        result = cursor.fetchall()
        return result
    finally:
        connection.close()


def get_tags_by_post_ids_dict(post_ids):
    connection = pool.get_connection()
    post_to_tags = {}
    try:
        cursor = connection.cursor()
        placeholders = ", ".join(["%s"] * len(post_ids))
        sql = f"SELECT `postId`, `content` FROM `tags` WHERE `postId` IN ({placeholders}) ORDER BY `postId`"
        cursor.execute(sql, post_ids)
        result = cursor.fetchall()

        for postId, content in result:
            if postId in post_to_tags:
                post_to_tags[postId].append(content)
            else:
                post_to_tags[postId] = [content]

        return post_to_tags
    finally:
        connection.close()