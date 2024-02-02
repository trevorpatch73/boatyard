from flask import Flask
import secrets
from os import path
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

db = SQLAlchemy()
DB_NAME = "database.db"

def create_database(app):
    if not path.exists('application/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')
    else:
        print('Database Exists!')
        
def initiate_functions(app):
    from .initiate import EnvironmentTypesTableInitiate, LocationItemsTableInitiate, TenantItemsTableInitiate, ZoneItemsTableInitiate
    EnvironmentTypesTableInitiate()
    LocationItemsTableInitiate()
    TenantItemsTableInitiate()
    ZoneItemsTableInitiate()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = str(secrets.token_hex(128))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True
    db.init_app(app)
    
    #migrate = Migrate(app, db)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User

    with app.app_context():
        db.create_all()
        initiate_functions(app) 

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app
