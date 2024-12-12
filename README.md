This is a university course system application implemented using python, flask, and sqlalchemy.

How to use:

1. Run app.py
2. Open your browser and go to http://<your-server-ip>:5001

To drop existing database, uncomment the following code block in `app.py` and rerun.
'''
with app.app_context():
    db.drop_all()
    db.create_all()
'''

