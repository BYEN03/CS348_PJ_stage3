from flask import Flask, request, flash, url_for, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from sqlalchemy import Index

app = Flask(__name__, template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///courses.db'
app.secret_key = "secret_key"
db = SQLAlchemy(app)


# Course Model
class Course(db.Model):
    course_id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(200), nullable=False)
    instructor = db.Column(db.String(200), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)  # New field for capacity

    def __init__(self, course_name, instructor, credits, capacity):
        self.course_name = course_name
        self.instructor = instructor
        self.credits = credits
        self.capacity = capacity

    @property
    def current_enrollment(self):
        # Calculate the current enrollment count for this course
        return Enrollment.query.filter_by(course_id=self.course_id).count()


# Student Model
class Student(db.Model):
    student_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(200), nullable=False)
    last_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Password field

    __table_args__ = (
        Index('idx_last_name', 'last_name'),
    )

    def __init__(self, first_name, last_name, email, password):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password


# Enrollment Model
class Enrollment(db.Model):
    enrollment_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    #__table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='unique_enrollment'),)
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', name='unique_enrollment'),
        # Index on student_id and course_id
        Index('idx_student_id', 'student_id'),
        Index('idx_course_id', 'course_id'),
        # compound index on both
        Index('idx_student_course', 'student_id', 'course_id')
    )

    def __init__(self, student_id, course_id):
        self.student_id = student_id
        self.course_id = course_id


# Routes

# Show all courses, students, and enrollments
@app.route('/')
def show_all():
    courses = Course.query.all()
    students = Student.query.all()
    enrollments = db.session.query(Enrollment, Student, Course).join(Student).join(Course).all()

    # Create a dictionary to store the number of students enrolled in each course
    course_enrollment_counts = {
        course.course_id: db.session.execute(text("SELECT COUNT(*) FROM enrollment WHERE course_id = :course_id"), {'course_id': course.course_id}).scalar()
        for course in courses
    }

    return render_template('show_all.html', courses=courses, students=students, enrollments=enrollments, course_enrollment_counts=course_enrollment_counts)

# Add a new course
@app.route('/new_course', methods=['GET', 'POST'])
def new_course():
    if request.method == 'POST':
        if not request.form['course_name'] or not request.form['instructor'] or not request.form['credits'] or not request.form['capacity']:
            flash('Please enter all the fields', 'error')
        else:
            course = Course(request.form['course_name'],request.form['instructor'], int(request.form['credits']), int(request.form['capacity']))
            db.session.add(course)
            db.session.commit()
            return redirect(url_for('show_all'))
    return render_template('new_course.html')


# Edit a course
@app.route('/edit_course/<int:id>', methods=['GET', 'POST'])
def edit_course(id):
    course = Course.query.get_or_404(id)
    if request.method == 'POST':
        course.course_name = request.form['course_name']
        course.instructor = request.form['instructor']
        course.credits = request.form['credits']
        course.capacity = int(request.form['capacity'])  # Update capacity
        db.session.commit()
        return redirect(url_for('show_all'))
    return render_template('edit_course.html', course=course)

# Delete a course
@app.route('/delete_course/<int:id>', methods=['POST'])
def delete_course(id):
    course = Course.query.get_or_404(id)
    db.session.delete(course)
    db.session.commit()
    return redirect(url_for('show_all'))


# Edit a student
@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    student = Student.query.get_or_404(id)
    if request.method == 'POST':
        entered_password = request.form['password']
        if not entered_password or entered_password != student.password:  # Check password
            flash('Incorrect password', 'error')
        else:
            student.first_name = request.form['first_name']
            student.last_name = request.form['last_name']
            student.email = request.form['email']
            db.session.commit()
            return redirect(url_for('show_all'))
    return render_template('edit_student.html', student=student)

