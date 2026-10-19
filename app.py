from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
import json
import urllib.request
import urllib.error
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = "educarenix_secret_key"


# =========================================================
# LOCAL AI CONFIGURATION (OLLAMA)
# =========================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    conn = sqlite3.connect("educarenix.db")

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin():

    return "admin_id" in session


# =========================================================
# BADGE HELPER
# =========================================================

def unlock_badge(user_id, badge_name):

    conn = get_db()

    badge = conn.execute("""
        SELECT *
        FROM badges
        WHERE name = ?
    """, (badge_name,)).fetchone()

    if badge is None:

        conn.close()

        return

    existing = conn.execute("""
        SELECT *
        FROM user_badges
        WHERE user_id = ?
        AND badge_id = ?
    """, (
        user_id,
        badge["id"]
    )).fetchone()

    if existing is None:

        conn.execute("""
            INSERT INTO user_badges
            (
                user_id,
                badge_id
            )
            VALUES (?, ?)
        """, (
            user_id,
            badge["id"]
        ))

        conn.commit()

    conn.close()


# =========================================================
# CHECK BADGES
# =========================================================

def check_badges(user_id):

    conn = get_db()

    completed_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lesson_progress
        WHERE user_id = ?
        AND completed = 1
    """, (user_id,)).fetchone()[0]

    user = conn.execute("""
        SELECT points
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    quiz_master = conn.execute("""
        SELECT id
        FROM quiz_attempts
        WHERE user_id = ?
        AND percentage >= 80
        LIMIT 1
    """, (user_id,)).fetchone()

    conn.close()

    if completed_lessons >= 1:

        unlock_badge(
            user_id,
            "First Step"
        )

    if completed_lessons >= 2:

        unlock_badge(
            user_id,
            "Skill Explorer"
        )

    if user and user["points"] >= 100:

        unlock_badge(
            user_id,
            "Learning Star"
        )

    if quiz_master:

        unlock_badge(
            user_id,
            "Quiz Master"
        )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    cursor = conn.cursor()

    # =====================================================
    # EXAMS
    # =====================================================

    cursor.execute("""
 CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        duration INTEGER DEFAULT 30,
        pass_percentage INTEGER DEFAULT 40,
        course_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id)
    )
""")
        # =====================================================
        # USERS
        # =====================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT DEFAULT 'student',

            points INTEGER DEFAULT 0
        )
    """)

        # =====================================================
        # ADMIN ACCOUNT
        # =====================================================
    admin_email = "admin@educarenix.com"
    admin_password = "EduCareNix@Admin123"

    existing_admin = cursor.execute("""
        SELECT id
        FROM users
        WHERE email = ?
    """, (admin_email,)).fetchone()

    cursor = conn.cursor()
    if existing_admin is None:
        
            cursor.execute("""
            INSERT INTO users
            (
                name,
                email,
                password,
                role,
                points
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
                "EduCareNix Admin",
                admin_email,
                generate_password_hash(admin_password),
                "admin",
                0))
    else:
         cursor.execute("""
            UPDATE users
            SET
                name = ?,
                password = ?,
                role = 'admin'
            WHERE email = ?
        """, (
                "EduCareNix Admin",
                generate_password_hash(admin_password),
                admin_email
            ))

        # =====================================================
        # COURSES
        # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            description TEXT,

            level TEXT
        )
    """)

        # =====================================================
        # LESSONS
        # =====================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            course_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            content TEXT,

            lesson_order INTEGER DEFAULT 1,

            FOREIGN KEY (course_id)
            REFERENCES courses(id)
        )
 """)
        # =====================================================
        # QUIZZES
        # =====================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            course_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            description TEXT,

            FOREIGN KEY (course_id)
            REFERENCES courses(id)
        )
    """)

        # =====================================================
        # QUESTIONS
        # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            quiz_id INTEGER NOT NULL,

            question TEXT NOT NULL,

            option_a TEXT NOT NULL,

            option_b TEXT NOT NULL,

            option_c TEXT NOT NULL,

            option_d TEXT NOT NULL,

            correct_answer TEXT NOT NULL,

            FOREIGN KEY (quiz_id)
            REFERENCES quizzes(id)
        )
    """)

        # =====================================================
        # CERTIFICATES
        # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificates (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            certificate_id TEXT UNIQUE NOT NULL,

            user_id INTEGER NOT NULL,

            course_id INTEGER NOT NULL,

            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, course_id),

            FOREIGN KEY (user_id)
            REFERENCES users(id),

            FOREIGN KEY (course_id)
            REFERENCES courses(id)
        )
    """)

        # =====================================================
        # BADGES
        # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS badges (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            description TEXT
        )
    """)

        # =====================================================
        # USER BADGES
        # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_badges (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            badge_id INTEGER NOT NULL,

            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, badge_id),

            FOREIGN KEY (user_id)
            REFERENCES users(id),

            FOREIGN KEY (badge_id)
            REFERENCES badges(id)
        )
    """)

        # =====================================================
        # LESSON PROGRESS
        # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lesson_progress (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            lesson_id INTEGER NOT NULL,

            completed INTEGER DEFAULT 0,

            UNIQUE(user_id, lesson_id),

            FOREIGN KEY (user_id)
            REFERENCES users(id),

            FOREIGN KEY (lesson_id)
            REFERENCES lessons(id)
        )
    """)

        # =====================================================
        # QUIZ ATTEMPTS
        # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            quiz_id INTEGER NOT NULL,

            score INTEGER DEFAULT 0,

            total INTEGER DEFAULT 0,

            percentage INTEGER DEFAULT 0,

            points INTEGER DEFAULT 0,

            FOREIGN KEY (user_id)
            REFERENCES users(id),

            FOREIGN KEY (quiz_id)
            REFERENCES quizzes(id)
        )
    """)

        # =====================================================
        # STUDENT REVIEWS
        # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            course_id INTEGER NOT NULL,

            rating INTEGER NOT NULL,

            review TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, course_id),

            FOREIGN KEY (user_id)
            REFERENCES users(id),

            FOREIGN KEY (course_id)
            REFERENCES courses(id)
        )
    """)

    conn.commit()

        # =====================================================
        # SAMPLE DATA
        # =====================================================

    course_count = cursor.execute("""
        SELECT COUNT(*)
        FROM courses
    """).fetchone()[0]

    if course_count == 0:

            # =================================================
            # PYTHON COURSE
            # =================================================

            cursor.execute("""
            INSERT INTO courses
            (
                title,
                description,
                level
            )
            VALUES (?, ?, ?)
        """, (
                "Python Programming",
                "Learn Python programming from basic to advanced concepts.",
                "Beginner"
            ))

            python_id = cursor.lastrowid

            # =================================================
            # C COURSE
            # =================================================

            cursor.execute("""
            INSERT INTO courses
            (
                title,
                description,
                level
            )
            VALUES (?, ?, ?)
        """, (
                "C Programming",
                "Learn C programming, functions, arrays, pointers and more.",
                "Beginner"
            ))

            c_id = cursor.lastrowid

            # =================================================
            # WEB DEVELOPMENT
            # =================================================

            cursor.execute("""
            INSERT INTO courses
            (
                title,
                description,
                level
            )
            VALUES (?, ?, ?)
        """, (
                "Web Development",
                "Learn HTML, CSS and JavaScript to build websites.",
                "Beginner"
            ))

            web_id = cursor.lastrowid

            # =================================================
            # PYTHON LESSONS
            # =================================================

            python_lessons = [

                (
                    python_id,
                    "Introduction to Python",
                    """Python is a high-level programming language.

It is easy to learn and widely used in:

• Web Development
• Data Science
• Artificial Intelligence
• Automation
• Machine Learning

In this lesson you will learn the basics of Python.""",
                    1
                ),

                (
                    python_id,
                    "Variables and Data Types",
                    """A variable is used to store data.

Example:

name = "Asraf"
age = 20

Common Python data types are:

• int
• float
• string
• list
• tuple
• dictionary
• boolean""",
                    2
                ),

                (
                    python_id,
                    "Conditional Statements",
                    """Conditional statements are used to make decisions.

Example:

age = 18

if age >= 18:
    print("Adult")
else:
    print("Minor")""",
                    3
                )
            ]

            cursor.executemany("""
            INSERT INTO lessons
            (
                course_id,
                title,
                content,
                lesson_order
            )
            VALUES (?, ?, ?, ?)
        """, python_lessons)

            # =================================================
            # C LESSONS
            # =================================================

            c_lessons = [

                (
                    c_id,
                    "Introduction to C",
                    """C is a general-purpose programming language.

C is widely used for:

• System Programming
• Embedded Systems
• Operating Systems
• Data Structures""",
                    1
                ),

                (
                    c_id,
                    "Variables in C",
                    """Variables store data in memory.

Example:

int age = 20;

char grade = 'A';

float marks = 85.5;""",
                    2
                )
            ]

            cursor.executemany("""
            INSERT INTO lessons
            (
                course_id,
                title,
                content,
                lesson_order
            )
            VALUES (?, ?, ?, ?)
        """, c_lessons)

            # =================================================
            # WEB LESSONS
            # =================================================

            web_lessons = [

                (
                    web_id,
                    "HTML Basics",
                    """HTML stands for HyperText Markup Language.

HTML is used to create the structure of a webpage.

Example:

<h1>Hello World</h1>

<p>Welcome to EduCareNix.</p>""",
                    1
                ),

                (
                    web_id,
                    "CSS Basics",
                    """CSS stands for Cascading Style Sheets.

CSS is used to style HTML pages.

Example:

body {
    background: white;
    color: black;
}""",
                    2
                )
            ]

            cursor.executemany("""
            INSERT INTO lessons
            (
                course_id,
                title,
                content,
                lesson_order
            )
            VALUES (?, ?, ?, ?)
        """, web_lessons)

            # =================================================
            # PYTHON QUIZ
            # =================================================

            cursor.execute("""
            INSERT INTO quizzes
            (
                course_id,
                title,
                description
            )
            VALUES (?, ?, ?)
        """, (
                python_id,
                "Python Basics Quiz",
                "Test your basic Python programming knowledge."
            ))

            python_quiz_id = cursor.lastrowid

            questions = [

                (
                    python_quiz_id,
                    "Which keyword is used to define a function in Python?",
                    "function",
                    "def",
                    "define",
                    "fun",
                    "B"
                ),

                (
                    python_quiz_id,
                    "Which of the following is a Python data type?",
                    "integer",
                    "string",
                    "float",
                    "All of the above",
                    "D"
                ),

                (
                    python_quiz_id,
                    "Which symbol is used for comments in Python?",
                    "//",
                    "/* */",
                    "#",
                    "<!-- -->",
                    "C"
                ),

                (
                    python_quiz_id,
                    "Which function is used to display output in Python?",
                    "display()",
                    "show()",
                    "print()",
                    "output()",
                    "C"
                ),

                (
                    python_quiz_id,
                    "Which operator is used for exponentiation in Python?",
                    "^",
                    "**",
                    "//",
                    "%%",
                    "B"
                )
            ]

            cursor.executemany("""
            INSERT INTO questions
            (
                quiz_id,
                question,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, questions)

    conn.commit()

        # =====================================================
        # BADGE DATA
        # =====================================================
    badge_count = cursor.execute("""
        SELECT COUNT(*)
        FROM badges
    """).fetchone()[0]

    if badge_count == 0:

            badges = [

                (
                    "First Step",
                    "Complete your first lesson."
                ),

                (
                    "Quiz Master",
                    "Score 80% or more in a quiz."
                ),

                (
                    "Learning Star",
                    "Earn 100 or more learning points."
                ),

                (
                    "Skill Explorer",
                    "Complete two or more lessons."
                )
            ]

            cursor.executemany("""
            INSERT INTO badges
            (
                name,
                description
            )
            VALUES (?, ?)
        """, badges)

            conn.commit()

    else:

            badge_updates = [

                (
                    "Complete your first lesson.",
                    "First Step"
                ),

                (
                    "Score 80% or more in a quiz.",
                    "Quiz Master"
                ),

                (
                    "Earn 100 or more learning points.",
                    "Learning Star"
                ),

                (
                    "Complete two or more lessons.",
                    "Skill Explorer"
                )
            ]

            for description, name in badge_updates:

                cursor.execute("""
                UPDATE badges
                SET description = ?
                WHERE name = ?
            """, (
                    description,
                    name
                ))

                conn.commit()

    conn.close()


# =========================================================
# HOME
# =========================================================

init_db()
@app.route("/")
def homepage():

    conn = get_db()

    total_courses = conn.execute("""
        SELECT COUNT(*)
        FROM courses
    """).fetchone()[0]

    total_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lessons
    """).fetchone()[0]

    total_quizzes = conn.execute("""
        SELECT COUNT(*)
        FROM quizzes
    """).fetchone()[0]

    total_badges = conn.execute("""
        SELECT COUNT(*)
        FROM badges
    """).fetchone()[0]

    total_students = conn.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'student'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        total_courses=total_courses,
        total_lessons=total_lessons,
        total_quizzes=total_quizzes,
        total_badges=total_badges,
        total_students=total_students
    )


