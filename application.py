from flask import Flask, render_template, request, redirect, jsonify, url_for

from models import Base, Category, Item
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

engine = create_engine('sqlite:///itemCatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


## Query all entries in Category table, display in template ##
@app.route('/')
@app.route('/category/')
def showCategories():
	categories = session.query(Category).all()
	return render_template('categories.html', categories=categories)


## Clicking on a category name will show a list of items in that category ##
# Each item is associated with a category id on creation, used to build this list
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/items/')
def showItems(category_id):
	category = session.query(Category).filter_by(id=category_id).one()
	items = session.query(Item).filter_by(category_id=category_id).all()
	return render_template('items.html', items=items, category=category)


if __name__ == '__main__':
	app.debug = True
	app.run(host='0.0.0.0', port=8000)