# Delete a student
@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    if 'password' not in request.form:
        flash('Password is required to delete a student.', 'error')
        return redirect(url_for('show_students'))

    entered_password = request.form['password']
    
    student = Student.query.get_or_404(id)
    
    if entered_password != student.password:
        flash('Incorrect password.', 'error')
    else:
        db.session.delete(student)
        db.session.commit()
        flash('Student deleted successfully.', 'success')
    
    return redirect(url_for('show_all'))


# Show all students
@app.route('/students')
def show_students():
    return render_template('show_students.html', students=Student.query.all())

# Add a new student
@app.route('/new_student', methods=['GET', 'POST'])
def new_student():
    if request.method == 'POST':
        if not request.form['first_name'] or not request.form['last_name'] or not request.form['email'] or not request.form['password']:
            flash('Please enter all the fields', 'error')
        else:
            student = Student(request.form['first_name'], request.form['last_name'], request.form['email'], request.form['password'])
            db.session.add(student)
            db.session.commit()
            return redirect(url_for('show_all'))
    return render_template('new_student.html')


@app.route('/enroll', methods=['GET', 'POST'])
def enroll():
    if request.method == 'POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']
        try:
            with db.session.begin():  # Explicit transaction
                #course = db.session.query(Course).with_for_update().get(course_id)  # Lock the row
                course = db.session.execute(
                    db.select(Course).where(Course.course_id == course_id).with_for_update()
                    ).scalar_one_or_none()

                #course = db.session.get(Course, course_id)
                if not course:
                    flash('Course not found', 'error')
                    return redirect(url_for('show_all'))
                
                if course.current_enrollment >= course.capacity:
                    flash('Course capacity reached. Cannot enroll more students.', 'error')
                else:
                    enrollment = Enrollment(student_id=student_id, course_id=course_id)
                    db.session.add(enrollment)
                db.session.commit()
                flash('Student enrolled successfully!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('This student is already enrolled in this course.', 'error')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('show_all'))

    students = Student.query.all()
    courses = Course.query.all()
    return render_template('enroll.html', students=students, courses=courses)


@app.route('/delete_enrollment/<int:id>', methods=['POST'])
def delete_enrollment(id):
    if 'password' not in request.form:
        flash('Password is required to delete an enrollment.', 'error')
        return redirect(url_for('show_all'))

    entered_password = request.form['password']
    
    enrollment = Enrollment.query.get_or_404(id)
    student = Student.query.get_or_404(enrollment.student_id)

    
    if entered_password != student.password:
        flash('Incorrect password.', 'error')
    else:
        db.session.delete(enrollment)
        db.session.commit()
        flash('Enrollment deleted successfully!', 'success')
    
    return redirect(url_for('show_all'))


# Sorting students alphabetically by last_name
@app.route('/sort_students', methods=['GET'])
def sort_students():
    try:
        # Use text() to declare the SQL expression
        sorted_students = db.session.execute(text("SELECT * FROM student ORDER BY last_name ASC")).fetchall()
        sorted_courses = db.session.execute(text("SELECT * FROM course")).fetchall()  
        enrollments = db.session.query(Enrollment, Student, Course).join(Student).join(Course).all()  
        course_enrollment_counts = {
           course.course_id: db.session.query(Enrollment).filter_by(course_id=course.course_id).count()
            for course in sorted_courses
        }
        return render_template('show_all.html', courses=sorted_courses, students=sorted_students, 
                               enrollments=enrollments, course_enrollment_counts=course_enrollment_counts)

    except SQLAlchemyError as e:
        error_message = f"An error occurred while sorting students: {str(e)}"  
        flash(error_message) 
        print(error_message)  # Print the error message to the terminal
        return redirect(url_for('show_all'))

# sort students by student_id
@app.route('/sort_students_id', methods=['GET'])
def sort_students_id():
    try:
        sorted_students = db.session.execute(text("SELECT * FROM student ORDER BY student_id ASC")).fetchall()
        sorted_courses = db.session.execute(text("SELECT * FROM course")).fetchall()  
        enrollments = db.session.query(Enrollment, Student, Course).join(Student).join(Course).all()
        course_enrollment_counts = {
           course.course_id: db.session.query(Enrollment).filter_by(course_id=course.course_id).count()
            for course in sorted_courses
        }
        return render_template('show_all.html', courses=sorted_courses, students=sorted_students, enrollments=enrollments, course_enrollment_counts=course_enrollment_counts)

    except SQLAlchemyError as e:
        error_message = f"An error occurred while sorting students: {str(e)}"  
        flash(error_message) 
        print(error_message) 
        return redirect(url_for('show_all'))

'''
# report
@app.route('/student_report', methods=['GET', 'POST'])
def student_report():
    if request.method == 'POST':
        student_id = request.form['student_id']
        print("id:      " + student_id)
        student = Student.query.filter_by(student_id=student_id).first()        
        total_credits = db.session.query(db.func.sum(Course.credits)).join(Enrollment).filter(Enrollment.student_id == student_id).scalar()
        # Courses enrolled
        courses = db.session.query(Course, Enrollment.enrollment_date).join(Enrollment).filter(Enrollment.student_id == student_id).all()

        return render_template('student_report.html', student=student, total_credits=total_credits, courses=courses)

    print("       0")
    students = Student.query.all()
    return render_template('student_report_form.html', students=students)
'''


@app.route('/student_report', methods=['GET', 'POST'])
def student_report():
    students = Student.query.all()
    courses = Course.query.all()
    enrollment_info = None
    total_enrolled_courses = 0
    popularity = None
    recommended_courses = []

    if request.method == 'POST':
        student_id = request.form['student_id']
        student = Student.query.filter_by(student_id=student_id).first()   
        #total_credits = db.session.query(db.func.sum(Course.credits)).join(Enrollment).filter(Enrollment.student_id == student_id).scalar()
        total_credits = db.session.execute(text("SELECT SUM(c.credits) FROM enrollment e JOIN course c ON e.course_id = c.course_id WHERE e.student_id = :student_id"),
                                  {'student_id': student_id}).scalar()

        course_id = request.form['course_id']
        course = Course.query.filter_by(course_id=course_id).first()
        # Fetch the selected student's total enrolled courses
        #total_enrolled_courses = db.session.query(Enrollment).filter_by(student_id=student_id).count()
        total_enrolled_courses = db.session.execute(text("SELECT COUNT(*) FROM enrollment WHERE student_id = :student_id"), {'student_id': student_id}).scalar()


        # Find the matching enrollment
        '''
        enrollment_info = db.session.query(Enrollment, Course).join(Course).filter(
            Enrollment.student_id == student_id, Enrollment.course_id == course_id
        ).first()
        '''
        enrollment_info = db.session.execute(text("SELECT * FROM enrollment e JOIN course c ON e.course_id = c.course_id WHERE e.student_id = :student_id AND e.course_id = :course_id"),
                                    {'student_id': student_id, 'course_id': course_id}).fetchone()


        if enrollment_info:
            # Calculate course popularity
            current_enrollment = course.current_enrollment
            popularity = round((float(current_enrollment) / course.capacity) * 100, 2) if course.capacity > 0 else 0

            # Get instructor's other courses for recommendation
            recommended_courses = Course.query.filter(
                Course.instructor == course.instructor, Course.course_id != course_id
            ).all()
        
        return render_template('student_report.html', student=student, total_credits=total_credits, course=course, popularity=popularity,
                               courses=courses, enrollment_info=enrollment_info, total_enrolled_courses=total_enrolled_courses, recommended_courses=recommended_courses)

    return render_template(
        'student_report_form.html',
        students=students,
        courses=courses,
        enrollment_info=enrollment_info,
        total_enrolled_courses=total_enrolled_courses,
        recommended_courses=recommended_courses
    )

#drop existing db

with app.app_context():
    db.drop_all()
    db.create_all()


# Run the application
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    #app.run(debug=True)
    app.run(host='0.0.0.0', port=5001)