# =========================================================
# OLD HOME ENDPOINT
# =========================================================

@app.route("/home")
def home():

    return redirect(
        url_for("homepage")
    )


# =========================================================
# SIGN UP
# =========================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            return "All fields are required!", 400

        hashed_password = generate_password_hash(
            password
        )

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO users
                (
                    name,
                    email,
                    password
                )
                VALUES (?, ?, ?)
            """, (
                name,
                email,
                hashed_password
            ))

            conn.commit()

            conn.close()

            return redirect(
                url_for("login")
            )

        except sqlite3.IntegrityError:

            conn.close()

            return "Email already registered!", 400

    return render_template(
        "signup.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session.clear()

            if user["role"] == "admin":

                session["admin_id"] = user["id"]

                session["admin_name"] = user["name"]

                return redirect(
                    url_for("admin_dashboard")
                )

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["role"] = user["role"]

            return redirect(
                url_for("dashboard")
            )

        return "Invalid email or password!", 401

    return render_template(
        "login.html"
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    courses_data = conn.execute("""
        SELECT *
        FROM courses
        ORDER BY id DESC
    """).fetchall()

    quiz_count = conn.execute("""
        SELECT COUNT(*)
        FROM quizzes
    """).fetchone()[0]

    total_courses = conn.execute("""
        SELECT COUNT(*)
        FROM courses
    """).fetchone()[0]

    popular_courses = courses_data[:3]

    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        courses=courses_data,
        popular_courses=popular_courses,
        quiz_count=quiz_count,
        total_courses=total_courses,
        total_quizzes=quiz_count
    )


# =========================================================
# COURSES
# =========================================================

@app.route("/courses")
def courses():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    courses_data = conn.execute("""
        SELECT
            courses.*,
            COALESCE(AVG(reviews.rating), 0) AS average_rating,
            COUNT(reviews.id) AS review_count

        FROM courses

        LEFT JOIN reviews
        ON courses.id = reviews.course_id

        GROUP BY courses.id

        ORDER BY courses.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "courses.html",
        courses=courses_data
    )


# =========================================================
# COURSE DETAILS
# =========================================================

@app.route("/course/<int:course_id>")
def course_details(course_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    # -----------------------------------------------------
    # GET COURSE
    # -----------------------------------------------------

    course = conn.execute("""
        SELECT
            courses.*,
            COALESCE(AVG(reviews.rating), 0) AS average_rating,
            COUNT(reviews.id) AS review_count

        FROM courses

        LEFT JOIN reviews
        ON courses.id = reviews.course_id

        WHERE courses.id = ?

        GROUP BY courses.id
    """, (
        course_id,
    )).fetchone()

    if course is None:

        conn.close()

        return "Course not found!", 404

    # -----------------------------------------------------
    # GET LESSONS
    # -----------------------------------------------------

    lessons = conn.execute("""
        SELECT *
        FROM lessons
        WHERE course_id = ?
        ORDER BY lesson_order ASC
    """, (
        course_id,
    )).fetchall()

    # -----------------------------------------------------
    # GET QUIZZES
    # -----------------------------------------------------

    quizzes_data = conn.execute("""
        SELECT *
        FROM quizzes
        WHERE course_id = ?
        ORDER BY id ASC
    """, (
        course_id,
    )).fetchall()

    # -----------------------------------------------------
    # CHECK CERTIFICATE
    # -----------------------------------------------------

    certificate = conn.execute("""
        SELECT *
        FROM certificates
        WHERE user_id = ?
        AND course_id = ?
    """, (
        user_id,
        course_id
    )).fetchone()

    # -----------------------------------------------------
    # COURSE PROGRESS
    # -----------------------------------------------------

    total_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lessons
        WHERE course_id = ?
    """, (
        course_id,
    )).fetchone()[0]

    completed_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lesson_progress
        JOIN lessons
        ON lesson_progress.lesson_id = lessons.id
        WHERE lesson_progress.user_id = ?
        AND lesson_progress.completed = 1
        AND lessons.course_id = ?
    """, (
        user_id,
        course_id
    )).fetchone()[0]

    # -----------------------------------------------------
    # USER'S OWN REVIEW
    # -----------------------------------------------------

    user_review = conn.execute("""
        SELECT *
        FROM reviews
        WHERE user_id = ?
        AND course_id = ?
    """, (
        user_id,
        course_id
    )).fetchone()

    # -----------------------------------------------------
    # ALL REVIEWS
    # -----------------------------------------------------

    reviews_data = conn.execute("""
        SELECT
            reviews.*,
            users.name AS student_name

        FROM reviews

        JOIN users
        ON reviews.user_id = users.id

        WHERE reviews.course_id = ?

        ORDER BY reviews.created_at DESC
    """, (
        course_id,
    )).fetchall()

    # -----------------------------------------------------
    # RATING BREAKDOWN
    # -----------------------------------------------------

    rating_breakdown = {}

    for rating_value in range(5, 0, -1):

        rating_count = conn.execute("""
            SELECT COUNT(*)
            FROM reviews
            WHERE course_id = ?
            AND rating = ?
        """, (
            course_id,
            rating_value
        )).fetchone()[0]

        rating_breakdown[rating_value] = rating_count

    # -----------------------------------------------------
    # CALCULATE PERCENTAGE
    # -----------------------------------------------------

    if total_lessons > 0:

        progress_percentage = int(
            (completed_lessons / total_lessons) * 100
        )

    else:

        progress_percentage = 0

    conn.close()

    return render_template(
        "course_details.html",

        course=course,

        lessons=lessons,

        quizzes=quizzes_data,

        certificate=certificate,

        total_lessons=total_lessons,

        completed_lessons=completed_lessons,

        progress_percentage=progress_percentage,

        reviews=reviews_data,

        user_review=user_review,

        rating_breakdown=rating_breakdown
    )


