from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from flask_login import UserMixin
from app import login
from sqlalchemy import Boolean, Float

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password) 

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username) 

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(140))
    type = db.Column(db.String(140))
    
    def __repr__(self):
        return format(self.id)   

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_img = db.Column(db.String)
    type = db.Column(db.String(140))
    is_continue = db.Column(Boolean, default=False)    
    is_double = db.Column(Boolean, default=False)
    id_img_double = db.Column(db.String)
    is_double_reference = db.Column(Boolean, default=False)
    
    def __repr__(self):
        return format(self.id) 
        
class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_test = db.Column(db.Integer)
    id_img1 = db.Column(db.Integer)
    id_img2 = db.Column(db.Integer)
    rating1 = db.Column(db.Float)
    rating2 = db.Column(db.Float)
    choice = db.Column(db.Integer)
    reason1 = db.Column(db.String)
    reason2 = db.Column(db.String)
    list_img = db.Column(db.String)
    list_rank = db.Column(db.String)
    
    def __repr__(self):
        return format(self.id)        
        
@login.user_loader
def load_user(id):
    return User.query.get(int(id))