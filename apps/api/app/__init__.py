from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

def create_app():
   app = Flask(__name__)
   CORS(app) # Enable CORS for all routes

   # import configurations
   app.config.from_object("app.config.Config")
   
   # Initialize DB (uncomment when config is ready)
   # db = SQLAlchemy(app)

   # Register Blueprints
   from app.routes import main
   app.register_blueprint(main)

   return app
