## for backend and site building ##
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
## for database operations ##
from models import Base, Category, Item, User
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

## GCONNECT START ##

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

	user_id = getUserID(data["email"])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	flash("you are now logged in as %s" % login_session['username'])
	return output

## GCONNECT END ##


## GDISCONNECT START ##

@app.route('/gdisconnect')
def gdisconnect():
	# Check if user is connected, only disconnect a connected user
	credentials = login_session.get('credentials')
	if credentials is None:
		response = make_response(json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	# Use HTTP GET to revoke current token with Google
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % credentials
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]

	if result['status'] == '200':
		# Reset the user's session
		del login_session['credentials']
		del login_session['gplus_id']
		del login_session['username']
		del login_session['email']

		response = make_response(json.dumps('Successfully disconnected.'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response
	else:
		# If the token was invalid for any reason
		response = make_response(json.dumps('Failed to revoke token for given user'), 400)
		response.headers['Content-Type'] = 'application/json'
		return response

## GDISCONNECT END ##


## User functions START ##

def createUser(login_session):
	newUser = User(name=login_session['username'], email=login_session['email'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email=login_session['email']).one()
	return user.id


def getUserInfo(user_id):
	user = session.query(User).filter_by(id=user_id).one()
	return user


def getUserID(email):
	try:
		user = session.query(User).filter_by(email=email).one()
		return user_id
	except:
		return None

## User functions END ##

### OAuth login code end ###


### JSON endpoints START ###

## All categories ##
@app.route('/JSON')
@app.route('/category/JSON')
def categoriesJSON():
	categories = session.query(Category).all()
	return jsonify(Category=[c.serialize for c in categories])


## All items in a category ##
@app.route('/category/<int:category_id>/JSON')
def categoryItemsJSON(category_id):
	items = session.query(Item).filter_by(category_id=category_id).all()
	return jsonify(Item=[i.serialize for i in items])


## Single item ##
@app.route('/category/<int:category_id>/items/<int:item_id>/JSON')
def itemJSON(category_id, item_id):
	item = session.query(Item).filter_by(id=item_id).one()
	return jsonify(Item=[item.serialize])

### JSON endpoints END


### HTML endpoints START ###

## Query all entries in Category table, display in template ##
@app.route('/')
@app.route('/category/')
def showCategories():
	if 'username' not in login_session:
		categories = session.query(Category).all()
		return render_template('publicCategories.html', categories=categories)
	categories = session.query(Category).all()
	return render_template('categories.html', categories=categories)


## Create new category ##
# Adds new entry to Category table #
@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
	if 'username' not in login_session:
		return redirect('/login')
	if request.method == 'POST':
		newCategory = Category(name=request.form['name'], user_id=login_session['user_id'])
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
	if 'username' not in login_session:
		return redirect('/login')
	editedCategory = session.query(Category).filter_by(id=category_id).one()
	if editedCategory.user_id != login_session['user_id']:
		return "<script>function myFunction() {alert('You are not authorized to edit this category.');}</script><body onload='myFunction()'>"
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
	if 'username' not in login_session:
		return redirect('/login')
	categoryToDelete = session.query(Category).filter_by(id=category_id).one()
	itemsToDelete = session.query(Item).filter_by(category_id=category_id).all()
	if categoryToDelete.user_id != login_session['user_id']:
		return "<script>function myFunction() {alert('You are not authorized to delete this category.');}</script><body onload='myFunction()'>"
	if request.method == 'POST':
		if request.form['confirm']:
			for i in itemsToDelete:
				session.delete(i)
				session.commit()
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
	creator = getUserInfo(category.user_id)
	if 'username' not in login_session or creator.id != login_session['user_id']:
		return render_template('publicItems.html', items=items, category=category)
	return render_template('items.html', items=items, category=category)


## Add a new item to catalog ##
# Category_id will keep the items arranged under the top level categories #
@app.route('/category/<int:category_id>/items/new/', methods=['GET', 'POST'])
def newItem(category_id):
	if 'username' not in login_session:
		return redirect('/login')
	category = session.query(Category).filter_by(id=category_id).one()
	if login_session['user_id'] != category.user_id:
		return "<script>function myFunction() {alert('You are not authorized to add items to this category.');}</script><body onload='myFunction()'>"
	if request.method == 'POST':
		newItem = Item(name=request.form['name'], description=request.form['description'], category_id=category_id, user_id=category.user_id)
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
	if 'username' not in login_session:
		return redirect('/login')
	editedItem = session.query(Item).filter_by(id=item_id).one()
	category = session.query(Category).filter_by(id=category_id).one()
	if login_session['user_id'] != category.user_id:
		return "<script>function myFunction() {alert('You are not authorized to edit items in this category.');}</script><body onload='myFunction()'>"
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
		return render_template('editItem.html', category_id=category.id, item=editedItem)


## Delete existing item in catalog ##
# Sends item object to be deleted, category_id is for redirecting to correct category afterwards #
@app.route('/category/<int:category_id>/items/<int:item_id>/delete/', methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
	if 'username' not in login_session:
		return redirect('/login')
	itemToDelete = session.query(Item).filter_by(id=item_id).one()
	category = session.query(Category).filter_by(id=category_id).one()
	if login_session['user_id'] != category.user_id:
		return "<script>function myFunction() {alert('You are not authorized to delete items from this category.');}</script><body onload='myFunction()'>"
	if request.method == 'POST':
		if request.form['confirm']:
			session.delete(itemToDelete)
			session.commit()
			flash("item delete success!")
			return redirect(url_for('showItems', category_id=category_id))
	else:
		return render_template('deleteItem.html', category_id=category_id, item=itemToDelete)

### HTML endpoints END ###


if __name__ == '__main__':
	app.debug = True
	app.secret_key = 'super secret key'
	app.run(host='0.0.0.0', port=8000)