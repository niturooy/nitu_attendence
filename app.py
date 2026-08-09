from flask import Flask, render_template, request, redirect, send_file, session
import sqlite3
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Paragraph
)
from reportlab.lib.styles import ParagraphStyle


app = Flask(__name__)

# Session এর জন্য secret key
app.secret_key = "attendance_system_secret_123"

DATABASE = "attendance.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

def create_tables():

    conn = get_db()

    # Students
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT NOT NULL,

            name TEXT NOT NULL,

            department TEXT NOT NULL,

            semester TEXT NOT NULL,

            section TEXT
        )
    """)

    # Subjects
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subjects (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            code TEXT NOT NULL,

            name TEXT NOT NULL
        )
    """)

    # Users
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            username TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT NOT NULL
        )
    """)

    # Attendance
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id INTEGER NOT NULL,

            subject_id INTEGER NOT NULL,

            attendance_date TEXT NOT NULL,

            status TEXT NOT NULL
        )
    """)

    conn.commit()

    conn.close()


# =========================================================
# CREATE DEFAULT TEACHER
# =========================================================

def create_default_teacher():

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE username = ?
    """, ("teacher",)).fetchone()

    if not user:

        conn.execute("""
            INSERT INTO users
            (name, username, password, role)

            VALUES (?, ?, ?, ?)
        """, (
            "Teacher",
            "teacher",
            "1234",
            "teacher"
        ))

        conn.commit()

    conn.close()


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required():

    if "user_id" not in session:

        return False

    return True


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if "user_id" in session:

        return redirect("/teacher_dashboard")

    return redirect("/login")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users

            WHERE username = ?
            AND password = ?
            AND role = 'teacher'
        """, (
            username,
            password
        )).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["name"] = user["name"]

            return redirect("/teacher_dashboard")

        return "Invalid username or password!"

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================================================
# TEACHER DASHBOARD
# =========================================================
@app.route("/teacher_dashboard")
def teacher_dashboard():

    if not login_required():

        return redirect("/login")

    conn = get_db()

    student_count = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]

    subject_count = conn.execute("""
        SELECT COUNT(*)
        FROM subjects
    """).fetchone()[0]

    attendance_count = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
    """).fetchone()[0]

    semester_count = conn.execute("""
        SELECT COUNT(DISTINCT semester)
        FROM students
    """).fetchone()[0]

    conn.close()

    return render_template(
        "teacher_dashboard.html",

        student_count=student_count,

        subject_count=subject_count,

        attendance_count=attendance_count,

        semester_count=semester_count
    )
  
# =========================================================
# STUDENT MANAGEMENT
# =========================================================

@app.route("/students", methods=["GET", "POST"])
def students():

    if not login_required():

        return redirect("/login")

    conn = get_db()

    # ---------------------------------------------
    # ADD STUDENT
    # ---------------------------------------------

    if request.method == "POST":

        student_id = request.form["student_id"]

        name = request.form["name"]

        department = request.form["department"]

        semester = request.form["semester"]

        section = request.form["section"]

        conn.execute("""
            INSERT INTO students
            (
                student_id,
                name,
                department,
                semester,
                section
            )

            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id,
            name,
            department,
            semester,
            section
        ))

        conn.commit()

    # ---------------------------------------------
    # FILTER
    # ---------------------------------------------

    selected_semester = request.args.get(
        "semester",
        ""
    )

    selected_section = request.args.get(
        "section",
        ""
    )

    query = """
        SELECT *
        FROM students
        WHERE 1=1
    """

    params = []

    if selected_semester:

        query += """
            AND semester = ?
        """

        params.append(selected_semester)

    if selected_section:

        query += """
            AND section = ?
        """

        params.append(selected_section)

    # প্রথমে যে student add হবে
    # তার serial আগে থাকবে

    query += """
        ORDER BY id ASC
    """

    student_list = conn.execute(
        query,
        params
    ).fetchall()

    # সব semester
    semesters = conn.execute("""
        SELECT DISTINCT semester
        FROM students
        ORDER BY semester
    """).fetchall()

    # সব section
    sections = conn.execute("""
        SELECT DISTINCT section
        FROM students
        WHERE section IS NOT NULL
        AND section != ''
        ORDER BY section
    """).fetchall()

    conn.close()

    return render_template(
        "students.html",

        students=student_list,

        semesters=semesters,

        sections=sections,

        selected_semester=selected_semester,

        selected_section=selected_section
    )


