from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure the upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# MongoDB setup
client = MongoClient('mongodb+srv://suhas:suhastimetracker@suhas-bigmangotree.jse0ber.mongodb.net/')
db = client['ECommerce']
company_credentials = db['company_credentials']
products_collection = db['products']
client_credentials = db['client']

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        company = company_credentials.find_one({'email': email, 'password': password})
        if company:
            session['user'] = email
            return redirect(url_for('manage_products'))
        else:
            return "Invalid email or password"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_name = request.form['company_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        description = request.form['description']
        phone = request.form['phone']
        profile_pic = request.files['profile_pic']
        address = request.form['address']
        
        if password != confirm_password:
            return "Passwords do not match"

        existing_company = company_credentials.find_one({'email': email})
        if existing_company:
            return "Company already registered"
        
        filename = secure_filename(profile_pic.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        profile_pic.save(filepath)

        company_credentials.insert_one({
            'company_name': company_name,
            'email': email,
            'password': password,
            'description': description,
            'phone': phone,
            'profile_pic': filename,
            'address': address
        })
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/products', methods=['GET', 'POST'])
def manage_products():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '')
    user_email = session['user']
    if search_query:
        products = products_collection.find({
            'company_email': user_email,
            '$or': [
                {'name': {'$regex': search_query, '$options': 'i'}},
                {'description': {'$regex': search_query, '$options': 'i'}}
            ]
        })
    else:
        products = products_collection.find({'company_email': user_email})
    
    return render_template('manage_products.html', products=products)

@app.route('/product/new', methods=['GET', 'POST'])
def create_product():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        quantity = request.form['quantity']
        image = request.files['image']
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        user_email = session['user']
        products_collection.insert_one({
            'name': name,
            'description': description,
            'price': price,
            'quantity': quantity,
            'image': filename,
            'company_email': user_email
        })
        return redirect(url_for('manage_products'))
    return render_template('product_form.html', action='Create')

@app.route('/product/edit/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user']
    product = products_collection.find_one({'_id': ObjectId(product_id), 'company_email': user_email})
    
    if not product:
        return "Product not found or you do not have permission to edit it"

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        quantity = request.form['quantity']
        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            products_collection.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': {'name': name, 'description': description, 'price': price, 'quantity': quantity, 'image': filename}}
            )
        else:
            products_collection.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': {'name': name, 'description': description, 'price': price, 'quantity': quantity}}
            )
        return redirect(url_for('manage_products'))
    
    return render_template('product_form.html', product=product, action='Edit')

@app.route('/product/delete/<product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user']
    products_collection.delete_one({'_id': ObjectId(product_id), 'company_email': user_email})
    return redirect(url_for('manage_products'))

@app.route('/client_login', methods=['GET', 'POST'])
def client_login():
    next_page = request.args.get('next', url_for('userhome'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        client = client_credentials.find_one({'email': email, 'password': password})
        if client:
            session['user'] = email
            return redirect(next_page)  # Redirect to the original page or userhome
        else:
            return "Invalid email or password"
    return render_template('client_login.html', next=next_page)

@app.route('/client_logout', methods=['GET'])
def client_logout():
    next_page = request.args.get('next', url_for('userhome'))
    session.pop('user', None)
    return redirect(next_page)  # Redirect to the same page or userhome



@app.route('/client_signup', methods=['GET', 'POST'])
def client_signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        gender = request.form['gender']
        phone = request.form['phone']
        
        if password != confirm_password:
            return "Passwords do not match"
        
        existing_client = client_credentials.find_one({'email': email})
        if existing_client:
            return "Client already registered"
        
        client_credentials.insert_one({
            'username': username,
            'email': email,
            'password': password,
            'gender': gender,
            'phone': phone
        })
        return redirect(url_for('client_login'))
    return render_template('client_signup.html')

@app.route('/userhome', methods=['GET'])
def userhome():
    search_query = request.args.get('search', '')
    if search_query:
        products = products_collection.find({
            '$or': [
                {'name': {'$regex': search_query, '$options': 'i'}},
                {'description': {'$regex': search_query, '$options': 'i'}}
            ]
        })
    else:
        products = products_collection.find()
    
    return render_template('userhome.html', products=products)

@app.route('/product/<product_id>', methods=['GET'])
def product(product_id):
    product = products_collection.find_one({'_id': ObjectId(product_id)})
    company_email = product['company_email']
    company = company_credentials.find_one({'email': company_email})
    company_name = company['company_name'].replace(' ', '-').replace('_', '-')  # Format for URL
    return render_template('product.html', product=product, company=company, company_name=company_name)




@app.route('/select_company', methods=['GET'])
def select_company():
    search_query = request.args.get('search', '')
    if search_query:
        companies = company_credentials.find({
            '$or': [
                {'company_name': {'$regex': search_query, '$options': 'i'}}
            ]
        })
    else:
        companies = company_credentials.find()
    return render_template('select_company.html', companies=companies)

@app.route('/company/<company_name>/products', methods=['GET'])
def company_products(company_name):
    # Convert company_name from hyphen-separated back to the actual company name
    formatted_company_name = company_name.replace('-', ' ').replace('_', ' ')
    # Fetch the company email using the formatted company name
    company = company_credentials.find_one({'company_name': formatted_company_name})
    if company:
        company_email = company['email']
    else:
        # Handle case where company is not found
        return redirect(url_for('select_company'))
    
    search_query = request.args.get('search', '')
    query = {'company_email': company_email}
    if search_query:
        query['$or'] = [
            {'name': {'$regex': search_query, '$options': 'i'}},
            {'description': {'$regex': search_query, '$options': 'i'}}
        ]
    products = products_collection.find(query)
    return render_template('company_products.html', products=products, company_name=formatted_company_name)





if __name__ == '__main__':
    app.run(debug=True)
