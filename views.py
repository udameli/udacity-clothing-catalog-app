import os
from werkzeug.utils import secure_filename
from werkzeug import url_decode
from models import Base, User, Type, Item
from flask import Flask, jsonify, request, url_for, abort, g, flash 
from flask import render_template, redirect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from flask.ext.httpauth import HTTPBasicAuth
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
from flask import session as login_session
import requests
import random, string

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

auth = HTTPBasicAuth() 

UPLOAD_FOLDER = 'static/images/'
ALLOWED_EXTENSIONS = set(['png', 'jpg','jpeg'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

engine = create_engine('sqlite:///clothingcatalog.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# JSON APIs to view items and types information
@app.route('/items/JSON')
def showAllJSON():
	items = session.query(Item).all()
	return jsonify(items = [i.serialize for i in items])

@app.route('/types/<string:type>/items/JSON')
def showTypeJSON(type):
	type_id = getTypeId(type)
	items = session.query(Item).filter_by(type_id = type_id).all()
	return jsonify(items = [i.serialize for i in items])

@app.route('/items/<int:item_id>/JSON')
def showItemJSON(item_id):
	item = session.query(Item).filter_by(id = item_id).one()
	return jsonify(item = item.serialize)

# main page. displays a selection of items
@app.route('/')
@app.route('/items')
def showAll():
	items = session.query(Item).all()
	types = session.query(Type).all()
	if 'username' not in login_session:
		# return list of items with no 'create new item' option
		return render_template('publicAllItems.html', items = items, 
			types = types, status = 'loggedOut')
	else: 
		# return list of items with 'create new item' option
		return render_template('allItems.html', items = items,
			types = types, status = 'loggedIn')

# displays all items in a particular category
@app.route('/types/<string:type>/items')
def showType(type):
	types = session.query(Type).all()
	if 'username' not in login_session:
		status = 'loggedOut'
	else:
		status = 'loggedIn'
	try:
		type_id = getTypeId(type)
		items = session.query(Item).filter_by(type_id = type_id).all()
		if status == 'loggedOut':
			# return list of items of one type with no 'create new item' option
			return render_template('publicTypeItems.html', type = type, 
				items = items, types = types, status = status)
		else: 
			# return list of items of one type with 'create new item' option
			return render_template('typeItems.html', type = type, items = items,
				types = types, status = status)
	except:
		return render_template('typeError.html', type = type, types = types, status = status)

# displays a particular item
@app.route('/items/<int:item_id>')
def showItem(item_id):
	item = session.query(Item).filter_by(id = item_id).one()
	types = session.query(Type).all()

	if 'username' not in login_session:
		status = 'loggedOut'
		return render_template('publicItemPage.html', item = item, types = types, 
			status = status)
	else:
		status = 'loggedIn'
		
		if item.user_id == login_session['user_id']:
			return render_template('itemPage.html', item = item, types = types, 
				status = status)
		else:
			return render_template('publicItemPage.html', item = item, 
			types = types, status = status)			



# form to add a new item
@app.route('/items/new')
def newItem():
	if 'username' not in login_session:
		return redirect(url_for('showLogin'))
	else:
		types = session.query(Type).all()
		return render_template('newItemForm.html', types = types, 
			status = 'loggedIn')


@app.route('/items/new', methods=['POST'])
def addNewItem():
	if 'username' not in login_session:
		return redirect(url_for('showLogin'))
	else:
		types = session.query(Type).all()
		# check if all fields were filled out
		if not request.form['name'] or not request.form['description'] or not request.form['type']:
			return render_template('preFilledForm.html', name = request.form['name'], 
				description = request.form['description'], error = 'Please fill out all fields', 
				types = types, status = 'loggedIn')
	
		# check if the post request has the file part
		if 'file' not in request.files:
			print('no file part')
			return render_template('preFilledForm.html', name = request.form['name'],
				description = request.form['description'], types = types,
				status = 'loggedIn')
	
		file = request.files['file']
		# check if filename is not empty
		if file.filename == '':
			print('no selected file')
			return render_template('preFilledForm.html', name = request.form['name'],
				description = request.form['description'], types = types,
				status = 'loggedIn') 
		if file and allowed_file(file.filename):
			# check if filename is secure
			filename = secure_filename(file.filename)

			# check if filename already exists
			img_path = '/' + UPLOAD_FOLDER + filename
			item = session.query(Item).filter_by(img_path = img_path).first()
			if item:
				return render_template('preFilledForm.html', name = request.form['name'],
					description = request.form['description'], types = types, 
					error = 'The image with this name already exists.', status = 'loggedIn')

			else:
				file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
				type = request.form['type']
				type_id = getTypeId(type)
				newItem = Item(name = request.form['name'], description = request.form['description'], type_id = type_id, user_id = login_session['user_id'], img_path = img_path)
				session.add(newItem)
				session.commit()
				item = session.query(Item).filter_by(name = request.form['name']).filter_by(description = request.form['description']).one()
				return redirect(url_for('showItem', item_id = item.id))


# form to edit an item
@app.route('/items/<int:item_id>/edit')
def itemToEdit(item_id):
	try:
		editedItem = session.query(Item).filter_by(id = item_id).first()
		if editedItem.user_id == login_session['user_id']:
			types = session.query(Type).all()
			return render_template('editedItemForm.html', types = types, item = editedItem,
				status = 'loggedIn')
		else:
			return redirect(url_for('showItem', item_id = editedItem.id))
	except:
		return redirect(url_for('showAll'))

@app.route('/items/<int:item_id>/edit', methods=['POST'])
def editItem(item_id):
	try:
		editedItem = session.query(Item).filter_by(id = item_id).first()
		types = session.query(Type).all()
		if editedItem.user_id == login_session['user_id']:
			if not request.form['name'] or not request.form['description'] or not request.form['type']:
				return render_template('preFilledFormNoImage.html', name = request.form['name'], 
					description = request.form['description'], error = 'Please fill out all fields', 
					types = types, status = 'loggedIn')

			editedItem.name = request.form['name']
			editedItem.description = request.form['description']
			editedItem.type_id = getTypeId(request.form['type'])
			session.commit()
			return redirect(url_for('showItem', item_id = item_id))
		else:
			return redirect(url_for('showItem', item_id = item_id))
	except:
		return redirect(url_for('showAll'))


# delete an item confirmation page
@app.route('/items/<int:item_id>/delete')
def itemToDelete(item_id):
	try:
		itemToDelete = session.query(Item).filter_by(id = item_id).first()
		types = session.query(Type).all()
		if itemToDelete.user_id == login_session['user_id']:
			return render_template('deleteItemPage.html', item = itemToDelete, 
				types = types, status = 'loggedIn')
		else:
			return redirect(url_for('showItem', item_id = item_id))
	except:
		return redirect(url_for('showAll'))

@app.route('/items/<int:item_id>/delete', methods=['POST'])
def deleteItem(item_id):
	try:
		itemToDelete = session.query(Item).filter_by(id = item_id).first()
		if itemToDelete.user_id == login_session['user_id']:
			filename = itemToDelete.img_path.split('/')[3]
			os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			session.delete(itemToDelete)
			session.commit()
			return redirect(url_for('showAll'))
		else:
			return redirect(url_for('showItem', item_id = item_id))
	except:
		return redirect(url_for('showAll'))

# login page with google plus button
@app.route('/login')
def showLogin():
	state = ''.join(random.choice(string.ascii_uppercase + 
		string.digits) for x in range(32))
	login_session['state'] = state
	types = session.query(Type).all()
	return render_template('login.html', STATE = state, types = types, 
		status = 'loggedOut')

@app.route('/gconnect', methods=['POST'])
def gconnect():
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	code = request.data

	try:
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope = '')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)

	except FlowExchangeError:
		response = make_response(
			json.dumps('Failed to upgrade the authorization code.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
		% access_token)
	h = httplib2.Http()
	result = json.loads((h.request(url, 'GET')[1]))

	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type'] = 'application/json'
		return response

	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(
			json.dumps("Token's user ID doesn't match given user ID."), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Verify that the access token is valid for this app.
	if result['issued_to'] != CLIENT_ID:
		response = make_response(
			json.dumps("Token's client ID does not match app's."), 401)
		print("Token's client ID does not match app's.")
		response.headers['Content-Type'] = 'application/json'
		return response

	stored_credentials = login_session.get('credentials')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_credentials is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'),
			200)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Store the access token in the session for later use.
	login_session['credentials'] = credentials 
	login_session['gplus_id'] = gplus_id

	# Get user info
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': credentials.access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params = params)

	# To decode json
	data = answer.json()

	login_session['username'] = data['name']
	login_session['email'] = data['email']
	login_session['picture'] = data['picture']

	user_id = getUserID(login_session['email'])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	output = ''
	output += '<h1>Welcome, '
	output += login_session['username']
	output += '!</h1>'
	flash("you are now logged in as %s" % login_session['username'])
	print("done!")
	return output

@app.route('/gdisconnect')
def gdisconnect():
	credentials = login_session.get('credentials')

	if credentials is None:
		response = make_response(json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	access_token = credentials.access_token
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]

	if result['status'] == '200':
		del login_session['credentials']
		del login_session['gplus_id']
		del login_session['username']
		del login_session['email']
		del login_session['picture']	

		response = make_response(json.dumps('Successfully disconnected.'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response

	else:
		response = make_response(
			json.dumps('Failed to revoke token for given user.'), 400)
		response.headers['Content-Type'] == 'application/json'
		return response

def createUser(login_session):
	newUser = User(username = login_session['username'], 
		email = login_session['email'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email = login_session['email']).one()
	return user.id 

def getUserID(email):
	try:
		user = session.query(User).filter_by(email = email).one()
		return user.id
	except:
		return None

# takes a clothing type as a parameter and returns its id 
def getTypeId(type):
	clothing_type = session.query(Type).filter_by(type = type).first()
	return clothing_type.id

# check if file has allowed extension
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
	app.debug = True
	app.secret_key = 'super_secret_key'
	app.run(host='0.0.0.0', port=5000)