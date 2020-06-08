import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    user, password = 'bflopz', 'hackmeplz'
    host = 'bflopz.mysql.pythonanywhere-services.com'
    db = 'bflopz$progetto' # dbFlask was created as a PythonAnywhere MySQL database

    # connection string: mysql://user:pword@host/db
    SQLALCHEMY_DATABASE_URI = 'mysql://{0}:{1}@{2}/{3}'.format(user, password, host, db)

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    #SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #    'sqlite:///' + os.path.join('/home/bflopz/', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