# =========================================================
# SUBMIT REVIEW
# =========================================================

@app.route(
    "/course/<int:course_id>/review",
    methods=["POST"]
)
def submit_review(course_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    rating = request.form.get(
        "rating",
        ""
    ).strip()

    review_text = request.form.get(
        "review",
        ""
    ).strip()

    # -----------------------------------------------------
    # VALIDATE RATING
    # -----------------------------------------------------

    try:

        rating = int(rating)

    except ValueError:

        return redirect(
            url_for(
                "course_details",
                course_id=course_id
            )
        )

    if rating < 1 or rating > 5:

        return redirect(
            url_for(
                "course_details",
                course_id=course_id
            )
        )

    # -----------------------------------------------------
    # VALIDATE REVIEW
    # -----------------------------------------------------

    if not review_text:

        return redirect(
            url_for(
                "course_details",
                course_id=course_id
            )
        )

    if len(review_text) > 1000:

        review_text = review_text[:1000]

    conn = get_db()

    # -----------------------------------------------------
    # CHECK COURSE
    # -----------------------------------------------------

    course = conn.execute("""
        SELECT id
        FROM courses
        WHERE id = ?
    """, (
        course_id,
    )).fetchone()

    if course is None:

        conn.close()

        return "Course not found!", 404

    # -----------------------------------------------------
    # CHECK EXISTING REVIEW
    # -----------------------------------------------------

    existing_review = conn.execute("""
        SELECT id
        FROM reviews
        WHERE user_id = ?
        AND course_id = ?
    """, (
        user_id,
        course_id
    )).fetchone()

    if existing_review:

        conn.execute("""
            UPDATE reviews
            SET
                rating = ?,
                review = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            AND course_id = ?
        """, (
            rating,
            review_text,
            user_id,
            course_id
        ))

    else:

        conn.execute("""
            INSERT INTO reviews
            (
                user_id,
                course_id,
                rating,
                review
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            course_id,
            rating,
            review_text
        ))

    conn.commit()

    conn.close()

    return redirect(
        url_for(
            "course_details",
            course_id=course_id
        )
    )


# =========================================================
# EDIT REVIEW
# =========================================================

@app.route(
    "/review/edit/<int:review_id>",
    methods=["GET", "POST"]
)
def edit_review(review_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    review = conn.execute("""
        SELECT
            reviews.*,
            courses.title AS course_title

        FROM reviews

        JOIN courses
        ON reviews.course_id = courses.id

        WHERE reviews.id = ?

        AND reviews.user_id = ?
    """, (
        review_id,
        user_id
    )).fetchone()

    if review is None:

        conn.close()

        return "Review not found!", 404

    if request.method == "POST":

        rating = request.form.get(
            "rating",
            ""
        ).strip()

        review_text = request.form.get(
            "review",
            ""
        ).strip()

        try:

            rating = int(rating)

        except ValueError:

            conn.close()

            return render_template(
                "edit_review.html",
                review=review,
                error="Please select a valid rating."
            )

        if rating < 1 or rating > 5:

            conn.close()

            return render_template(
                "edit_review.html",
                review=review,
                error="Rating must be between 1 and 5."
            )

        if not review_text:

            conn.close()

            return render_template(
                "edit_review.html",
                review=review,
                error="Review cannot be empty."
            )

        if len(review_text) > 1000:

            review_text = review_text[:1000]

        conn.execute("""
            UPDATE reviews
            SET
                rating = ?,
                review = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            AND user_id = ?
        """, (
            rating,
            review_text,
            review_id,
            user_id
        ))

        conn.commit()

        course_id = review["course_id"]

        conn.close()

        return redirect(
            url_for(
                "course_details",
                course_id=course_id
            )
        )

    conn.close()

    return render_template(
        "edit_review.html",
        review=review
    )


# =========================================================
# DELETE REVIEW
# =========================================================

@app.route(
    "/review/delete/<int:review_id>",
    methods=["POST", "GET"]
)
def delete_review(review_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    review = conn.execute("""
        SELECT course_id
        FROM reviews
        WHERE id = ?
        AND user_id = ?
    """, (
        review_id,
        user_id
    )).fetchone()

    if review is None:

        conn.close()

        return "Review not found!", 404

    course_id = review["course_id"]

    conn.execute("""
        DELETE FROM reviews
        WHERE id = ?
        AND user_id = ?
    """, (
        review_id,
        user_id
    ))

    conn.commit()

    conn.close()

    return redirect(
        url_for(
            "course_details",
            course_id=course_id
        )
    )


# =========================================================
# LESSON
# =========================================================

@app.route("/lesson/<int:lesson_id>")
def lesson(lesson_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    lesson_data = conn.execute("""
        SELECT
            lessons.*,
            courses.title AS course_title
        FROM lessons
        JOIN courses
        ON lessons.course_id = courses.id
        WHERE lessons.id = ?
    """, (
        lesson_id,
    )).fetchone()

    completed = conn.execute("""
        SELECT *
        FROM lesson_progress
        WHERE user_id = ?
        AND lesson_id = ?
        AND completed = 1
    """, (
        user_id,
        lesson_id
    )).fetchone()

    conn.close()

    if lesson_data is None:

        return "Lesson not found!", 404

    return render_template(
        "lesson.html",
        lesson=lesson_data,
        completed=completed is not None
    )


# =========================================================
# MARK LESSON COMPLETE + COURSE CERTIFICATE
# =========================================================

@app.route(
    "/lesson/<int:lesson_id>/complete",
    methods=["POST"]
)
def complete_lesson(lesson_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    lesson_data = conn.execute("""
        SELECT
            lessons.id,
            lessons.course_id,
            courses.title AS course_title
        FROM lessons
        JOIN courses
        ON lessons.course_id = courses.id
        WHERE lessons.id = ?
    """, (
        lesson_id,
    )).fetchone()

    if lesson_data is None:

        conn.close()

        return "Lesson not found!", 404

    course_id = lesson_data["course_id"]

    existing = conn.execute("""
        SELECT *
        FROM lesson_progress
        WHERE user_id = ?
        AND lesson_id = ?
    """, (
        user_id,
        lesson_id
    )).fetchone()

    if existing:

        conn.execute("""
            UPDATE lesson_progress
            SET completed = 1
            WHERE user_id = ?
            AND lesson_id = ?
        """, (
            user_id,
            lesson_id
        ))

    else:

        conn.execute("""
            INSERT INTO lesson_progress
            (
                user_id,
                lesson_id,
                completed
            )
            VALUES (?, ?, 1)
        """, (
            user_id,
            lesson_id
        ))

    conn.commit()

    total_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lessons
        WHERE course_id = ?
    """, (
        course_id,
    )).fetchone()[0]

    completed_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lesson_progress
        JOIN lessons
        ON lesson_progress.lesson_id = lessons.id
        WHERE lesson_progress.user_id = ?
        AND lesson_progress.completed = 1
        AND lessons.course_id = ?
    """, (
        user_id,
        course_id
    )).fetchone()[0]

    if total_lessons > 0 and completed_lessons >= total_lessons:

        existing_certificate = conn.execute("""
            SELECT *
            FROM certificates
            WHERE user_id = ?
            AND course_id = ?
        """, (
            user_id,
            course_id
        )).fetchone()

        if existing_certificate is None:

            certificate_id = (
                "ECN-"
                + os.urandom(6).hex().upper()
            )

            conn.execute("""
                INSERT INTO certificates
                (
                    certificate_id,
                    user_id,
                    course_id
                )
                VALUES (?, ?, ?)
            """, (
                certificate_id,
                user_id,
                course_id
            ))

            conn.commit()

    conn.close()

    check_badges(user_id)

    return redirect(
        url_for(
            "lesson",
            lesson_id=lesson_id
        )
    )


# =========================================================
# QUIZZES
# =========================================================

@app.route("/quizzes")
def quizzes():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    quiz_list = conn.execute("""
        SELECT
            quizzes.*,
            courses.title AS course_title
        FROM quizzes
        JOIN courses
        ON quizzes.course_id = courses.id
        ORDER BY quizzes.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "quizzes.html",
        quizzes=quiz_list
    )


# =========================================================
# START QUIZ
# =========================================================

