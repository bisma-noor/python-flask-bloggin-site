from flask import Flask, render_template, request, abort, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mail import Mail
from sqlalchemy import text
import json
import math

config_path = r"G:\PycharmProject\pythonProject\templates\config.json"

try:
    with open(config_path, 'r') as c:
        params = json.load(c)["params"]
    print("config.json loaded successfully!")

except Exception as e:
    print(f"Error loading config.json: {e}")

local_server=True
app = Flask(__name__)

app.secret_key='thoughtspot'

app.config.update(
    MAIL_SERVER= "smtp.gmail.com",
    MAIL_PORT = "587",
    MAIL_USE_SSL = False,
    MAIL_USE_TLS = True,
    MAIL_USERNAME = params['gmail-user'],
    MAIL_PASSWORD = params['gmail-password']
)
mail=Mail(app)
if(local_server):
    app.config["SQLALCHEMY_DATABASE_URI"] = params['local_url']
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_url']
db = SQLAlchemy(app)

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False)
    email = db.Column(db.String(50), nullable=False)
    phone_no = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.DateTime, nullable=True)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    img_file = db.Column(db.String(50), nullable=True)
    date = db.Column(db.String(12), nullable=True)

def reset_auto_increment():
    max_id = db.session.execute(text("SELECT MAX(sno) FROM posts")).fetchone()[0]
    if max_id is None:
        max_id = 0
    db.session.execute(text(f"ALTER TABLE posts AUTO_INCREMENT = {max_id + 1}"))
    db.session.commit()

@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts) / int(params['no_of_posts']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page - 1) * int(params['no_of_posts']):(page - 1) * int(params['no_of_posts']) + int(
        params['no_of_posts'])]
    if page == 1:
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif page == last:
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    show_prev = page > 1
    show_next = page < last

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next, show_prev=show_prev, show_next=show_next)

@app.route("/login")
def login():
    return render_template("login.html", params=params)

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route("/post/<string:post_slug>", methods=['Get'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    if not post:
        return "Post not found!", 404
    return render_template("post.html", params=params, post=post)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    # Check if the user is already logged in
    if "user" in session and session['user'] == params['admin_user']:
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    if request.method == "POST":
        username = request.form.get("uname")
        userpass = request.form.get("upass")

        print("Submitted Username:", username)
        print("Submitted Password:", userpass)
        print("Stored Username:", params['admin_user'])
        print("Stored Password:", params['admin_password'])

        if username == params['admin_user'] and userpass == params['admin_password']:
            session['user'] = username
            posts = Posts.query.all()
            return render_template("dashboard.html", params=params, posts=posts)
        else:
            return "Invalid username or password", 401

    return render_template("login.html", params=params)

@app.route("/about")
def About():
    return render_template("about.html",params=params)

@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def Edit(sno):
    if "user" in session and session['user'] == params['admin_user']:
      if request.method=="POST":
          box_title=request.form.get('title')
          slug= request.form.get('slug')
          content = request.form.get('content')
          img = request.form.get('img')
          date=datetime.now()
          post=Posts.query.filter_by(sno=sno).first()
          post.title=box_title
          post.slug=slug
          post.img_file=img
          post.date=date
          db.session.commit()
          return redirect('/dashboard')

      post = Posts.query.filter_by(sno=sno).first()
      return render_template("edit.html", params=params, post=post)

@app.route("/add", methods=['GET', 'POST'])
def Add():
    if "user" in session and session['user'] == params['admin_user']:
      if request.method=="POST":
          box_title=request.form.get('title')
          slug= request.form.get('slug')
          content = request.form.get('content')
          img = request.form.get('img')
          date = datetime.now()
          post = Posts(title=box_title, slug=slug, content=content, img_file=img, date=date)
          db.session.add(post)
          db.session.commit()
          return redirect('/dashboard')
      return render_template("add.html", params=params)

@app.route("/delete/<string:sno>", methods=['GET', 'POST'])
def Delete(sno):
    if "user" in session and session['user'] == params['admin_user']:
        post=Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        reset_auto_increment()
    return redirect('/dashboard')

@app.route("/contact", methods=['GET', 'POST'])
def Contact():
    if (request.method=="POST"):
        '''Add entity to database'''
        name=request.form.get('name')
        email=request.form.get('email')
        phone=request.form.get('phone')
        message=request.form.get('message')

        entry=Contacts(name=name, email=email, phone_no=phone, msg=message, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message(
            "New message from thoughtspot by "+name,
            sender=email,
            recipients=[params['gmail-user']],
            body = message + "\n" + phone
        )

    return render_template("contact.html",params=params)

@app.route("/post")
def Post():
    post = Posts.query.first()
    if not post:
        return "Post not found!", 404
    return render_template("post.html", params=params, post=post)

if __name__ == "__main__":
    app.run(debug=True)