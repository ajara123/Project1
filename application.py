import os
from statistics import mean

from flask import Flask, session, render_template, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
	#have to think if the user is new and wants to signup instead login
    return render_template('index.html')

@app.route("/login", methods=["POST"])
def login():
	username=request.form.get("username")
	password=request.form.get("password")
	if db.execute("SELECT * FROM users WHERE username = :username AND password = :password", {"username": username, "password": password}).rowcount == 0:
		return render_template("error.html", message="Password or username is not correct")
	session["username"]=username
	return render_template('welcome.html', logged_user=session["username"])

@app.route("/search", methods=["POST"])
def search():
	isbn=request.form.get("isbn")
	title=request.form.get("title")
	author=request.form.get("author")
	if db.execute("SELECT * FROM books WHERE isbn = :isbn OR author = :author OR title = :title", {"isbn":isbn,"author":author,"title":title }).rowcount == 0:
		return render_template ("error.html", message = "Search details are incorrect, please check")
	else:
		books=db.execute("SELECT isbn, title, author FROM books WHERE isbn = :isbn OR author = :author OR title = :title", {"isbn":isbn, "author":author,"title":title}).fetchall()
		return render_template("result.html", books=books)

@app.route("/search/<string:book_isbn>", methods=["GET","POST"])
def book(book_isbn):

	book=db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": book_isbn }).fetchone()
	
	user=session["username"]

	if request.method == "POST":
		user_review=db.execute("SELECT review, score FROM reviews WHERE user_id=:user AND book=:book_id", {"user": user, "book_id":book_isbn}).fetchone()
		if request.form['submit']== 'text':
			new_review = request.form.get("new_review")
			user=session["username"]

			if user_review == None:
				db.execute("INSERT INTO reviews (user_id, book, review) VALUES (:user_id, :book, :review)", {"user_id":user, "book":book.isbn, "review": new_review})
				db.commit()
			elif user_review.review==None:
				db.execute("UPDATE reviews SET review=:new_review WHERE user_id=:user AND book=:book_id", {"new_review":new_review, "user":user, "book_id":book_isbn})
				db.commit()
			else:
				return render_template("error.html", message="You have already submitted review")
		
		if request.form['submit']=='scale':
			option=int(request.form.getlist("inlineRadioOptions")[0])
			user=session["username"]
			
			if user_review==None:
				db.execute("INSERT INTO reviews (user_id, book, score) VALUES (:user_id, :book, :score)", {"user_id":user, "book":book_isbn, "score": option})
				db.commit()
			elif user_review.score==None:
				db.execute("UPDATE reviews SET score=:score WHERE user_id=:user AND book=:book_id", {"score":option, "user":user, "book_id":book_isbn})
				db.commit()
			else:
				return render_template("error.html", message="You have already submitted rating")

	reviews=db.execute("SELECT review from reviews WHERE book = :isbn AND review <> 'None'", {"isbn": book_isbn }).fetchall()
	ratings=db.execute("SELECT score from reviews WHERE book=:isbn AND score in (1,2,3,4,5)", {"isbn": book_isbn}).fetchall()
	
	list_scores=[]
	number_rating=0
	for rating in ratings:
		list_scores.append(rating.score)

	if list_scores==[]:
		average_score="No ratings yet"
	else:
		average_score=mean(list_scores)
		number_rating=len(list_scores)
	
		
	if reviews==[]:
		reviews=["No reviews yet"]	
	return render_template("book.html", book=book, reviews=reviews, average_score=average_score, number_rating=number_rating)

@app.route("/signup")
def signup():
	return render_template('signup.html')

@app.route("/register", methods=["POST"])
def register():
	username=request.form.get("username")
	password=request.form.get("password")
	password_2=request.form.get("password_2")
	session["username"]=username
	if password!=password_2:
		return render_template("error.html", message="please check password")
	if db.execute("SELECT * FROM users WHERE username=:username", {"username":username}).rowcount >= 1:
		return render_template("error.html", message="User with such username already exists")
	else:
		db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username":username, "password":password})
	db.commit()
	return render_template("welcome.html", logged_user=username)

@app.route("/api/<string:book_isbn>", methods=["GET"])
def api_request(book_isbn):
	if db.execute("SELECT isbn, title, author, year FROM books WHERE isbn=:book_isbn", {"book_isbn": book_isbn}).rowcount==0:
		return render_template("error.html", message="404 Error")
	else:
		book_details=db.execute("SELECT isbn, title, author, year FROM books WHERE isbn=:book_isbn", {"book_isbn": book_isbn}).fetchone()
		book_reviews=db.execute("SELECT book, review, score FROM reviews WHERE book=:book_isbn", {"book_isbn":book_isbn}).fetchall()
		list_scores=[]
		for book_review in book_reviews:
			if book_review.score!=None:
				list_scores.append(book_review.score)
		if list_scores==[]:
			average_score=None
			review_count=0
		else:
			average_score=mean(list_scores)
			review_count=len(list_scores)
		return render_template('api.html', book_details=book_details, average_score=average_score, review_count=review_count)