@app.route("/quiz/<int:quiz_id>")
def start_quiz(quiz_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    quiz = conn.execute("""
        SELECT
            quizzes.*,
            courses.title AS course_title
        FROM quizzes
        JOIN courses
        ON quizzes.course_id = courses.id
        WHERE quizzes.id = ?
    """, (
        quiz_id,
    )).fetchone()

    questions_data = conn.execute("""
        SELECT *
        FROM questions
        WHERE quiz_id = ?
        ORDER BY id ASC
    """, (
        quiz_id,
    )).fetchall()

    conn.close()

    if quiz is None:

        return "Quiz not found!", 404

    return render_template(
        "quiz.html",
        quiz=quiz,
        questions=questions_data
    )


# =========================================================
# SUBMIT QUIZ
# =========================================================

@app.route(
    "/quiz/<int:quiz_id>/submit",
    methods=["POST"]
)
def submit_quiz(quiz_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    quiz = conn.execute("""
        SELECT *
        FROM quizzes
        WHERE id = ?
    """, (
        quiz_id,
    )).fetchone()

    if quiz is None:

        conn.close()

        return "Quiz not found!", 404

    questions_data = conn.execute("""
        SELECT *
        FROM questions
        WHERE quiz_id = ?
        ORDER BY id ASC
    """, (
        quiz_id,
    )).fetchall()

    score = 0

    total = len(questions_data)

    for question in questions_data:

        user_answer = request.form.get(
            f"question_{question['id']}"
        )

        if user_answer == question["correct_answer"]:

            score += 1

    if total > 0:

        percentage = int(
            (score / total) * 100
        )

    else:

        percentage = 0

    points = score * 10

    conn.execute("""
        UPDATE users
        SET points = points + ?
        WHERE id = ?
    """, (
        points,
        user_id
    ))

    conn.execute("""
        INSERT INTO quiz_attempts
        (
            user_id,
            quiz_id,
            score,
            total,
            percentage,
            points
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        quiz_id,
        score,
        total,
        percentage,
        points
    ))

    conn.commit()

    conn.close()

    check_badges(user_id)

    return render_template(
        "quiz_result.html",
        score=score,
        total=total,
        percentage=percentage,
        points=points
    )


# =========================================================
# STUDENT BADGES
# =========================================================

@app.route("/badges")
def badges():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    check_badges(user_id)

    conn = get_db()

    badges_data = conn.execute("""
        SELECT
            badges.id,
            badges.name,
            badges.description,

            CASE
                WHEN user_badges.id IS NOT NULL
                THEN 1
                ELSE 0
            END AS earned

        FROM badges

        LEFT JOIN user_badges

        ON badges.id = user_badges.badge_id

        AND user_badges.user_id = ?

        ORDER BY badges.id ASC
    """, (
        user_id,
    )).fetchall()

    conn.close()

    return render_template(
        "badges.html",
        badges=badges_data
    )


# =========================================================
# MY PROGRESS
# =========================================================

@app.route("/progress")
def progress():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    check_badges(user_id)

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    total_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lessons
    """).fetchone()[0]

    completed_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lesson_progress
        WHERE user_id = ?
        AND completed = 1
    """, (
        user_id,
    )).fetchone()[0]

    quizzes_attempted = conn.execute("""
        SELECT COUNT(*)
        FROM quiz_attempts
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()[0]

    average_result = conn.execute("""
        SELECT AVG(percentage)
        FROM quiz_attempts
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()[0]

    average_quiz = (
        int(average_result)
        if average_result is not None
        else 0
    )

    if total_lessons > 0:

        lesson_progress = int(
            (completed_lessons / total_lessons) * 100
        )

    else:

        lesson_progress = 0

    course_list = conn.execute("""
        SELECT *
        FROM courses
        ORDER BY id DESC
    """).fetchall()

    course_progress = []

    for course in course_list:

        total = conn.execute("""
            SELECT COUNT(*)
            FROM lessons
            WHERE course_id = ?
        """, (
            course["id"],
        )).fetchone()[0]

        completed = conn.execute("""
            SELECT COUNT(*)
            FROM lesson_progress
            JOIN lessons
            ON lesson_progress.lesson_id = lessons.id
            WHERE lesson_progress.user_id = ?
            AND lesson_progress.completed = 1
            AND lessons.course_id = ?
        """, (
            user_id,
            course["id"]
        )).fetchone()[0]

        if total > 0:

            percentage = int(
                (completed / total) * 100
            )

        else:

            percentage = 0

        course_progress.append({
            "title": course["title"],
            "total": total,
            "completed": completed,
            "percentage": percentage
        })

    conn.close()

    return render_template(
        "progress.html",
        user=user,
        total_lessons=total_lessons,
        completed_lessons=completed_lessons,
        quizzes_attempted=quizzes_attempted,
        average_quiz=average_quiz,
        lesson_progress=lesson_progress,
        course_progress=course_progress
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():
    

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    badge_count = conn.execute("""
        SELECT COUNT(*)
        FROM user_badges
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()[0]

    completed_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lesson_progress
        WHERE user_id = ?
        AND completed = 1
    """, (
        user_id,
    )).fetchone()[0]

    review_count = conn.execute("""
        SELECT COUNT(*)
        FROM reviews
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()[0]

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        badge_count=badge_count,
        completed_lessons=completed_lessons,
        review_count=review_count
    )
# ============================================================
# PROFILE PHOTO UPLOAD
# ============================================================

@app.route("/profile/upload-photo", methods=["POST"])
def upload_profile_photo():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Make sure upload folder exists
    upload_folder = os.path.join(
        app.root_path,
        "static",
        "uploads",
        "profiles"
    )

    os.makedirs(upload_folder, exist_ok=True)

    # Get uploaded file
    file = request.files.get("profile_photo")

    if not file or file.filename == "":
        return redirect(url_for("profile"))

    # Allowed extensions
    allowed_extensions = {
        "jpg",
        "jpeg",
        "png",
        "webp"
    }

    filename = file.filename

    if "." not in filename:
        return redirect(url_for("profile"))

    extension = filename.rsplit(".", 1)[1].lower()

    if extension not in allowed_extensions:
        return redirect(url_for("profile"))

    # Maximum file size = 5 MB
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > 5 * 1024 * 1024:
        return redirect(url_for("profile"))

    # Create database column if it doesn't exist
    conn = get_db()

    columns = conn.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    if "profile_photo" not in column_names:

        conn.execute(
            "ALTER TABLE users ADD COLUMN profile_photo TEXT"
        )

        conn.commit()

    # Get old photo
    user = conn.execute(
        """
        SELECT profile_photo
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    old_photo = None

    if user and user["profile_photo"]:
        old_photo = user["profile_photo"]

    # Create unique filename
    import uuid

    new_filename = (
        str(user_id)
        + "_"
        + uuid.uuid4().hex
        + "."
        + extension
    )

    file_path = os.path.join(
        upload_folder,
        new_filename
    )

    # Save new photo
    file.save(file_path)

    # Save relative path in database
    photo_path = (
        "uploads/profiles/"
        + new_filename
    )

    conn.execute(
        """
        UPDATE users
        SET profile_photo = ?
        WHERE id = ?
        """,
        (photo_path, user_id)
    )

    conn.commit()
    conn.close()

    # Delete previous photo
    if old_photo:

        old_file_path = os.path.join(
            app.root_path,
            "static",
            old_photo
        )

        if (
            os.path.exists(old_file_path)
            and os.path.isfile(old_file_path)
        ):
            try:
                os.remove(old_file_path)
            except Exception:
                pass

    return redirect(url_for("profile"))

# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        admin = conn.execute("""
            SELECT *
            FROM users
            WHERE email = ?
            AND role = 'admin'
        """, (
            email,
        )).fetchone()

        conn.close()

        if admin and check_password_hash(
            admin["password"],
            password
        ):

            session.clear()

            session["admin_id"] = admin["id"]

            session["admin_name"] = admin["name"]

            return redirect(
                url_for("admin_dashboard")
            )

        return render_template(
            "admin_login.html",
            error="Invalid admin email or password."
        )

    return render_template(
        "admin_login.html"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    total_users = conn.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'student'
    """).fetchone()[0]

    total_courses = conn.execute("""
        SELECT COUNT(*)
        FROM courses
    """).fetchone()[0]

    total_lessons = conn.execute("""
        SELECT COUNT(*)
        FROM lessons
    """).fetchone()[0]

    total_quizzes = conn.execute("""
        SELECT COUNT(*)
        FROM quizzes
    """).fetchone()[0]

    total_questions = conn.execute("""
        SELECT COUNT(*)
        FROM questions
    """).fetchone()[0]

    total_badges = conn.execute("""
        SELECT COUNT(*)
        FROM badges
    """).fetchone()[0]

    total_reviews = conn.execute("""
        SELECT COUNT(*)
        FROM reviews
    """).fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_courses=total_courses,
        total_lessons=total_lessons,
        total_quizzes=total_quizzes,
        total_questions=total_questions,
        total_badges=total_badges,
        total_reviews=total_reviews
    )


# =========================================================
# ADMIN - MANAGE REVIEWS
# =========================================================

@app.route("/admin/reviews")
def admin_reviews():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    reviews_data = conn.execute("""
        SELECT
            reviews.id,
            reviews.rating,
            reviews.review,
            reviews.created_at,
            reviews.updated_at,

            users.name AS student_name,
            users.email AS student_email,

            courses.title AS course_title

        FROM reviews

        JOIN users
        ON reviews.user_id = users.id

        JOIN courses
        ON reviews.course_id = courses.id

        ORDER BY reviews.created_at DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_reviews.html",
        reviews=reviews_data
    )


# =========================================================
# ADMIN - DELETE REVIEW
# =========================================================

@app.route(
    "/admin/reviews/delete/<int:review_id>",
    methods=["POST", "GET"]
)
def admin_delete_review(review_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    conn.execute("""
        DELETE FROM reviews
        WHERE id = ?
    """, (
        review_id,
    ))

    conn.commit()

    conn.close()

    return redirect(
        url_for("admin_reviews")
    )


# =========================================================
# ADMIN - MANAGE STUDENTS
# =========================================================

@app.route(
    "/admin/users",
    endpoint="admin_users"
)
@app.route(
    "/admin/students",
    endpoint="admin_students"
)
def manage_students():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    students = conn.execute("""
        SELECT
            id,
            name,
            email,
            points
        FROM users
        WHERE role = 'student'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_users.html",
        users=students,
        students=students
    )


# =========================================================
# ADMIN - DELETE STUDENT
# =========================================================

@app.route(
    "/admin/users/delete/<int:user_id>"
)
@app.route(
    "/admin/students/delete/<int:user_id>"
)
def admin_delete_user(user_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
        AND role = 'student'
    """, (
        user_id,
    )).fetchone()

    if user is None:

        conn.close()

        return redirect(
            url_for("admin_users")
        )

    # Delete reviews

    conn.execute("""
        DELETE FROM reviews
        WHERE user_id = ?
    """, (
        user_id,
    ))

    # Delete quiz attempts

    conn.execute("""
        DELETE FROM quiz_attempts
        WHERE user_id = ?
    """, (
        user_id,
    ))

    # Delete lesson progress

    conn.execute("""
        DELETE FROM lesson_progress
        WHERE user_id = ?
    """, (
        user_id,
    ))

    # Delete user badges

    conn.execute("""
        DELETE FROM user_badges
        WHERE user_id = ?
    """, (
        user_id,
    ))

    # Delete certificates

    conn.execute("""
        DELETE FROM certificates
        WHERE user_id = ?
    """, (
        user_id,
    ))

    # Delete student

    conn.execute("""
        DELETE FROM users
        WHERE id = ?
        AND role = 'student'
    """, (
        user_id,
    ))

    conn.commit()

    conn.close()

    return redirect(
        url_for("admin_students")
    )


# =========================================================
# ADMIN - MANAGE BADGES
# =========================================================

@app.route("/admin/badges")
def admin_badges():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    badges_data = conn.execute("""
        SELECT
            badges.id,
            badges.name,
            badges.description,
            COUNT(user_badges.id) AS earned_count

        FROM badges

        LEFT JOIN user_badges

        ON badges.id = user_badges.badge_id

        GROUP BY
            badges.id,
            badges.name,
            badges.description

        ORDER BY badges.id ASC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_badges.html",
        badges=badges_data
    )


# =========================================================
# ADMIN - ADD BADGE
# =========================================================

@app.route(
    "/admin/badges/add",
    methods=["GET", "POST"]
)
def admin_add_badge():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not name:

            return render_template(
                "admin_add_badge.html",
                error="Badge name is required."
            )

        conn = get_db()

        existing = conn.execute("""
            SELECT id
            FROM badges
            WHERE name = ?
        """, (
            name,
        )).fetchone()

        if existing:

            conn.close()

            return render_template(
                "admin_add_badge.html",
                error="Badge already exists."
            )

        conn.execute("""
            INSERT INTO badges
            (
                name,
                description
            )
            VALUES (?, ?)
        """, (
            name,
            description
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for("admin_badges")
        )

    return render_template(
        "admin_add_badge.html"
    )


# =========================================================
# ADMIN - EDIT BADGE
# =========================================================

@app.route(
    "/admin/badges/edit/<int:badge_id>",
    methods=["GET", "POST"]
)
def admin_edit_badge(badge_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    badge = conn.execute("""
        SELECT *
        FROM badges
        WHERE id = ?
    """, (
        badge_id,
    )).fetchone()

    if badge is None:

        conn.close()

        return redirect(
            url_for("admin_badges")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not name:

            conn.close()

            return render_template(
                "admin_edit_badge.html",
                badge=badge,
                error="Badge name is required."
            )

        conn.execute("""
            UPDATE badges
            SET
                name = ?,
                description = ?
            WHERE id = ?
        """, (
            name,
            description,
            badge_id
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for("admin_badges")
        )

    conn.close()

    return render_template(
        "admin_edit_badge.html",
        badge=badge
    )


# =========================================================
# ADMIN - DELETE BADGE
# =========================================================

@app.route(
    "/admin/badges/delete/<int:badge_id>"
)
def admin_delete_badge(badge_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    conn.execute("""
        DELETE FROM user_badges
        WHERE badge_id = ?
    """, (
        badge_id,
    ))

    conn.execute("""
        DELETE FROM badges
        WHERE id = ?
    """, (
        badge_id,
    ))

    conn.commit()

    conn.close()

    return redirect(
        url_for("admin_badges")
    )


# =========================================================
# ADMIN - MANAGE COURSES
# =========================================================

@app.route("/admin/courses")
def admin_courses():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    courses_data = conn.execute("""
        SELECT *
        FROM courses
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_courses.html",
        courses=courses_data
    )


# =========================================================
# ADMIN - ADD COURSE
# =========================================================

@app.route(
    "/admin/courses/add",
    methods=["GET", "POST"]
)
def admin_add_course():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        level = request.form.get(
            "level",
            ""
        ).strip()

        if not title:

            return render_template(
                "admin_add_course.html",
                error="Course title is required."
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO courses
            (
                title,
                description,
                level
            )
            VALUES (?, ?, ?)
        """, (
            title,
            description,
            level
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for("admin_courses")
        )

    return render_template(
        "admin_add_course.html"
    )


# =========================================================
# ADMIN - EDIT COURSE
# =========================================================

@app.route(
    "/admin/courses/edit/<int:course_id>",
    methods=["GET", "POST"]
)
def admin_edit_course(course_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    course = conn.execute("""
        SELECT *
        FROM courses
        WHERE id = ?
    """, (
        course_id,
    )).fetchone()

    if course is None:

        conn.close()

        return "Course not found!", 404

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        level = request.form.get(
            "level",
            ""
        ).strip()

        if not title:

            conn.close()

            return render_template(
                "admin_edit_course.html",
                course=course,
                error="Course title is required."
            )

        conn.execute("""
            UPDATE courses
            SET
                title = ?,
                description = ?,
                level = ?
            WHERE id = ?
        """, (
            title,
            description,
            level,
            course_id
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for("admin_courses")
        )

    conn.close()

    return render_template(
        "admin_edit_course.html",
        course=course
    )


# =========================================================
# ADMIN - DELETE COURSE
# =========================================================

@app.route(
    "/admin/courses/delete/<int:course_id>"
)
def admin_delete_course(course_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    course = conn.execute("""
        SELECT id
        FROM courses
        WHERE id = ?
    """, (
        course_id,
    )).fetchone()

    if course is None:

        conn.close()

        return "Course not found!", 404

    # Delete reviews

    conn.execute("""
        DELETE FROM reviews
        WHERE course_id = ?
    """, (
        course_id,
    ))

    # Delete questions

    conn.execute("""
        DELETE FROM questions
        WHERE quiz_id IN (
            SELECT id
            FROM quizzes
            WHERE course_id = ?
        )
    """, (
        course_id,
    ))

    # Delete quiz attempts

    conn.execute("""
        DELETE FROM quiz_attempts
        WHERE quiz_id IN (
            SELECT id
            FROM quizzes
            WHERE course_id = ?
        )
    """, (
        course_id,
    ))

    # Delete quizzes

    conn.execute("""
        DELETE FROM quizzes
        WHERE course_id = ?
    """, (
        course_id,
    ))

    # Delete lesson progress

    conn.execute("""
        DELETE FROM lesson_progress
        WHERE lesson_id IN (
            SELECT id
            FROM lessons
            WHERE course_id = ?
        )
    """, (
        course_id,
    ))

    # Delete certificates

    conn.execute("""
        DELETE FROM certificates
        WHERE course_id = ?
    """, (
        course_id,
    ))

    # Delete lessons

    conn.execute("""
        DELETE FROM lessons
        WHERE course_id = ?
    """, (
        course_id,
    ))

    # Delete course

    conn.execute("""
        DELETE FROM courses
        WHERE id = ?
    """, (
        course_id,
    ))

    conn.commit()

    conn.close()

    return redirect(
        url_for("admin_courses")
    )


# =========================================================
# ADMIN - MANAGE LESSONS
# =========================================================

@app.route("/admin/lessons")
def admin_lessons():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    lessons = conn.execute("""
        SELECT
            lessons.id,
            lessons.course_id,
            lessons.title,
            lessons.content,
            lessons.lesson_order,
            courses.title AS course_title

        FROM lessons

        LEFT JOIN courses

        ON lessons.course_id = courses.id

        ORDER BY lessons.id DESC
    """).fetchall()

    courses_data = conn.execute("""
        SELECT
            id,
            title
        FROM courses
        ORDER BY title ASC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_lessons.html",
        lessons=lessons,
        courses=courses_data
    )


# =========================================================
# ADMIN - ADD LESSON
# =========================================================

@app.route(
    "/admin/lessons/add",
    methods=["GET", "POST"]
)
def admin_add_lesson():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    courses_data = conn.execute("""
        SELECT
            id,
            title
        FROM courses
        ORDER BY title ASC
    """).fetchall()

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        content = request.form.get(
            "content",
            ""
        ).strip()

        course_id = request.form.get(
            "course_id",
            ""
        ).strip()

        lesson_order = request.form.get(
            "lesson_order",
            "1"
        ).strip()

        if not title:

            conn.close()

            return render_template(
                "admin_add_lesson.html",
                courses=courses_data,
                error="Lesson title is required."
            )

        if not course_id:

            conn.close()

            return render_template(
                "admin_add_lesson.html",
                courses=courses_data,
                error="Please select a course."
            )

        try:

            lesson_order = int(
                lesson_order
            )

        except ValueError:

            lesson_order = 1

        conn.execute("""
            INSERT INTO lessons
            (
                course_id,
                title,
                content,
                lesson_order
            )
            VALUES (?, ?, ?, ?)
        """, (
            course_id,
            title,
            content,
            lesson_order
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for("admin_lessons")
        )

    conn.close()

    return render_template(
        "admin_add_lesson.html",
        courses=courses_data
    )


# =========================================================
# ADMIN - EDIT LESSON
# =========================================================

@app.route(
    "/admin/lessons/edit/<int:lesson_id>",
    methods=["GET", "POST"]
)
def admin_edit_lesson(lesson_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    lesson_data = conn.execute("""
        SELECT *
        FROM lessons
        WHERE id = ?
    """, (
        lesson_id,
    )).fetchone()

    if lesson_data is None:

        conn.close()

        return "Lesson not found!", 404

    courses_data = conn.execute("""
        SELECT
            id,
            title
        FROM courses
        ORDER BY title ASC
    """).fetchall()

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        content = request.form.get(
            "content",
            ""
        ).strip()

        course_id = request.form.get(
            "course_id",
            ""
        ).strip()

        lesson_order = request.form.get(
            "lesson_order",
            "1"
        ).strip()

        if not title:

            conn.close()

            return render_template(
                "admin_edit_lesson.html",
                lesson=lesson_data,
                courses=courses_data,
                error="Lesson title is required."
            )

        if not course_id:

            conn.close()

            return render_template(
                "admin_edit_lesson.html",
                lesson=lesson_data,
                courses=courses_data,
                error="Please select a course."
            )

        try:

            lesson_order = int(
                lesson_order
            )

        except ValueError:

            lesson_order = 1

        conn.execute("""
            UPDATE lessons
            SET
                course_id = ?,
                title = ?,
                content = ?,
                lesson_order = ?
            WHERE id = ?
        """, (
            course_id,
            title,
            content,
            lesson_order,
            lesson_id
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for("admin_lessons")
        )

    conn.close()

    return render_template(
        "admin_edit_lesson.html",
        lesson=lesson_data,
        courses=courses_data
    )


# =========================================================
# ADMIN - DELETE LESSON
# =========================================================

@app.route(
    "/admin/lessons/delete/<int:lesson_id>"
)
def admin_delete_lesson(lesson_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    lesson_data = conn.execute("""
        SELECT id
        FROM lessons
        WHERE id = ?
    """, (
        lesson_id,
    )).fetchone()

    if lesson_data is None:

        conn.close()

        return "Lesson not found!", 404

    conn.execute("""
        DELETE FROM lesson_progress
        WHERE lesson_id = ?
    """, (
        lesson_id,
    ))

    conn.execute("""
        DELETE FROM lessons
        WHERE id = ?
    """, (
        lesson_id,
    ))

    conn.commit()

    conn.close()

    return redirect(
        url_for("admin_lessons")
    )


# =========================================================
# ADMIN - MANAGE QUIZZES
# =========================================================

@app.route("/admin/quizzes")
def admin_quizzes():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    quizzes_data = conn.execute("""
        SELECT
            quizzes.id,
            quizzes.title,
            quizzes.description,
            quizzes.course_id,
            courses.title AS course_title

        FROM quizzes

        LEFT JOIN courses

        ON quizzes.course_id = courses.id

        ORDER BY quizzes.id DESC
    """).fetchall()

    courses_data = conn.execute("""
        SELECT
            id,
            title
        FROM courses
        ORDER BY id
    """).fetchall()

    quiz_data = []

    for quiz in quizzes_data:

        question_count = conn.execute("""
            SELECT COUNT(*)
            FROM questions
            WHERE quiz_id = ?
        """, (
            quiz["id"],
        )).fetchone()[0]

        quiz_data.append({
            "id": quiz["id"],
            "title": quiz["title"],
            "description": quiz["description"],
            "course_id": quiz["course_id"],
            "course_title": quiz["course_title"],
            "question_count": question_count
        })

    conn.close()

    return render_template(
        "admin_quizzes.html",
        quizzes=quiz_data,
        courses=courses_data
    )


# =========================================================
# ADMIN - ADD QUIZ
# =========================================================

@app.route(
    "/admin/quizzes/add",
    methods=["GET", "POST"]
)
def admin_add_quiz():

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    courses_data = conn.execute("""
        SELECT
            id,
            title
        FROM courses
        ORDER BY title
    """).fetchall()

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        course_id = request.form.get(
            "course_id",
            ""
        ).strip()

        if not title or not course_id:

            conn.close()

            return render_template(
                "admin_add_quiz.html",
                courses=courses_data,
                error="Please fill all required fields."
            )

        conn.execute("""
            INSERT INTO quizzes
            (
                course_id,
                title,
                description
            )
            VALUES (?, ?, ?)
        """, (
            course_id,
            title,
            description
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for("admin_quizzes")
        )

    conn.close()

    return render_template(
        "admin_add_quiz.html",
        courses=courses_data
    )


# =========================================================
# ADMIN - EDIT QUIZ
# =========================================================

@app.route(
    "/admin/quizzes/edit/<int:quiz_id>",
    methods=["GET", "POST"]
)
def admin_edit_quiz(quiz_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    quiz = conn.execute("""
        SELECT
            id,
            course_id,
            title,
            description
        FROM quizzes
        WHERE id = ?
    """, (
        quiz_id,
    )).fetchone()

    if quiz is None:

        conn.close()

        return redirect(
            url_for("admin_quizzes")
        )

    courses_data = conn.execute("""
        SELECT
            id,
            title
        FROM courses
        ORDER BY title
    """).fetchall()

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        course_id = request.form.get(
            "course_id",
            ""
        ).strip()

        if not title or not course_id:

            conn.close()

            return render_template(
                "admin_edit_quiz.html",
                quiz=quiz,
                courses=courses_data,
                error="Please fill all required fields."
            )

        conn.execute("""
            UPDATE quizzes
            SET
                course_id = ?,
                title = ?,
                description = ?
            WHERE id = ?
        """, (
            course_id,
            title,
            description,
            quiz_id
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for("admin_quizzes")
        )

    conn.close()

    return render_template(
        "admin_edit_quiz.html",
        quiz=quiz,
        courses=courses_data
    )


# =========================================================
# ADMIN - DELETE QUIZ
# =========================================================

@app.route(
    "/admin/quizzes/delete/<int:quiz_id>"
)
def admin_delete_quiz(quiz_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    conn.execute("""
        DELETE FROM quiz_attempts
        WHERE quiz_id = ?
    """, (
        quiz_id,
    ))

    conn.execute("""
        DELETE FROM questions
        WHERE quiz_id = ?
    """, (
        quiz_id,
    ))

    conn.execute("""
        DELETE FROM quizzes
        WHERE id = ?
    """, (
        quiz_id,
    ))

    conn.commit()

    conn.close()

    return redirect(
        url_for("admin_quizzes")
    )


# =========================================================
# ADMIN - MANAGE QUESTIONS
# =========================================================

@app.route(
    "/admin/quizzes/<int:quiz_id>/questions"
)
def admin_questions(quiz_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    quiz = conn.execute("""
        SELECT
            quizzes.id,
            quizzes.title,
            quizzes.description,
            courses.title AS course_title

        FROM quizzes

        LEFT JOIN courses

        ON quizzes.course_id = courses.id

        WHERE quizzes.id = ?
    """, (
        quiz_id,
    )).fetchone()

    if quiz is None:

        conn.close()

        return redirect(
            url_for("admin_quizzes")
        )

    questions_data = conn.execute("""
        SELECT
            id,
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer

        FROM questions

        WHERE quiz_id = ?

        ORDER BY id
    """, (
        quiz_id,
    )).fetchall()

    conn.close()

    return render_template(
        "admin_questions.html",
        quiz=quiz,
        questions=questions_data
    )


# =========================================================
# ADMIN - ADD QUESTION
# =========================================================

@app.route(
    "/admin/quizzes/<int:quiz_id>/questions/add",
    methods=["GET", "POST"]
)
def admin_add_question(quiz_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    quiz = conn.execute("""
        SELECT
            quizzes.id,
            quizzes.title,
            courses.title AS course_title

        FROM quizzes

        LEFT JOIN courses

        ON quizzes.course_id = courses.id

        WHERE quizzes.id = ?
    """, (
        quiz_id,
    )).fetchone()

    if quiz is None:

        conn.close()

        return redirect(
            url_for("admin_quizzes")
        )

    if request.method == "POST":

        question = request.form.get(
            "question",
            ""
        ).strip()

        option_a = request.form.get(
            "option_a",
            ""
        ).strip()

        option_b = request.form.get(
            "option_b",
            ""
        ).strip()

        option_c = request.form.get(
            "option_c",
            ""
        ).strip()

        option_d = request.form.get(
            "option_d",
            ""
        ).strip()

        correct_answer = request.form.get(
            "answer",
            ""
        ).strip().upper()

        if not all([
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer
        ]):

            conn.close()

            return render_template(
                "admin_add_question.html",
                quiz=quiz,
                error="Please fill all fields."
            )

        if correct_answer not in [
            "A",
            "B",
            "C",
            "D"
        ]:

            conn.close()

            return render_template(
                "admin_add_question.html",
                quiz=quiz,
                error="Correct answer must be A, B, C or D."
            )

        conn.execute("""
            INSERT INTO questions
            (
                quiz_id,
                question,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            quiz_id,
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for(
                "admin_questions",
                quiz_id=quiz_id
            )
        )

    conn.close()

    return render_template(
        "admin_add_question.html",
        quiz=quiz
    )


# =========================================================
# ADMIN - EDIT QUESTION
# =========================================================

@app.route(
    "/admin/questions/edit/<int:question_id>",
    methods=["GET", "POST"]
)
def admin_edit_question(question_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    question = conn.execute("""
        SELECT
            id,
            quiz_id,
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer

        FROM questions

        WHERE id = ?
    """, (
        question_id,
    )).fetchone()

    if question is None:

        conn.close()

        return redirect(
            url_for("admin_quizzes")
        )

    quiz = conn.execute("""
        SELECT
            quizzes.id,
            quizzes.title,
            courses.title AS course_title

        FROM quizzes

        LEFT JOIN courses

        ON quizzes.course_id = courses.id

        WHERE quizzes.id = ?
    """, (
        question["quiz_id"],
    )).fetchone()

    if request.method == "POST":

        question_text = request.form.get(
            "question",
            ""
        ).strip()

        option_a = request.form.get(
            "option_a",
            ""
        ).strip()

        option_b = request.form.get(
            "option_b",
            ""
        ).strip()

        option_c = request.form.get(
            "option_c",
            ""
        ).strip()

        option_d = request.form.get(
            "option_d",
            ""
        ).strip()

        correct_answer = request.form.get(
            "answer",
            ""
        ).strip().upper()

        if not all([
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer
        ]):

            conn.close()

            return render_template(
                "admin_edit_question.html",
                question=question,
                quiz=quiz,
                error="Please fill all fields."
            )

        if correct_answer not in [
            "A",
            "B",
            "C",
            "D"
        ]:

            conn.close()

            return render_template(
                "admin_edit_question.html",
                question=question,
                quiz=quiz,
                error="Correct answer must be A, B, C or D."
            )

        conn.execute("""
            UPDATE questions
            SET
                question = ?,
                option_a = ?,
                option_b = ?,
                option_c = ?,
                option_d = ?,
                correct_answer = ?

            WHERE id = ?
        """, (
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            question_id
        ))

        conn.commit()

        conn.close()

        return redirect(
            url_for(
                "admin_questions",
                quiz_id=question["quiz_id"]
            )
        )

    conn.close()

    return render_template(
        "admin_edit_question.html",
        question=question,
        quiz=quiz
    )


# =========================================================
# ADMIN - DELETE QUESTION
# =========================================================

@app.route(
    "/admin/questions/delete/<int:question_id>"
)
def admin_delete_question(question_id):

    if not is_admin():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    question = conn.execute("""
        SELECT
            quiz_id
        FROM questions
        WHERE id = ?
    """, (
        question_id,
    )).fetchone()

    if question is None:

        conn.close()

        return redirect(
            url_for("admin_quizzes")
        )

    quiz_id = question["quiz_id"]

    conn.execute("""
        DELETE FROM questions
        WHERE id = ?
    """, (
        question_id,
    ))

    conn.commit()

    conn.close()

    return redirect(
        url_for(
            "admin_questions",
            quiz_id=quiz_id
        )
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin_id",
        None
    )

    session.pop(
        "admin_name",
        None
    )

    return redirect(
        url_for("admin_login")
    )


# =========================================================
# STUDENT LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("homepage")
    )


# =========================================================
# CERTIFICATE QR CODE INJECTION
# =========================================================

@app.after_request
def add_certificate_qr_code(response):

    content_type = response.headers.get(
        "Content-Type",
        ""
    )

    if "text/html" not in content_type:

        return response

    if not request.path.startswith("/certificate/"):

        return response

    try:

        html = response.get_data(
            as_text=True
        )

    except Exception:

        return response

    if "educarenix-certificate-qr" in html:

        return response

    qr_widget = r'''
<style id="educarenix-certificate-qr-style">
#educarenix-certificate-qr {
    position: absolute;
    right: 72px;
    bottom: 48px;
    z-index: 50;
    width: 112px;
    padding: 8px;
    border-radius: 12px;
    background: rgba(255,255,255,.97);
    border: 1px solid #e5e7eb;
    box-shadow: 0 10px 30px rgba(15,23,42,.16);
    text-align: center;
}
#educarenix-certificate-qr canvas,
#educarenix-certificate-qr img {
    width: 94px !important;
    height: 94px !important;
    display: block;
    margin: 0 auto;
}
#educarenix-certificate-qr .qr-label {
    margin-top: 5px;
    font-family: Arial, sans-serif;
    font-size: 8px;
    line-height: 1.2;
    font-weight: 800;
    letter-spacing: .7px;
    color: #334155;
    text-transform: uppercase;
}
#educarenix-certificate-qr .qr-small {
    margin-top: 2px;
    font-family: Arial, sans-serif;
    font-size: 7px;
    color: #64748b;
}
@media (max-width: 750px) {
    #educarenix-certificate-qr {
        position: relative;
        right: auto;
        bottom: auto;
        margin: 22px auto 0;
    }
}
@media print {
    #educarenix-certificate-qr {
        position: absolute;
        right: 55px;
        bottom: 35px;
        box-shadow: none;
        border: 1px solid #cbd5e1;
    }
}
</style>

<div id="educarenix-certificate-qr" aria-label="Certificate verification QR code">
    <div id="educarenix-certificate-qr-code"></div>
    <div class="qr-label">Scan to Verify</div>
    <div class="qr-small">EduCareNix</div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>

<script>
(function () {

    function createCertificateQR() {

        var box = document.getElementById(
            "educarenix-certificate-qr"
        );

        var target = document.getElementById(
            "educarenix-certificate-qr-code"
        );

        if (
            !box ||
            !target ||
            typeof QRCode === "undefined"
        ) {

            return;
        }

        var text = document.body.innerText || "";

        var match = text.match(
            /CERTIFICATE\s*ID:\s*([A-Z0-9-]+)/i
        );

        if (!match) {

            box.style.display = "none";

            return;
        }

        var certificateId =
            match[1].toUpperCase();

        var verifyUrl =
            window.location.origin +
            "/verify/" +
            encodeURIComponent(certificateId);

        target.innerHTML = "";

        new QRCode(
            target,
            {
                text: verifyUrl,
                width: 94,
                height: 94,
                colorDark: "#111827",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.M
            }
        );
    }

    if (
        document.readyState === "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            createCertificateQR
        );

    } else {

        createCertificateQR();

    }

})();
</script>
'''

    if "</body>" in html.lower():

        pos = html.lower().rfind("</body>")

        html = (
            html[:pos]
            + qr_widget
            + html[pos:]
        )

        response.set_data(html)

    return response


# =========================================================
# GLOBAL AI CHATBOT BUTTON
# =========================================================

@app.after_request
def add_global_chatbot_button(response):

    content_type = response.headers.get(
        "Content-Type",
        ""
    )

    if "text/html" not in content_type:

        return response

    try:

        html = response.get_data(
            as_text=True
        )

    except Exception:

        return response

    if "educarenix-global-ai-button" in html:

        return response

    chatbot_widget = """
<style id="educarenix-global-ai-style">

#educarenix-global-ai-button {

    position: fixed !important;

    right: 24px !important;

    bottom: 24px !important;

    width: 64px !important;

    height: 64px !important;

    display: flex !important;

    align-items: center !important;

    justify-content: center !important;

    z-index: 2147483647 !important;

    border-radius: 20px !important;

    text-decoration: none !important;

    font-size: 30px !important;

    background: linear-gradient(
        135deg,
        #2563eb,
        #7c3aed
    ) !important;

    color: #ffffff !important;

    border: 1px solid rgba(
        255,
        255,
        255,
        .25
    ) !important;

    box-shadow:
        0 15px 45px
        rgba(37,99,235,.45)
        !important;

    transition:
        transform .25s ease,
        box-shadow .25s ease
        !important;
}

#educarenix-global-ai-button:hover {

    transform:
        translateY(-6px)
        scale(1.08)
        !important;

    box-shadow:
        0 20px 55px
        rgba(124,58,237,.60)
        !important;
}

#educarenix-global-ai-button::after {

    content: "Ask EduCareNix AI";

    position: absolute;

    right: 74px;

    white-space: nowrap;

    padding: 8px 12px;

    border-radius: 10px;

    background:
        rgba(8,15,35,.95);

    color: #ffffff;

    font-size: 12px;

    font-family: Arial, sans-serif;

    opacity: 0;

    pointer-events: none;

    transform:
        translateX(8px);

    transition: .25s ease;
}

#educarenix-global-ai-button:hover::after {

    opacity: 1;

    transform:
        translateX(0);
}

@media (max-width: 600px) {

    #educarenix-global-ai-button {

        right: 16px !important;

        bottom: 16px !important;

        width: 58px !important;

        height: 58px !important;

        font-size: 27px !important;

        border-radius: 18px !important;
    }

    #educarenix-global-ai-button::after {

        display: none;
    }
}

</style>

<a
    id="educarenix-global-ai-button"
    href="/chatbot"
    title="EduCareNix AI Assistant"
    aria-label="Open EduCareNix AI Assistant"
>
    🤖
</a>
"""

    if "</body>" in html.lower():

        pos = html.lower().rfind("</body>")

        html = (
            html[:pos]
            + chatbot_widget
            + html[pos:]
        )

        response.set_data(html)

    return response


# =========================================================
# CHECK QUESTIONS TABLE
# =========================================================

def check_questions_table():

    conn = get_db()

    columns = conn.execute("""
        PRAGMA table_info(questions)
    """).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    if "correct_answer" not in column_names:

        print(
            "WARNING: correct_answer column is missing "
            "from questions table."
        )

    conn.close()


# =========================================================
# REAL AI CHAT API - LOCAL OLLAMA
# =========================================================

@app.route("/api/chat", methods=["POST"])
def api_chat():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "error": "Please login first."
        }), 401

    try:

        data = request.get_json(
            silent=True
        ) or {}

        user_message = str(
            data.get(
                "message",
                ""
            )
        ).strip()

        if not user_message:

            return jsonify({
                "success": False,
                "error": "Please enter a message."
            }), 400

        if len(user_message) > 4000:

            return jsonify({
                "success": False,
                "error": (
                    "Message is too long. "
                    "Please keep it under 4000 characters."
                )
            }), 400

        system_prompt = (
            "You are EduCareNix AI, a friendly educational assistant "
            "for students. Help with Python, C, C++, DSA, Web Development, "
            "Data Analytics, Artificial Intelligence, mathematics, "
            "programming and general study topics. "
            "Explain difficult concepts in simple language. "
            "When giving code, make it beginner-friendly and explain "
            "important parts. "
            "Do not claim to have performed actions that you did not perform. "
            "Keep answers useful and reasonably concise unless the student "
            "asks for detail. "
            "The student may use Bengali, Banglish, Hindi, or English; "
            "reply in the language that best matches the student's message."
        )

        payload = {

            "model": OLLAMA_MODEL,

            "stream": False,

            "messages": [

                {
                    "role": "system",
                    "content": system_prompt
                },

                {
                    "role": "user",
                    "content": user_message
                }
            ],

            "options": {
                "temperature": 0.7
            }
        }

        body = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

        http_request = urllib.request.Request(

            OLLAMA_URL,

            data=body,

            headers={
                "Content-Type":
                "application/json"
            },

            method="POST"
        )

        with urllib.request.urlopen(
            http_request,
            timeout=120
        ) as http_response:

            raw_response = (
                http_response
                .read()
                .decode("utf-8")
            )

        ai_response = json.loads(
            raw_response
        )

        reply = str(
            ai_response
            .get("message", {})
            .get("content", "")
        ).strip()

        if not reply:

            return jsonify({
                "success": False,
                "error": (
                    "The local AI returned an empty "
                    "response. Please try again."
                )
            }), 500

        return jsonify({
            "success": True,
            "reply": reply
        })

    except urllib.error.URLError as connection_error:

        print(
            "OLLAMA CONNECTION ERROR:",
            connection_error
        )

        return jsonify({
            "success": False,
            "error": (
                "EduCareNix AI is not connected to Ollama. "
                "Please make sure Ollama is running and try again."
            )
        }), 503

    except Exception as ai_error:

        print(
            "OLLAMA AI ERROR:",
            ai_error
        )

        return jsonify({
            "success": False,
            "error": (
                "The local AI could not answer right now. "
                "Please try again."
            )
        }), 500


# =========================================================
# CHATBOT PAGE
# =========================================================

@app.route("/chatbot")
def chatbot():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    return render_template(
        "chatbot.html"
    )


# =========================================================
# PUBLIC CERTIFICATE VERIFICATION
# =========================================================

@app.route(
    "/verify",
    methods=["GET", "POST"]
)
def verify_certificate_search():

    certificate_id = ""

    if request.method == "POST":

        certificate_id = request.form.get(
            "certificate_id",
            ""
        ).strip().upper()

        if certificate_id:

            return redirect(
                url_for(
                    "verify_certificate",
                    certificate_id=certificate_id
                )
            )

    return render_template(
        "verify_certificate.html",
        certificate=None,
        searched=bool(certificate_id)
    )


# =========================================================
# VERIFY CERTIFICATE
# =========================================================

@app.route(
    "/verify/<certificate_id>"
)
def verify_certificate(certificate_id):

    certificate_id = (
        certificate_id
        .strip()
        .upper()
    )

    conn = get_db()

    certificate = conn.execute("""
        SELECT
            certificates.certificate_id,
            certificates.issued_at,
            users.name AS student_name,
            courses.title AS course_name

        FROM certificates

        JOIN users
        ON certificates.user_id = users.id

        JOIN courses
        ON certificates.course_id = courses.id

        WHERE UPPER(
            certificates.certificate_id
        ) = ?
    """, (
        certificate_id,
    )).fetchone()

    conn.close()

    return render_template(
        "verify_certificate.html",
        certificate=certificate,
        searched=True
    )


# =========================================================
# VIEW CERTIFICATE
# =========================================================

@app.route(
    "/certificate/<int:certificate_id>"
)
def view_certificate(certificate_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    certificate = conn.execute("""
        SELECT
            certificates.id,
            certificates.certificate_id,
            certificates.issued_at,

            users.name AS student_name,

            courses.title AS course_name

        FROM certificates

        JOIN users
        ON certificates.user_id = users.id

        JOIN courses
        ON certificates.course_id = courses.id

        WHERE certificates.id = ?

        AND certificates.user_id = ?

    """, (
        certificate_id,
        session["user_id"]
    )).fetchone()

    conn.close()

    if certificate is None:

        return "Certificate not found!", 404

    return render_template(
        "certificate.html",
        certificate=certificate
    )
# =========================================================
# EDIT PROFILE
# =========================================================

@app.route(
    "/profile/edit",
    methods=["GET", "POST"]
)
def edit_profile():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    if user is None:

        conn.close()

        session.clear()

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        if not name or not email:

            conn.close()

            return render_template(
                "edit_profile.html",
                user=user,
                error="Name and email are required."
            )

        # Check duplicate email

        existing_user = conn.execute("""
            SELECT id
            FROM users
            WHERE email = ?
            AND id != ?
        """, (
            email,
            user_id
        )).fetchone()

        if existing_user:

            conn.close()

            return render_template(
                "edit_profile.html",
                user=user,
                error="This email is already registered with another account."
            )

        # Update profile

        conn.execute("""
            UPDATE users
            SET
                name = ?,
                email = ?
            WHERE id = ?
        """, (
            name,
            email,
            user_id
        ))

        conn.commit()

        conn.close()

        # Update current login session

        session["user_name"] = name

        return redirect(
            url_for("profile")
        )

    conn.close()

    return render_template(
        "edit_profile.html",
        user=user
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@app.route(
    "/profile/change-password",
    methods=["GET", "POST"]
)
def change_password():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    if user is None:

        conn.close()

        session.clear()

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Check current password

        if not check_password_hash(
            user["password"],
            current_password
        ):

            conn.close()

            return render_template(
                "change_password.html",
                error="Current password is incorrect."
            )

        # Minimum password length

        if len(new_password) < 6:

            conn.close()

            return render_template(
                "change_password.html",
                error="New password must contain at least 6 characters."
            )

        # Check confirmation

        if new_password != confirm_password:

            conn.close()

            return render_template(
                "change_password.html",
                error="New password and confirm password do not match."
            )

        # Prevent same password

        if check_password_hash(
            user["password"],
            new_password
        ):

            conn.close()

            return render_template(
                "change_password.html",
                error="New password must be different from your current password."
            )

        # Hash new password

        hashed_password = generate_password_hash(
            new_password
        )

        conn.execute("""
            UPDATE users
            SET password = ?
            WHERE id = ?
        """, (
            hashed_password,
            user_id
        ))

        conn.commit()

        conn.close()

        return render_template(
            "change_password.html",
            success="Password changed successfully!"
        )

    conn.close()

    return render_template(
        "change_password.html"
    )


# =========================================================
# PROFILE UPLOAD SETTINGS
# =========================================================

UPLOAD_FOLDER = os.path.join("static", "uploads", "profiles")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_PROFILE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}


def allowed_profile_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_PROFILE_EXTENSIONS
    )


os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    init_db()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