# =========================================================
# DELETE STUDENT
# =========================================================

@app.route("/students/delete/<int:id>")
def delete_student(id):

    if not login_required():

        return redirect("/login")

    conn = get_db()

    conn.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (id,))

    conn.commit()

    conn.close()

    return redirect("/students")


# =========================================================
# EDIT STUDENT
# =========================================================

@app.route(
    "/students/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit_student(id):

    if not login_required():

        return redirect("/login")

    conn = get_db()

    if request.method == "POST":

        student_id = request.form["student_id"]

        name = request.form["name"]

        department = request.form["department"]

        semester = request.form["semester"]

        section = request.form["section"]

        conn.execute("""
            UPDATE students

            SET
                student_id = ?,
                name = ?,
                department = ?,
                semester = ?,
                section = ?

            WHERE id = ?
        """, (
            student_id,
            name,
            department,
            semester,
            section,
            id
        ))

        conn.commit()

        conn.close()

        return redirect("/students")

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (id,)).fetchone()

    conn.close()

    return render_template(
        "edit_student.html",
        student=student
    )


# =========================================================
# SUBJECT MANAGEMENT
# =========================================================

@app.route("/subjects", methods=["GET", "POST"])
def subjects():

    if not login_required():

        return redirect("/login")

    conn = get_db()

    if request.method == "POST":

        code = request.form["code"]

        name = request.form["name"]

        conn.execute("""
            INSERT INTO subjects
            (code, name)

            VALUES (?, ?)
        """, (
            code,
            name
        ))

        conn.commit()

    subject_list = conn.execute("""
        SELECT *
        FROM subjects
        ORDER BY id ASC
    """).fetchall()

    conn.close()

    return render_template(
        "subjects.html",
        subjects=subject_list
    )


# =========================================================
# TAKE ATTENDANCE
# =========================================================

@app.route(
    "/attendance",
    methods=["GET", "POST"]
)
def attendance():

    if not login_required():

        return redirect("/login")

    conn = get_db()

    subjects = conn.execute("""
        SELECT *
        FROM subjects
        ORDER BY name
    """).fetchall()

    semesters = conn.execute("""
        SELECT DISTINCT semester
        FROM students
        ORDER BY semester
    """).fetchall()

    selected_semester = request.values.get(
        "semester",
        ""
    )

    selected_subject = request.values.get(
        "subject_id",
        ""
    )

    # ---------------------------------------------
    # ATTENDANCE SAVE
    # ---------------------------------------------

    if request.method == "POST":

        subject_id = request.form["subject_id"]

        date = request.form["date"]

        semester = request.form["semester"]

        students = conn.execute("""
            SELECT *
            FROM students

            WHERE semester = ?

            ORDER BY id ASC
        """, (
            semester,
        )).fetchall()

        for student in students:

            status = request.form.get(
                f"status_{student['id']}"
            )

            if status:

                # একই date + subject + student থাকলে
                # আগে delete করবে

                conn.execute("""
                    DELETE FROM attendance

                    WHERE
                        student_id = ?
                        AND subject_id = ?
                        AND attendance_date = ?
                """, (
                    student["id"],
                    subject_id,
                    date
                ))

                conn.execute("""
                    INSERT INTO attendance
                    (
                        student_id,
                        subject_id,
                        attendance_date,
                        status
                    )

                    VALUES (?, ?, ?, ?)
                """, (
                    student["id"],
                    subject_id,
                    date,
                    status
                ))

        conn.commit()

        conn.close()

        return redirect(
            f"/attendance?semester={semester}"
            f"&subject_id={subject_id}"
        )

    # ---------------------------------------------
    # FILTER STUDENTS
    # ---------------------------------------------

    students = []

    if selected_semester:

        students = conn.execute("""
            SELECT *
            FROM students

            WHERE semester = ?

            ORDER BY id ASC
        """, (
            selected_semester,
        )).fetchall()

    conn.close()

    return render_template(
        "attendance.html",

        students=students,

        subjects=subjects,

        semesters=semesters,

        selected_semester=selected_semester,

        selected_subject=selected_subject
    )


