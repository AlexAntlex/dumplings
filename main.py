import datetime
import os
import requests
import random

from flask_login import AnonymousUserMixin
from flask import render_template, Flask, request, flash, g, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_restful import abort
from werkzeug.utils import redirect, secure_filename

from config import Config
from data import db_session
from data.group import Group
from data.posts import Post
from data.user_posts import PostUser
from data.users import User
from form.edit_group import ChangeIngoForm
from form.login import LoginForm
from form.post import PostForm
from form.register import RegisterForm
from form.delete import DeleteForm

app = Flask(__name__)
app.config.from_object(Config)


class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.id = '0'


login_manager = LoginManager()
login_manager.anonymous_user = Anonymous
login_manager.init_app(app)


#  Upload files
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


def main():
    db_session.global_init("db/users.sqlite")
    app.run()


@app.before_request
def before_request():
    g.user = current_user


@app.route('/game/<id>', methods=['GET', 'POST'])
def game(id):
    return render_template("game.html", id=id)


@app.route('/apps')
def apps():
    return render_template("apps.html")


@app.route("/", methods=['GET', 'POST'])
def index():
    session = db_session.create_session()
    if request.method == "POST":
        if request.form.get("options") == 'user':
            my = g.user.id
            posts = session.query(PostUser).filter(PostUser.autor_id != my).order_by(PostUser.id.desc())
            return render_template('start_page.html', posts=posts, check='checked', link='user')
        else:
            posts = session.query(Post).order_by(Post.id.desc())
            return render_template('start_page.html', posts=posts, check2='checked', link='group')
    return render_template('start_page.html')


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            avatar=url_for('static', filename='img/boy.png')
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(
            User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/delete", methods=['GET', 'POST'])
def delete():
    form = DeleteForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('delete.html', title='Deletion',
                                   form=form,
                                   message="Пароли не совпадают")
        else:
            session = db_session.create_session()
            my = g.user.id
            user = session.query(User).filter(User.id == my).first()
            if user.check_password(form.password.data):
                session.delete(user)
                session.commit()
                return redirect('/register')
    return render_template('delete.html', title='Deletion', form=form)


@app.route('/user/<id>', methods=['GET', 'POST'])
def user_profile(id):
    session = db_session.create_session()
    user = session.query(User).filter_by(id=id).first()
    form = PostForm()
    if user == None:
        flash('User ' + id + ' not found.')
        return render_template('login.html')
    else:
        you = user.name
        my = g.user.id
        info = user.about
        user_id = int(id)
        if my == user_id:
            if form.validate_on_submit():
                file = form.file_url.data
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    way_to_file = os.path.join(app.config['UPLOAD_FOLDER_USER'], filename)
                    file.save(way_to_file)
                    post = PostUser(text=form.text.data,
                                    date=datetime.datetime.now().strftime("%A %d %b %Y (%H:%M)"),
                                    autor_id=my,
                                    file=way_to_file)
                    session.add(post)
                    session.commit()
                    return redirect(f'{id}')
                elif file.filename == '':
                    post = PostUser(text=form.text.data,
                                    date=datetime.datetime.now().strftime("%A %d %b %Y (%H:%M)"),
                                    autor_id=my)
                    session.add(post)
                    session.commit()
                    return redirect(f'{id}')
            posts = session.query(PostUser).filter_by(autor_id=user_id).order_by(PostUser.id.desc())
            return render_template('profile_user.html', title=you, you=you, user_id=user_id, my_id=my, info=info,
                                   form=form, posts=posts, avatar=user.avatar, id=id)
        else:
            posts = session.query(PostUser).filter_by(autor_id=user_id).order_by(PostUser.id.desc())
            return render_template('profile_user.html', title=you, you=you, user_id=user_id, my_id=my, info=info,
                                   form=form, posts=posts, avatar=user.avatar, id=id)


@app.route('/post_edit/<int:id>', methods=['GET', 'POST'])
@login_required
def post_edit(id):
    form = PostForm()
    session = db_session.create_session()
    post = session.query(PostUser).filter_by(id=id).first()
    prev_text = post.text
    my = g.user.id
    if request.method == 'POST':
        new_text = request.form.get("area")
        file = form.file_url.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            way_to_file = os.path.join(app.config['UPLOAD_FOLDER_USER'], filename)
            file.save(way_to_file)
            post.text = new_text
            post.file = way_to_file
            session.commit()
            return redirect(f'/user/{g.user.id}')
        elif file.filename == '':
            post.text = new_text
            session.commit()
            return redirect(f'/user/{g.user.id}')
    return render_template('delete_post.html', form=form, prev_text=prev_text)


@app.route('/post_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def post_delete(id):
    session = db_session.create_session()
    posts = session.query(PostUser).filter(PostUser.id == id,
                                           PostUser.autor_id == g.user.id).first()
    if posts:
        session.delete(posts)
        session.commit()
    else:
        abort(404)
    return redirect(f'/user/{g.user.id}')


@app.route('/edit', methods=['GET', 'POST'])
def edit():
    form = ChangeIngoForm()
    user_id = g.user.id
    if request.method == "GET":
        session = db_session.create_session()
        user = session.query(User).filter_by(id=int(user_id)).first()
        if user:
            form.name.data = user.name
            form.info.data = user.about
            form.avatar.data = user.avatar
        else:
            os.abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter_by(id=int(user_id)).first()
        if user:
            way_to_file = user.avatar
            file = form.avatar.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                way_to_file = os.path.join(app.config['UPLOAD_FOLDER_USER'], filename)
                file.save(way_to_file)
            user.name = form.name.data
            user.about = form.info.data
            user.avatar = way_to_file
            session.commit()
            return redirect(f'/user/{user_id}')
        else:
            os.abort(404)
    num = random.randint(1, 35)
    name = "img/edit/edit" + str(num) + ".jpg"
    return render_template('edit_group.html', info=user.about, name=user.name, form=form, im_user=1, pic=name)


@app.route('/group/<int:id_group>', methods=['GET', 'POST'])
def group(id_group):
    session = db_session.create_session()
    user = session.merge(current_user)
    form = PostForm()
    my = g.user.id
    if form.validate_on_submit():
        way_to_file = ""
        file = form.file_url.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            way_to_file = os.path.join(app.config['UPLOAD_FOLDER_GROUP'], filename)
            file.save(way_to_file)
        post = Post(text=form.text.data,
                    date=datetime.datetime.now().strftime("%A %d %b %Y (%H:%M)"),
                    autor_id=id_group,
                    file=way_to_file)
        session.add(post)
        session.commit()
        return redirect(f'/group/{id_group}')
    posts = session.query(Post).filter(Post.autor_id == id_group).order_by(Post.id.desc())
    group_info = session.query(Group).filter_by(id=id_group).first()
    return render_template('group.html', title='Авторизация', form=form, posts=posts, info=group_info,
                           avatar=group_info.avatar, id=id_group, my=my,  user=user)


@app.route('/groups')
def list_group():
    session = db_session.create_session()
    groups = session.query(Group).all()
    user = session.merge(current_user)
    return render_template('group_list.html', title='you', groups=groups, user=user)


@app.route('/group_delete/<int:id_group>', methods=['GET', 'POST'])
def delete_group(id_group):
    session = db_session.create_session()
    group = session.query(Group).filter_by(id=id_group).first()
    if group:
        for post in session.query(Post).filter(Post.autor_id == id_group):
            session.delete(post)
        session.delete(group)
        session.commit()
    else:
        os.abort(404)
    return redirect('/')


@app.route('/group_edit/<int:id_group>', methods=['GET', 'POST'])
def edit_group(id_group):
    form = ChangeIngoForm()
    if request.method == "GET":
        session = db_session.create_session()
        group = session.query(Group).filter_by(id=id_group).first()
        if group:
            form.name.data = group.name
            form.info.data = group.info
            form.avatar.data = group.avatar
        else:
            os.abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        group = session.query(Group).filter_by(id=id_group).first()
        if group:
            way_to_file = group.avatar
            file = form.avatar.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                way_to_file = os.path.join(app.config['UPLOAD_FOLDER_GROUP'], filename)
                file.save(way_to_file)
            group.name = form.name.data
            group.info = form.info.data
            group.avatar = way_to_file
            session.commit()
            return redirect(f'/group/{id_group}')
        else:
            os.abort(404)
    num = random.randint(1, 21)
    name = "img/edit/edit" + str(num) + ".jpg"
    return render_template('edit_group.html', info=group, form=form, im_user=0, pic=name)


@app.route('/make_group', methods=['GET', 'POST'])
def make_group():
    form = ChangeIngoForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.merge(current_user)
        group = Group(
            name=form.name.data,
            info=form.info.data,
            avatar=url_for('static', filename='img/deer.png'),
            admin=g.user.id
        )
        session.add(group)
        user.follow(group)
        session.commit()
        return redirect(f'/group/{group.id}')
    return render_template('edit_group.html', title='Groups', form=form)


@app.route('/group_post_edit/<int:id>', methods=['GET', 'POST'])
def gr_post_edit(id):
    form = PostForm()
    session = db_session.create_session()
    post = session.query(Post).filter_by(id=id).first()
    prev_text = post.text
    if request.method == 'POST':
        new_text = request.form.get("area")
        file = form.file_url.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            way_to_file = os.path.join(app.config['UPLOAD_FOLDER_USER'], filename)
            file.save(way_to_file)
            post.text = new_text
            post.file = way_to_file
            session.commit()
            return redirect(f'/group/{post.autor_id}')
        elif file.filename == '':
            post.text = new_text
            session.commit()
            return redirect(f'/group/{post.autor_id}')
    return render_template('delete_post.html', form=form, prev_text=prev_text)


@app.route('/group_post_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def gr_post_delete(id):
    session = db_session.create_session()
    post = session.query(Post).filter(Post.id == id,
                                      Post.autor_id == g.user.id).first()
    if post:
        session.delete(post)
        session.commit()
    else:
        os.abort(404)
    return redirect(f'/group/{post.autor_id}')


@app.route('/follow/<group_id>')
@login_required
def follow(group_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    group = session.query(Group).filter_by(id=group_id).first()
    user.follow(group)
    session.commit()
    return redirect(f'/group/{group_id}')


@app.route('/unfollow/<group_id>')
def unfollow(group_id):
    session = db_session.create_session()
    user = session.merge(current_user)
    group = session.query(Group).filter_by(id=group_id).first()
    user.unfollow(group)
    session.commit()
    return redirect(f'/')


@app.route('/joke')
def random_joke():
    api_server = "https://icanhazdadjoke.com/slack"
    response = requests.get(api_server)
    json_response = response.json(strict=False)
    picture = json_response["attachments"][0]["text"]
    num = random.randint(1, 21)
    name = "img/laugh/laugh" + str(num) + ".jpg"
    return render_template("joke.html", joke=picture, name=name)


if __name__ == '__main__':
    app.debug = True
    main()
