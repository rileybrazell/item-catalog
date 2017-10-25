# Item Catalog
For Udacity's Full Stack Web Developer course I created a webapp to access 
the contents of an SQLite database, allowing an OAuth2.0 logged-in user to 
create, edit, and delete database entries. This app was written in Python 
using Flask and SQLAlchemy for the backend with Bootstrap for responsive design.

## Getting Started
Requires [Flask](http://flask.pocoo.org/docs/0.10/), [SQLAlchemy](https://www.sqlalchemy.org/), and [oauth2client](https://github.com/google/oauth2client)
- Clone or download and unzip files
- `pip install flask sqlalchemy` in the same directory as `application.py`
- `python models.py` to build the database
- `python application.py` and open a browser to `localhost:8000` to access app
- Login with Google to create, edit, and delete database items

### What I Learned
In the course of building this app I learned the structure of a modern webapp.
Using Flask made it possible to present HTML templates based on user input and 
to interact with a database using SQLAlchemy. I also learned how OAuth 2.0
authentication with Google works and how to use it to create a local permissions 
system.