# =========================================================
# ATTENDANCE REPORT
# =========================================================
@app.route("/attendance_report", methods=["GET", "POST"])
def attendance_report():

    if not login_required():
        return redirect("/login")

    conn = get_db()

    # Filter values
    selected_semester = request.values.get("semester", "")
    selected_subject = request.values.get("subject_id", "")
    selected_date = request.values.get("date", "")
    selected_percentage = request.values.get("percentage", "")

    # Dropdown data
    semesters = conn.execute("""
        SELECT DISTINCT semester
        FROM students
        ORDER BY semester
    """).fetchall()

    subjects = conn.execute("""
        SELECT *
        FROM subjects
        ORDER BY name
    """).fetchall()

    # Main query
    query = """
        SELECT

            students.id,
            students.student_id,
            students.name,
            students.semester,
            students.section,

            COUNT(attendance.id) AS total_days,

            SUM(
                CASE
                    WHEN attendance.status = 'Present'
                    THEN 1
                    ELSE 0
                END
            ) AS present_days,

            SUM(
                CASE
                    WHEN attendance.status = 'Absent'
                    THEN 1
                    ELSE 0
                END
            ) AS absent_days

        FROM students

        LEFT JOIN attendance
        ON students.id = attendance.student_id
    """

    conditions = []
    params = []

    # Semester filter
    if selected_semester:

        conditions.append(
            "students.semester = ?"
        )

        params.append(selected_semester)

    # Subject filter
    if selected_subject:

        conditions.append(
            "attendance.subject_id = ?"
        )

        params.append(selected_subject)

    # Date filter
    if selected_date:

        conditions.append(
            "attendance.attendance_date = ?"
        )

        params.append(selected_date)

    # WHERE
    if conditions:

        query += " WHERE " + " AND ".join(conditions)

    query += """
        GROUP BY students.id

        ORDER BY
            students.semester,
            students.student_id
    """

    report = conn.execute(
        query,
        params
    ).fetchall()

    # ---------------------------------------------
    # Percentage Filter
    # ---------------------------------------------

    filtered_report = []

    for student in report:

        total = student["total_days"] or 0

        present = student["present_days"] or 0

        if total > 0:

            percentage = (
                present / total
            ) * 100

        else:

            percentage = 0

        # Below 70%
        if selected_percentage == "below70":

            if percentage < 70:

                filtered_report.append(student)

        # 70% or above
        elif selected_percentage == "70plus":

            if percentage >= 70:

                filtered_report.append(student)

        # All
        else:

            filtered_report.append(student)

    conn.close()

    return render_template(
        "attendance_report.html",

        report=filtered_report,

        semesters=semesters,

        subjects=subjects,

        selected_semester=selected_semester,

        selected_subject=selected_subject,

        selected_date=selected_date,

        selected_percentage=selected_percentage
    )

    # ==============================
    # DATE FILTER
    # ==============================

    if selected_date:

        query += """
            AND attendance.attendance_date = ?
        """

        params.append(selected_date)


    # ==============================
    # SEMESTER FILTER
    # ==============================

    if selected_semester:

        query += """
            AND students.semester = ?
        """

        params.append(selected_semester)


    # ==============================
    # SECTION FILTER
    # ==============================

    if selected_section:

        query += """
            AND students.section = ?
        """

        params.append(selected_section)


    # ==============================
    # SUBJECT FILTER
    # ==============================

    if selected_subject:

        query += """
            AND attendance.subject_id = ?
        """

        params.append(selected_subject)


    # ==============================
    # ORDER
    # ==============================

    query += """

        ORDER BY
            attendance.attendance_date DESC,
            students.semester,
            students.section,
            students.student_id

    """


    report = conn.execute(
        query,
        params
    ).fetchall()


    conn.close()


    return render_template(

        "attendance_report.html",

        report=report,

        semesters=semesters,

        sections=sections,

        subjects=subjects,

        selected_date=selected_date,

        selected_semester=selected_semester,

        selected_section=selected_section,

        selected_subject=selected_subject

    )
