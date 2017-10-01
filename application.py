## for backend and site building ##
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
## for database operations ##
from models import Base, Category, Item
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
## for oauth login ##
from flask import session as login_session
from flask import make_response
import random, string
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import httplib2, json, requests

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Project"

engine = create_engine('sqlite:///itemCatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


### OAuth login code ###
## GCONNECT ##
# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state, CLIENT_ID=CLIENT_ID)


@app.route('/gconnect', methods=['POST'])
def gconnect():
	# Check if state from login page matches state created above
	# If yes, get the one time code from google login
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	code = request.data
	
	# Try to exchange the one time code with a creditials object
	try:
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	
	# Check that credentials object has a valid access token
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])

	# Check for errors with access token info
	if result.get('error') is not None:
		reponse = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type'] = 'application/json'

	# Verify that the access token is valid for the intended user
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(json.dumps("Token's user ID doesn't match given user ID."), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Verify that the access token is valid for this app
	if result['issued_to'] != CLIENT_ID:
		response = make_response(json.dumps("Token's client ID does not match app's"), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Check to see if user is already logged in
	stored_credentials = login_session.get('credentials')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_credentials is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'), 200)
		response.headers['Content-Type'] = 'application/json'

	# Put the access token into the session object
	login_session['credentials'] = credentials.access_token
	login_session['gplus_id'] = gplus_id

	# Get user info from Google
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': access_token, 'alt': 'json'}
	
	answer = requests.get(userinfo_url, params=params)
	data = answer.json()

	login_session['username'] = data["name"]
	login_session['email'] = data["email"]

	output =''
	output += '<h1>Welcome, '
	output += login_session['username']
	output += '!</h1>'

	flash("you are now logged in as %s" % login_session['username'])
	return output
## GCONNECT END ##
### OAuth login code end ###


## JSON endpoints for db items ##
@app.route('/category.json')
def categoriesJSON():
	categories = session.query(Category).all()
	for c in categories:
		return jsonify(Category=[c.serialize for c in categories])


## Query all entries in Category table, display in template ##
@app.route('/')
@app.route('/category/')
def showCategories():
	categories = session.query(Category).all()
	return render_template('categories.html', categories=categories)


## Create new category ##
# Adds new entry to Category table #
@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
	if request.method == 'POST':
		newCategory = Category(name=request.form['name'])
		session.add(newCategory)
		session.commit()
		flash("category add success!")
		return redirect(url_for('showCategories'))
	else:
		return render_template('newCategory.html')


## Edit existing category name ##
# URLs contain category id, used to get entry from Category table and commit changes to name #
@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
	editedCategory = session.query(Category).filter_by(id=category_id).one()

	if request.method == 'POST':
		if request.form['name']:
			editedCategory.name = request.form['name']
			session.add(editedCategory)
			session.commit()
			flash("category edit success!")
			return redirect(url_for('showCategories'))
	else:
		return render_template('editCategory.html', category=editedCategory)


## Delete existing category ##
# Get entry from Category table, delete, and commit deletion #
@app.route('/category/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_id):
	categoryToDelete = session.query(Category).filter_by(id=category_id).one()

	if request.method == 'POST':
		if request.form['confirm']:
			session.delete(categoryToDelete)
			session.commit()
			flash("category delete success!")
			return redirect(url_for('showCategories'))
	else:
		return render_template('deleteCategory.html', category=categoryToDelete)


## Clicking on a category name will show a list of items in that category ##
# Each item is associated with a category id on creation, used to build this list #
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/items/')
def showItems(category_id):
	category = session.query(Category).filter_by(id=category_id).one()
	items = session.query(Item).filter_by(category_id=category_id).all()
	return render_template('items.html', items=items, category=category)


## Add a new item to catalog ##
# Category_id will keep the items arranged under the top level categories #
@app.route('/category/<int:category_id>/items/new/', methods=['GET', 'POST'])
def newItem(category_id):
	category = session.query(Category).filter_by(id=category_id).one()

	if request.method == 'POST':
		newItem = Item(name=request.form['name'], description=request.form['description'], category_id=category_id)
		session.add(newItem)
		session.commit()
		flash("item add success!")
		return redirect(url_for('showItems', category_id=category_id))
	else:
		return render_template('newItem.html', category=category)


## Edit existing item in catalog ##
# Gets item to be edited and passes to form to pre-fill inputs #
@app.route('/category/<int:category_id>/items/<int:item_id>/edit/', methods=['GET', 'POST'])
def editItem(category_id, item_id):
	editedItem = session.query(Item).filter_by(category_id=category_id, id=item_id).one()

	if request.method == 'POST':
		if request.form['name']:
			editedItem.name = request.form['name']
		if request.form['description']:
			editedItem.description = request.form['description']

		session.add(editedItem)
		session.commit()
		flash("item edit success!")
		return redirect(url_for('showItems', category_id=category_id))
	else:
		return render_template('editItem.html', category_id=category_id, item=editedItem)


## Delete existing item in catalog ##
# Sends item object to be deleted, category_id is for redirecting to correct category afterwards #
@app.route('/category/<int:category_id>/items/<int:item_id>/delete/', methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
	itemToDelete = session.query(Item).filter_by(category_id=category_id, id=item_id).one()

	if request.method == 'POST':
		if request.form['confirm']:
			session.delete(itemToDelete)
			session.commit()
			flash("item delete success!")
			return redirect(url_for('showItems', category_id=category_id))
	else:
		return render_template('deleteItem.html', category_id=category_id, item=itemToDelete)


if __name__ == '__main__':
	app.debug = True
	app.secret_key = 'super secret key'
	app.run(host='0.0.0.0', port=8000)