import os


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dumplings'
    UPLOAD_FOLDER_GROUP = 'static/group_files'
    UPLOAD_FOLDER_USER = 'static/user_files'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'PNG'}