# =========================================================
# ATTENDANCE DETAILS
# =========================================================

@app.route("/attendance_details")
def attendance_details():

    if not login_required():

        return redirect("/login")

    conn = get_db()

    records = conn.execute("""
        SELECT

            students.student_id,

            students.name,

            students.semester,

            students.section,

            subjects.code,

            subjects.name AS subject_name,

            attendance.attendance_date,

            attendance.status

        FROM attendance

        JOIN students

        ON attendance.student_id = students.id

        JOIN subjects

        ON attendance.subject_id = subjects.id

        ORDER BY
            attendance.attendance_date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "attendance_details.html",
        records=records
    )


# =========================================================
# STUDENT REPORT
# =========================================================

@app.route(
    "/student_report",
    methods=["GET", "POST"]
)
def student_report():

    if not login_required():

        return redirect("/login")

    conn = get_db()

    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY name
    """).fetchall()

    selected_student = None

    summary = None

    records = []

    if request.method == "POST":

        student_id = request.form["student_id"]

        selected_student = conn.execute("""
            SELECT *
            FROM students
            WHERE id = ?
        """, (
            student_id,
        )).fetchone()

        summary = conn.execute("""
            SELECT

                COUNT(*) AS total_days,

                SUM(
                    CASE
                        WHEN status = 'Present'
                        THEN 1
                        ELSE 0
                    END
                ) AS present_days,

                SUM(
                    CASE
                        WHEN status = 'Absent'
                        THEN 1
                        ELSE 0
                    END
                ) AS absent_days

            FROM attendance

            WHERE student_id = ?
        """, (
            student_id,
        )).fetchone()

        records = conn.execute("""
            SELECT

                attendance.attendance_date,

                subjects.code,

                subjects.name AS subject_name,

                attendance.status

            FROM attendance

            JOIN subjects

            ON attendance.subject_id = subjects.id

            WHERE attendance.student_id = ?

            ORDER BY
                attendance.attendance_date DESC
        """, (
            student_id,
        )).fetchall()

    conn.close()

    return render_template(
        "student_report.html",

        students=students,

        selected_student=selected_student,

        summary=summary,

        records=records
    )


