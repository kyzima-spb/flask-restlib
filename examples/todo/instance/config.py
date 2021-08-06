import os


instance_dir = os.path.abspath(os.path.dirname(__file__))


SQLALCHEMY_DATABASE_URI = f'sqlite:///{instance_dir}/db.sqlite3'
SQLALCHEMY_TRACK_MODIFICATIONS = False
