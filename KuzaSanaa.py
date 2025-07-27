import sqlite3

def create_database_and_table():
    try:
        # Connect to SQLite database (it will create if it doesn't exist)
        connection = sqlite3.connect('KuzaSanaa.db')
        cursor = connection.cursor()

        # Create User table with Password column added
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS User (
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT NOT NULL UNIQUE,
            Email TEXT NOT NULL UNIQUE,
            Password TEXT NOT NULL,
            Role TEXT NOT NULL,
            Bio TEXT
        )
        """)

        # Create Content table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Content (
            ContentID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID INTEGER,
            FilePath TEXT NOT NULL,
            UploadDate DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (UserID) REFERENCES User(UserID)
        )
        """)

        # Create Comment table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Comment (
            CommentID INTEGER PRIMARY KEY AUTOINCREMENT,
            ContentID INTEGER,
            UserID INTEGER,
            CommentText TEXT NOT NULL,
            CommentDate DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ContentID) REFERENCES Content(ContentID),
            FOREIGN KEY (UserID) REFERENCES User(UserID)
        )
        """)

        connection.commit()
        print("Tables 'User', 'Content', and 'Comment' created successfully.")

    except sqlite3.Error as e:
        print(f"Error: {e}")

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("SQLite connection is closed.")

if __name__ == "__main__":
    create_database_and_table()