# =========================================================
# SUBJECT REPORT
# =========================================================
@app.route("/subject_report", methods=["GET", "POST"])
def subject_report():

    if not login_required():
        return redirect("/login")

    conn = get_db()

    # সব Subject
    subjects = conn.execute("""
        SELECT *
        FROM subjects
        ORDER BY name
    """).fetchall()

    # সব Student
    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY student_id
    """).fetchall()

    selected_subject = None
    selected_student = None

    total = 0
    present = 0
    absent = 0
    percentage = 0

    if request.method == "POST":

        subject_id = request.form["subject_id"]
        student_id = request.form["student_id"]

        # Subject information
        selected_subject = conn.execute("""
            SELECT *
            FROM subjects
            WHERE id = ?
        """, (subject_id,)).fetchone()

        # Student information
        selected_student = conn.execute("""
            SELECT *
            FROM students
            WHERE id = ?
        """, (student_id,)).fetchone()

        # Attendance calculation
        summary = conn.execute("""
            SELECT

                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN status = 'Present'
                        THEN 1
                        ELSE 0
                    END
                ) AS present,

                SUM(
                    CASE
                        WHEN status = 'Absent'
                        THEN 1
                        ELSE 0
                    END
                ) AS absent

            FROM attendance

            WHERE subject_id = ?
            AND student_id = ?

        """, (
            subject_id,
            student_id
        )).fetchone()

        total = summary["total"] or 0
        present = summary["present"] or 0
        absent = summary["absent"] or 0

        if total > 0:
            percentage = (present / total) * 100

    conn.close()

    return render_template(
        "subject_report.html",

        subjects=subjects,
        students=students,

        selected_subject=selected_subject,
        selected_student=selected_student,

        total=total,
        present=present,
        absent=absent,
        percentage=percentage
    )

# =========================================================
# ALL ATTENDANCE PDF
# =========================================================

@app.route("/attendance_report/pdf")
def attendance_report_pdf():

    if not login_required():

        return redirect("/login")

    conn = get_db()

    report = conn.execute("""
        SELECT

            students.student_id,

            students.name,

            students.semester,

            COUNT(attendance.id) AS total_days,

            SUM(
                CASE
                    WHEN attendance.status = 'Present'
                    THEN 1
                    ELSE 0
                END
            ) AS present_days,

            SUM(
                CASE
                    WHEN attendance.status = 'Absent'
                    THEN 1
                    ELSE 0
                END
            ) AS absent_days

        FROM students

        LEFT JOIN attendance

        ON students.id = attendance.student_id

        GROUP BY students.id

        ORDER BY students.student_id
    """).fetchall()

    conn.close()

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    elements = []

    title_style = ParagraphStyle(
        name="TitleStyle",
        fontSize=16,
        alignment=1,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        name="SubtitleStyle",
        fontSize=12,
        alignment=1,
        spaceAfter=20
    )

    elements.append(
        Paragraph(
            "ONLINE ATTENDANCE MANAGEMENT SYSTEM",
            title_style
        )
    )

    elements.append(
        Paragraph(
            "ATTENDANCE SUMMARY REPORT",
            subtitle_style
        )
    )

    data = [[
        "Student ID",
        "Name",
        "Semester",
        "Total",
        "Present",
        "Absent",
        "Attendance %"
    ]]

    for student in report:

        total = student["total_days"] or 0

        present = student["present_days"] or 0

        absent = student["absent_days"] or 0

        percentage = (
            (present / total) * 100
            if total > 0 else 0
        )

        data.append([
            str(student["student_id"]),
            str(student["name"]),
            str(student["semester"]),
            str(total),
            str(present),
            str(absent),
            f"{percentage:.2f}%"
        ])

    table = Table(
        data,
        repeatRows=1
    )

    table.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#2E7D32")
        ),

        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white
        ),

        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        ),

        (
            "ALIGN",
            (0, 0),
            (-1, -1),
            "CENTER"
        ),

        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.grey
        ),

        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [
                colors.white,
                colors.HexColor("#E8F5E9")
            ]
        ),

        (
            "PADDING",
            (0, 0),
            (-1, -1),
            7
        )
    ]))

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="attendance_summary_report.pdf",
        mimetype="application/pdf"
    )


# =========================================================
# STUDENT WISE PDF
# =========================================================

@app.route("/student_report/pdf/<int:student_id>")
def student_report_pdf(student_id):

    if not login_required():

        return redirect("/login")

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (
        student_id,
    )).fetchone()

    if not student:

        conn.close()

        return "Student not found!"

    summary = conn.execute("""
        SELECT

            COUNT(*) AS total_days,

            SUM(
                CASE
                    WHEN status = 'Present'
                    THEN 1
                    ELSE 0
                END
            ) AS present_days,

            SUM(
                CASE
                    WHEN status = 'Absent'
                    THEN 1
                    ELSE 0
                END
            ) AS absent_days

        FROM attendance

        WHERE student_id = ?
    """, (
        student_id,
    )).fetchone()

    records = conn.execute("""
        SELECT

            attendance.attendance_date,

            subjects.name AS subject_name,

            attendance.status

        FROM attendance

        JOIN subjects

        ON attendance.subject_id = subjects.id

        WHERE attendance.student_id = ?

        ORDER BY
            attendance.attendance_date DESC
    """, (
        student_id,
    )).fetchall()

    conn.close()

    total = summary["total_days"] or 0

    present = summary["present_days"] or 0

    absent = summary["absent_days"] or 0

    percentage = (
        (present / total) * 100
        if total > 0 else 0
    )

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    elements = []

    title_style = ParagraphStyle(
        name="Title",
        fontSize=16,
        alignment=1,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        name="Subtitle",
        fontSize=12,
        alignment=1,
        spaceAfter=20
    )

    elements.append(
        Paragraph(
            "ONLINE ATTENDANCE MANAGEMENT SYSTEM",
            title_style
        )
    )

    elements.append(
        Paragraph(
            "STUDENT ATTENDANCE REPORT",
            subtitle_style
        )
    )

    student_info = [

        [
            "Student ID",
            str(student["student_id"])
        ],

        [
            "Student Name",
            str(student["name"])
        ],

        [
            "Department",
            str(student["department"])
        ],

        [
            "Semester",
            str(student["semester"])
        ],

        [
            "Section",
            str(student["section"])
        ]
    ]

    info_table = Table(
        student_info,
        colWidths=[120, 350]
    )

    info_table.setStyle(TableStyle([

        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.grey
        ),

        (
            "BACKGROUND",
            (0, 0),
            (0, -1),
            colors.HexColor("#E8F5E9")
        ),

        (
            "FONTNAME",
            (0, 0),
            (0, -1),
            "Helvetica-Bold"
        ),

        (
            "PADDING",
            (0, 0),
            (-1, -1),
            7
        )
    ]))

    elements.append(info_table)

    elements.append(
        Spacer(1, 20)
    )

    summary_data = [

        [
            "Total Class",
            "Present",
            "Absent",
            "Attendance %"
        ],

        [
            str(total),
            str(present),
            str(absent),
            f"{percentage:.2f}%"
        ]
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            117,
            117,
            117,
            119
        ]
    )

    summary_table.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#2E7D32")
        ),

        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white
        ),

        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        ),

        (
            "ALIGN",
            (0, 0),
            (-1, -1),
            "CENTER"
        ),

        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.grey
        ),

        (
            "PADDING",
            (0, 0),
            (-1, -1),
            8
        )
    ]))

    elements.append(summary_table)

    elements.append(
        Spacer(1, 25)
    )

    elements.append(
        Paragraph(
            "Attendance History",
            ParagraphStyle(
                name="History",
                fontSize=12,
                spaceAfter=10
            )
        )
    )

    data = [
        [
            "Date",
            "Subject",
            "Status"
        ]
    ]

    for record in records:

        data.append([
            str(record["attendance_date"]),
            str(record["subject_name"]),
            str(record["status"])
        ])

    history_table = Table(
        data,
        colWidths=[
            120,
            250,
            100
        ],
        repeatRows=1
    )

    history_table.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#2E7D32")
        ),

        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white
        ),

        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        ),

        (
            "ALIGN",
            (0, 0),
            (-1, -1),
            "CENTER"
        ),

        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.grey
        ),

        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [
                colors.white,
                colors.HexColor("#E8F5E9")
            ]
        ),

        (
            "PADDING",
            (0, 0),
            (-1, -1),
            7
        )
    ]))

    elements.append(history_table)

    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="student_attendance_report.pdf",
        mimetype="application/pdf"
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    create_tables()

    create_default_teacher()

    app.run(
        debug=True
    )