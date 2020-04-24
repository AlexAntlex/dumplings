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


class Anonymous(AnonymousUserMixin):  # если пользователь не зашел в свою учетку
    def __init__(self):               # его id становится 0
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


@app.route('/game/<id>', methods=['GET', 'POST'])  # раздел с игрой, подключаем шаблон html,
def game(id):                                      # передаем id, подключается игра из списка
    return render_template("game.html", id=id)


@app.route('/apps')  # страница со списком игр
def apps():
    return render_template("apps.html")


@app.route("/", methods=['GET', 'POST'])     # стартовая страница с отображением последних постов на сайте
def index():                                 # не показывает собственные посты, есть возможность показывать посты
    session = db_session.create_session()    # отдельно групп или отдельно пользователей
    if request.method == "POST":             # если пользователь не зашел в акк, то показываются все посты
        if request.form.get("options") == 'user':
            my = g.user.id
            posts = session.query(PostUser).filter(PostUser.autor_id != my).order_by(PostUser.id.desc())
            return render_template('start_page.html', posts=posts, check='checked', link='user')
        else:
            posts = session.query(Post).order_by(Post.id.desc())
            return render_template('start_page.html', posts=posts, check2='checked', link='group')
    return render_template('start_page.html')


@app.route('/register', methods=['GET', 'POST'])  # страница регистрации, подключает форму регистрации
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:  # проверка на парвильность пароля
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():  # проверка на наличие пользователя
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            avatar=url_for('static', filename='img/boy.png')
        )
        user.set_password(form.password.data)  # заносит данные в бд и перенаправляет на страницу с логином
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])  # страница с логином, вызывает форму логина и шаблон
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(
            User.email == form.email.data).first()
        if user and user.check_password(form.password.data):  # проверка на правильность пароля
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')  # при выходе из учетки идет перенаправление на стартовую страницу
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/delete", methods=['GET', 'POST'])  # удаление страницы, шаблон с удалением + форма
def delete():
    form = DeleteForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('delete.html', title='Deletion',  # проверка на правильность пароля
                                   form=form,
                                   message="Пароли не совпадают")
        else:
            session = db_session.create_session()
            my = g.user.id
            user = session.query(User).filter(User.id == my).first()
            if user.check_password(form.password.data):
                session.delete(user)
                session.commit()
                return redirect('/register')  # при совпадении данных перенаправляет на страницу регистрации
    return render_template('delete.html', title='Deletion', form=form)


@app.route('/user/<id>', methods=['GET', 'POST'])  # загрузка профиля пользователя
def user_profile(id):
    session = db_session.create_session()
    user = session.query(User).filter_by(id=id).first()
    form = PostForm()  # форма с постами
    if user == None:
        flash('User ' + id + ' not found.')
        return render_template('login.html')
    else:
        you = user.name                            # если пользователь и текущий юзер совпадают
        my = g.user.id                             # добавляется возможность делать посты + редактировать/удалять
        info = user.about
        user_id = int(id)
        if my == user_id:
            if form.validate_on_submit():          # добавление поста в бд
                file = form.file_url.data          # если есть картинка
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
                elif file.filename == '':          # если картинки нет
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


@app.route('/post_edit/<int:id>', methods=['GET', 'POST'])  # страница с редактированием поста, имеет свой шаблон
@login_required                                             # редактирует пост, который находит в бд
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


@app.route('/post_delete/<int:id>', methods=['GET', 'POST'])  # удаление поста из бд
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


@app.route('/edit', methods=['GET', 'POST'])  # редакт профиля, изменяет данные в базе данных
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


@app.route('/group/<int:id_group>', methods=['GET', 'POST'])  # страница с определенной группой
def group(id_group):                                          # возможность писать посты как у юзера и редачить их
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


@app.route('/groups')  # список групп, на которые подписан юзер
def list_group():
    session = db_session.create_session()
    groups = session.query(Group).all()
    user = session.merge(current_user)
    return render_template('group_list.html', title='you', groups=groups, user=user)


@app.route('/group_delete/<int:id_group>', methods=['GET', 'POST'])  # удаление группы из базы данных
def delete_group(id_group):
    session = db_session.create_session()
    group = session.query(Group).filter_by(id=id_group).first()
    if group:
        for post in session.query(Post).filter(Post.autor_id == id_group):
            session.delete(post)                                     # автоматически удаляет все посты из базы данных
        session.delete(group)
        session.commit()
    else:
        os.abort(404)
    return redirect('/')


@app.route('/group_edit/<int:id_group>', methods=['GET', 'POST'])  # редактирование информации о группе
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
    num = random.randint(1, 35)       # чтобы не было пусто, отображает рандомные картинки из специальной папки
    name = "img/edit/edit" + str(num) + ".jpg"
    return render_template('edit_group.html', info=group, form=form, im_user=0, pic=name)


@app.route('/make_group', methods=['GET', 'POST'])  # создание новой группы с автоматическим указанием админа
def make_group():
    form = ChangeIngoForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.merge(current_user)
        group = Group(
            name=form.name.data,
            info=form.info.data,
            avatar=url_for('static', filename='img/deer.png'),  # внесение в бд со стандартной аватаркой
            admin=g.user.id
        )
        session.add(group)
        user.follow(group)
        session.commit()
        return redirect(f'/group/{group.id}')
    return render_template('edit_group.html', title='Groups', form=form)


@app.route('/group_post_edit/<int:id>', methods=['GET', 'POST'])  # редакт поста в группе, тот же шаблон, что у юзера
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


@app.route('/group_post_delete/<int:id>', methods=['GET', 'POST'])  # удаление поста в группе аналогично с удалением поста юзера
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


@app.route('/joke')  # страница с шутками, подключает api, достающий рандомную шутку из базы
def random_joke():   # добавляет рандомную картинку смайлика из папки
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
