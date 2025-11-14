# database/db.py
import sqlite3
from tkinter import messagebox
from utils.security import hash_password, check_password
from datetime import datetime
import os

DB_NAME = os.path.join("data", "social_media.db")
ADMIN_USER = 'admin@dcccd.edu'

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        messagebox.showerror("Database Error", "Failed to connect to the database.")
        return None

def setup_database():
    conn = get_db_connection()
    if conn is None:
        return
    try:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            name TEXT,
            bio TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            grad_year TEXT,
            major TEXT,
            profile_picture TEXT
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY(email) REFERENCES users(email)
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            comment_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(post_id) REFERENCES posts(id),
            FOREIGN KEY(email) REFERENCES users(email)
        );

        CREATE TABLE IF NOT EXISTS post_reactions (
            post_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            reaction_type TEXT NOT NULL CHECK(reaction_type IN ('like','dislike')),
            reacted_at TEXT NOT NULL,
            PRIMARY KEY (post_id, email),
            FOREIGN KEY(post_id) REFERENCES posts(id),
            FOREIGN KEY(email) REFERENCES users(email)
        );
        """)
        admin_password_hash = hash_password('admin123')
        try:
            cursor.execute("INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
                           (ADMIN_USER, admin_password_hash, 'Administrator', 'admin'))
            conn.commit()
            print("Default admin user created.")
        except sqlite3.IntegrityError:
            pass

        conn.commit()
    except sqlite3.Error as e:
        print(f"Error during database setup: {e}")
    finally:
        conn.close()

# --- User CRUD and authentication helpers

def register_user_db(email, password, name):
    conn = get_db_connection()
    if conn is None:
        return False

    hashed_pw = hash_password(password)
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password_hash, name, bio, role) VALUES (?, ?, ?, ?, ?)",
                       (email, hashed_pw, name, f"New user {name}", 'user'))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        messagebox.showerror("Registration Failed", "A user with this email already exists.")
        return False
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"An error occurred during registration: {e}")
        return False
    finally:
        conn.close()

def verify_user_credentials(email, password):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if user and check_password(user['password_hash'], password):
            return dict(user)
        return None
    except sqlite3.Error as e:
        print(f"Error verifying credentials: {e}")
        return None
    finally:
        conn.close()

def get_all_users():
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT email, name, role, created_at FROM users")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error retrieving users: {e}")
        return []
    finally:
        conn.close()

def get_user_data(email):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, bio, role, created_at, grad_year, major, profile_picture FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except sqlite3.Error as e:
        print(f"Error retrieving user data: {e}")
        return None
    finally:
        conn.close()

def update_profile_picture_in_db(email: str, profile_picture_path: str) -> bool:
    """
    Stores the profile picture path for the given user email.
    Returns True on success, False on failure.
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET profile_picture = ? WHERE email = ?", (profile_picture_path, email))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating profile picture in DB: {e}")
        return False
    finally:
        conn.close()
def delete_user_db(email):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting user: {e}")
        messagebox.showerror("Database Error", f"An error occurred while deleting user: {e}")
        return False
    finally:
        conn.close()

# --- Posts and comments (original logic preserved)

def create_post(user_email, content):
    ts = datetime.now().strftime("%m/%d/%Y at %H:%M")
    conn = get_db_connection()
    if conn is None:
        return
    try:
        c = conn.cursor()
        c.execute("INSERT INTO posts (email, content, created_at) VALUES (?, ?, ?)", (user_email, content, ts))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating post: {e}")
    finally:
        conn.close()

def fetch_posts():
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        c = conn.cursor()
        c.execute("""
            SELECT p.id, p.email, u.name, p.content, p.created_at
            FROM posts p
            JOIN users u ON p.email = u.email
            ORDER BY p.id DESC
        """)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching posts: {e}")
        return []
    finally:
        conn.close()

def add_comment(post_id, user_email, comment_text):
    ts = datetime.now().strftime("%m/%d/%Y at %H:%M")
    conn = get_db_connection()
    if conn is None:
        return
    try:
        c = conn.cursor()
        c.execute("INSERT INTO comments (post_id, email, comment_text, created_at) VALUES (?, ?, ?, ?)",
                  (post_id, user_email, comment_text, ts))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error adding comment: {e}")
    finally:
        conn.close()

def update_database_schema():
    # columns already created in setup_database; function kept for compatibility
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()
def reset_password_db(email, new_password):
    """Handles password reset logic in database layer."""
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            return False, "No user found with that email."

        new_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (new_hash, email))
        conn.commit()
        return True, "Password updated successfully! Please log in again."

    except sqlite3.Error as e:
        return False, f"Database Error: {e}"
    finally:
        conn.close()