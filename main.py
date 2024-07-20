from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
import hashlib
import time
import string
import random

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
admin_credentials = db['admin']

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        company = company_credentials.find_one({'email': email, 'password': hashed_password})
        if company:
            session['user'] = email
            # Check if required fields are filled
            if all(key in company and company[key] for key in ['description', 'phone', 'profile_pic', 'address']):
                return redirect(url_for('manage_products'))
            else:
                return redirect(url_for('complete_profile'))
        else:
            return "Invalid email or password"
    return render_template('login.html')

@app.route('/complete_profile', methods=['GET', 'POST'])
def complete_profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user']
    company = company_credentials.find_one({'email': user_email})
    
    if request.method == 'POST':
        description = request.form['description']
        phone = request.form['phone']
        profile_pic = request.files['profile_pic']
        address = request.form['address']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match"

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        filename = secure_filename(profile_pic.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        profile_pic.save(filepath)
        
        company_credentials.update_one(
            {'email': user_email},
            {
                '$set': {
                    'description': description,
                    'phone': phone,
                    'profile_pic': filename,
                    'address': address,
                    'password': hashed_password
                }
            }
        )
        return redirect(url_for('manage_products'))

    return render_template('signup.html', company_name=company['company_name'])

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('complete_profile'))

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
        
        more_images = request.files.getlist('more_images')
        more_images_filenames = []
        for img in more_images:
            if img.filename:
                more_filename = secure_filename(img.filename)
                more_filepath = os.path.join(app.config['UPLOAD_FOLDER'], more_filename)
                img.save(more_filepath)
                more_images_filenames.append(more_filename)

        user_email = session['user']
        products_collection.insert_one({
            'name': name,
            'description': description,
            'price': price,
            'quantity': quantity,
            'image': filename,
            'more_images': more_images_filenames,
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
        
        update_data = {
            'name': name,
            'description': description,
            'price': price,
            'quantity': quantity,
        }
        
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            update_data['image'] = filename
        
        more_images = request.files.getlist('more_images')
        more_images_filenames = product.get('more_images', [])
        for img in more_images:
            if img.filename:
                more_filename = secure_filename(img.filename)
                more_filepath = os.path.join(app.config['UPLOAD_FOLDER'], more_filename)
                img.save(more_filepath)
                more_images_filenames.append(more_filename)
        
        update_data['more_images'] = more_images_filenames
        
        products_collection.update_one(
            {'_id': ObjectId(product_id)},
            {'$set': update_data}
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
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        client = client_credentials.find_one({'email': email, 'password': hashed_password})
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
        
        # Hash the password using SHA-256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        client_credentials.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
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


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        admin = admin_credentials.find_one({'name': name, 'password': password})
        if admin:
            session['admin'] = name
            return redirect(url_for('admin_companies'))
        else:
            return "Invalid name or password"
    return render_template('admin_login.html')



@app.route('/admin_companies', methods=['GET'])
def admin_companies():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    search_query = request.args.get('search', '')
    if search_query:
        companies = company_credentials.find({
            '$or': [
                {'company_name': {'$regex': search_query, '$options': 'i'}}
            ]
        })
    else:
        companies = company_credentials.find()
    
    # Replace missing fields with "-"
    company_list = []
    for company in companies:
        company_data = {
            'company_name': company.get('company_name', '-'),
            'description': company.get('description', '-'),
            'address': company.get('address', '-'),
            'phone': company.get('phone', '-'),
            'email': company.get('email', '-'),  # Added email field
            'profile_pic': company.get('profile_pic', '-')
        }
        company_list.append(company_data)
    
    return render_template('admin_companies.html', companies=company_list)



@app.route('/add_company', methods=['GET', 'POST'])
def add_company():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    password = None
    error_message = None
    
    if request.method == 'POST':
        company_name = request.form['company_name']
        email = request.form['email']
        
        # Check if email already exists in the database
        if company_credentials.find_one({'email': email}):
            error_message = 'Email already exists. Please use a different email.'
            return render_template('add_company.html', error_message=error_message)
        
        # Generate a unique alphanumeric password
        password = generate_unique_password()
        
        # Hash the password using SHA-256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Insert the company data into the database
        company_credentials.insert_one({
            'company_name': company_name,
            'email': email,
            'password': hashed_password,
            'description': '',  # Empty field
            'address': '',      # Empty field
            'phone': '',        # Empty field
            'profile_pic': '',  # Empty field
        })
        
        return render_template('add_company.html', password=password)
    
    return render_template('add_company.html')


def generate_unique_password():
    """Generate a unique alphanumeric password using timestamp and random characters."""
    timestamp = int(time.time())
    random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    password = f"{timestamp}{random_chars}"
    return password



if __name__ == '__main__':
    app.run(debug=True)
