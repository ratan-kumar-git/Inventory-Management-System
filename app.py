from collections import defaultdict
from flask import Flask, render_template, request, redirect, flash, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from io import BytesIO
import bcrypt
import datetime
import pytz

app = Flask(__name__)

# Make Connection with Data Base
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.secret_key = 'Bablu@12345'

db = SQLAlchemy(app)


def india_time():
    return datetime.datetime.now(pytz.timezone("Asia/Kolkata"))

# User Table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


    def __init__(self, email, password, name):
        self.name = name
        self.email = email
        self.password = self.hash_password(password)

    def hash_password(self, password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

# Customer Table
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_village = db.Column(db.String(100), nullable=False)
    customer_mob_no = db.Column(db.String(100), nullable=False)

    def __init__(self, user_id, customer_name, customer_village, customer_mob_no):
        self.user_id = user_id
        self.customer_name = customer_name
        self.customer_village = customer_village
        self.customer_mob_no = customer_mob_no

# Product Table
class Products(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prod_name = db.Column(db.String(100), nullable=False)
    prod_quantity = db.Column(db.Integer, nullable=False)
    prod_sell_price = db.Column(db.Integer, nullable=False)
    prod_mrp = db.Column(db.Integer, nullable=False)
    prod_buy_price = db.Column(db.Integer, nullable=False)
    prod_min_quantity = db.Column(db.Integer, nullable=False)

    def __init__(self, user_id, prod_name, prod_quantity, prod_sell_price, prod_mrp, prod_buy_price, prod_min_quantity):
        self.user_id = user_id
        self.prod_name = prod_name
        self.prod_quantity = prod_quantity
        self.prod_sell_price = prod_sell_price
        self.prod_mrp = prod_mrp
        self.prod_buy_price = prod_buy_price
        self.prod_min_quantity = prod_min_quantity

# Billing Table
class Billing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    billing_date = db.Column(db.DateTime, default=india_time)
    total_amount = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, default=0)  # Amount the customer paid
    dues = db.Column(db.Float, default=0)  # Remaining amount to be paid

    # Relationship
    customer = db.relationship('Customer', backref=db.backref('bills', lazy=True, cascade="all"))

    def __init__(self, customer_id, billing_date, total_amount, amount_paid, dues):
        self.customer_id = customer_id
        self.total_amount = total_amount
        self.amount_paid = amount_paid
        self.dues = dues

# BillingDetail Table
class BillingDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    billing_id = db.Column(db.Integer, db.ForeignKey('billing.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    # Relationships
    billing = db.relationship('Billing', backref=db.backref('details', lazy=True, cascade="all"))
    product = db.relationship('Products', backref=db.backref('billing_details', lazy=True, cascade="all"))

    def __init__(self, billing_id, product_id, quantity, total_price):
        self.billing_id = billing_id
        self.product_id = product_id
        self.quantity = quantity
        self.total_price = total_price

# Contact Us Table
class Contact_us(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(100), nullable=False)

    def __init__(self, email, subject, message):
        self.email = email
        self.subject = subject
        self.message = message


with app.app_context():
    db.create_all()


# Home Page
@app.route('/')
def index():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()
        return render_template('home.html', title='Home', current_page = 'home', user=user, messages=messages)
    else:
        return render_template('home.html', title='Home', current_page = 'home')


# Register Page
@app.route('/signup', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if there's already a user registered
        # existing_users = User.query.count()
        # if existing_users >= 2:
        #     flash('Registration is closed. Only two user is allowed to the website', 'error')
        #     return redirect('/login')

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please use different email.', 'error')
            return redirect('/signup')  # Redirect back to registration page with flash message

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect('/signup')

    return render_template('signup.html', title='Signup Page')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user:
            if user.check_password(password):
                session['email'] = user.email
                return redirect('/dashboard')
            else:
                error = 'Incorrect password. Please try again.'
        else:
            error = 'Email not found. Please register first.'
        flash(error, 'error')
    return render_template('login.html', title='Login Page')

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'email' not in session:
        flash('You need to login first.', 'error')
        return redirect('/login')

    user = User.query.filter_by(email=session['email']).first()

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return redirect('/change_password')

        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect('/change_password')

        # Update password
        user.password = user.hash_password(new_password)
        db.session.commit()
        flash('Password updated successfully.', 'success')
        return redirect('/change_password')

    return render_template('change_password.html', title='Change Password', user=user)


#Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()
        customers = Customer.query.filter(Customer.user_id == user.id).order_by(Customer.id.desc()).all()

        # Get products with low stock
        low_prod_stock = Products.query.filter(Products.user_id == user.id, Products.prod_quantity<=Products.prod_min_quantity).order_by(Products.prod_quantity).all()
        
        #get all products
        products = Products.query.filter(Products.user_id == user.id).order_by(Products.id).all() 

        # Get total customers, products, billings, and sales
        total_customer = Customer.query.filter(Customer.user_id == user.id).count()
        total_product = Products.query.filter(Products.user_id == user.id).count()

        total_billings = (
        db.session.query(Billing)
        .join(Customer, Customer.id == Billing.customer_id)
        .filter(Customer.user_id == user.id)
        .count()
        )
        
        total_sales = (
        db.session.query(func.sum(Billing.total_amount))
        .join(Customer, Customer.id == Billing.customer_id)  # Correct join condition
        .filter(Customer.user_id == user.id)  # Filters for the specific user
        .scalar()
        ) or 0

        return render_template('dashboard.html', title='Dashboard', current_page = 'dashboard', 
            user=user, messages=messages, customers=customers, low_prod_stock=low_prod_stock,
            total_customer=total_customer, total_product=total_product, total_sales=total_sales, 
            total_billings=total_billings, products=products)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

# Get Sales Data for Chart   
@app.route('/get_sales_data')
def get_sales_data():
    if 'email' in session:
        # Fetch sales data
        sales_data = Billing.query.with_entities(Billing.billing_date, Billing.total_amount).all()

        # Aggregate sales per day
        sales_summary = defaultdict(float)
        for sale in sales_data:
            date_str = sale.billing_date.strftime('%d-%m')  # Format date
            sales_summary[date_str] += sale.total_amount

        # Convert to JSON format
        sales_json = {
            "dates": list(sales_summary.keys()),
            "amounts": list(sales_summary.values())
        }

        return jsonify(sales_json)  # Return JSON response
    else:
        return jsonify({"error": "Unauthorized"}), 403

# Get Data During Billing
@app.route('/get_product_details/<int:id>', methods=['GET'])
def get_product_details(id):
    product = db.session.get(Products, id)
    print(product)

    if product:
        return jsonify({
            'prod_qty': product.prod_quantity,
            'min_qty': product.prod_min_quantity,
            'sell_price': product.prod_sell_price,
            'mrp': product.prod_mrp,
            'buy_price': product.prod_buy_price
            })
    
    return jsonify({'error': 'Customer not found'}), 404


#Customer
@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()
    
        # Get page number from request arguments, default to 1
        page = request.args.get('page', 1, type=int)
        
        # Paginate products (10 per page)
        customers = Customer.query.filter(Customer.user_id == user.id).order_by(Customer.id.desc()).paginate(page=page, per_page=10)
        total_customer = Customer.query.filter(Customer.user_id == user.id).count()

        # Get total dues separately
        customer_dues = {
            c.id: db.session.query(func.coalesce(func.sum(Billing.dues), 0))
            .filter(Billing.customer_id == c.id)
            .scalar()
            for c in customers.items
        }


        return render_template('customer.html', title='Customer', current_page='customer', user=user, customers=customers, total_customer=total_customer, min=min, enumerate=enumerate, messages=messages, customer_dues=customer_dues)

    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#add_customer
@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()
        if request.method == 'POST':
            customer_name = request.form['customer_name']
            customer_village = request.form['customer_vill_name']
            customer_mob_no = request.form['mobile_number']
        
            new_data = Customer(user_id=user.id, customer_name=customer_name, customer_village=customer_village, customer_mob_no=customer_mob_no)
            db.session.add(new_data)
            db.session.commit()
            flash('Customer Added Successful.', 'success')

        return render_template('add_customer.html', title='Add Customer', current_page = 'add_customer', user=user, messages=messages)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#Download Customer Excel
@app.route('/download_customer', methods=['GET'])
def download_customer():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        customers = Customer.query.filter(Customer.user_id == user.id).all()

        # Create a DataFrame from the query results
        data = [{
            "Name" : data.customer_name,
            "village": data.customer_village,
            "Mob-No.": data.customer_mob_no,
            "Dues": 0,
        } for data in customers]

        df = pd.DataFrame(data)

        # Convert DataFrame to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=True, sheet_name='Customer List')
        output.seek(0)
        return send_file(output, download_name=f'Customers_list.xlsx', as_attachment=True)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

# Customer Bill Details    
@app.route('/customer_detail/<int:id>', methods=['GET'])
def customer_detail(id):
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()
        customer = Customer.query.filter_by(id=id, user_id=user.id).first()
        billings = Billing.query.filter_by(customer_id=customer.id).order_by(Billing.id.desc()).all()
        total_dues = sum(billing.dues for billing in billings)

        return render_template('customer_detail.html', title='Customer Detail', current_page='customer', user=user, customer=customer, billings=billings, total_dues=total_dues, messages=messages)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

# Customer Billing History Details     
@app.route('/customer_billing_detail/<int:custo_id>/<int:bill_id>', methods=['GET'])
def customer_billing_detail(custo_id, bill_id):
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        customer = Customer.query.filter_by(id=custo_id, user_id=user.id).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()

        # Join BillingDetails with Billing and Products to fetch required details in one query
        customer_billing_details = (
            db.session.query(BillingDetails, Billing, Products)
            .join(Billing, BillingDetails.billing_id == Billing.id)
            .join(Products, BillingDetails.product_id == Products.id)
            .filter(Billing.id == bill_id)
            .all()
        )
        return render_template(
            'customer_bill_detail.html',
            title='Customer Detail',
            current_page='customer',
            user=user,
            customer=customer,
            customer_billing_details=customer_billing_details,
            messages=messages
        )
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

# Delete Customer 
@app.route('/delete_customer/<int:id>', methods=['GET'])
def delete_customer(id):
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        if not user:
            flash('User not found.', 'error')
            return redirect('/login')

        customer = Customer.query.filter_by(id=id, user_id=user.id).first()
        if not customer :
            flash('Customer not found.', 'error')
            return redirect('/customers')

        try:
            db.session.delete(customer)
            db.session.commit()
            flash('Customer deleted successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while deleting the customer. Please try again.', 'error')
            print(f"SQLAlchemyError: {e}")

        return redirect('/customers')
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#Products
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()

        # Get page number from request arguments, default to 1
        page = request.args.get('page', 1, type=int)
        
        # Paginate products (10 per page)
        products = Products.query.filter(Products.user_id == user.id).order_by(Products.id.desc()).paginate(page=page, per_page=10)
        total_product = Products.query.filter(Products.user_id == user.id).count()

        return render_template('product.html', title='Products', current_page='products', 
                               user=user, products=products, total_product=total_product, min=min, enumerate=enumerate, messages=messages)

    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#Add Products
@app.route('/add_product', methods=['GET', 'POST'])
def add_products():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()

        if request.method == 'POST':
            prod_name = request.form['product_name']
            prod_quantity = request.form['product_quantity']
            prod_sell_price = request.form['selling_price']
            prod_mrp = request.form['mrp']
            prod_buy_price = request.form['purches_price']
            prod_min_quantity = request.form['min_quantity']
        
            new_data = Products(user_id=user.id, prod_name=prod_name, prod_quantity=prod_quantity, prod_sell_price= prod_sell_price, prod_mrp=prod_mrp, prod_buy_price=prod_buy_price,  prod_min_quantity= prod_min_quantity)
            db.session.add(new_data)
            db.session.commit()
            flash('Product Added Successful.', 'success')
        return render_template('add_product.html', title='Add Products', current_page = 'add_product', user=user, messages=messages)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#Add Stock
@app.route('/add_stock', methods=['GET', 'POST'])
def add_stock():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()

        if request.method == 'POST':
            product_id = request.form['product_id']

            product = Products.query.filter_by(id=product_id, user_id=user.id).first()
            if not product:
                flash('Product not found.', 'error')
                return redirect('/add_stock')
            
            stock_quantity = int(request.form['quantity'])
            product.prod_quantity += stock_quantity
            product.prod_buy_price  = request.form['buy_price']
            product.prod_mrp = request.form['mrp']
            product.prod_sell_price = request.form['sell_price']

            db.session.commit()
            flash('Stock Added Successful.', 'success')
        return redirect('/dashboard')
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#Download Product Excel
@app.route('/download_excel', methods=['GET'])
def download_excel():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        products = Products.query.filter(Products.user_id == user.id).all()

        # Create a DataFrame from the query results
        data = [{
            "Product Name" : data.prod_name,
            "Product Qty": data.prod_quantity,
            "Prod_Sell_Price": data.prod_sell_price,
            "Prod_MRP": data.prod_mrp,
            "Prod_Buy_Price": data.prod_buy_price,
            "Prod_Min_Qty": data.prod_min_quantity
        } for data in products]

        df = pd.DataFrame(data)

        # Convert DataFrame to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=True, sheet_name='Products List')
        output.seek(0)
        return send_file(output, download_name=f'Products_list.xlsx', as_attachment=True)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

# Edit product 
@app.route('/edit_product/<int:id>', methods=['GET'])
def edit_product(id):
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        product = Products.query.filter_by(id=id, user_id=user.id).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()

        if not product :
            flash('Data not found or you do not have permission to edit this data.', 'error')
            return redirect('/products')
        
        return render_template('edit_product.html', title='Edit Product', user=user, product=product, messages=messages)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

# Update Product
@app.route('/update_data/<int:id>', methods=['POST'])
def update_data(id):
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        product = Products.query.filter_by(id=id, user_id=user.id).first()

        if not product :
            flash('Data not found or you do not have permission to edit this data.', 'error')
            return redirect('/products')
        
        product.prod_name = request.form['product_name']
        product.prod_quantity = request.form['product_quantity']
        product.prod_sell_price = request.form['selling_price']
        product.prod_mrp = request.form['mrp']
        product.prod_buy_price = request.form['purches_price']
        product.prod_min_quantity = request.form['min_quantity']

        db.session.commit()
        flash('Data updated successfully.', 'success')
        return redirect('/products')
           
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

# Delete product
@app.route('/delete_product/<int:id>', methods=['GET'])
def delete_product(id):
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        if not user:
            flash('User not found.', 'error')
            return redirect('/login')

        product = Products.query.filter_by(id=id, user_id=user.id).first()
        if not product :
            flash('Customer not found.', 'error')
            return redirect('/products')

        try:
            db.session.delete(product)
            db.session.commit()
            flash('Customer deleted successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while deleting the customer. Please try again.', 'error')
            print(f"SQLAlchemyError: {e}")

        return redirect('/products')
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#Billing
@app.route('/billing', methods=['GET', 'POST'])
def billing():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        customers = Customer.query.filter_by(user_id=user.id).all()
        products = Products.query.filter_by(user_id=user.id).all()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()
        return render_template('billing.html', title='Billing', current_page = 'billing', user=user, customers=customers, products=products, messages=messages)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')
    
#Billing_process
@app.route('/prod_billing', methods=['GET', 'POST'])
def prod_billing():
    if 'email' not in session:
        flash('You need to login first.', 'error')
        return redirect('/login')

    user = User.query.filter_by(email=session['email']).first()
    data = request.get_json()
    print(data)

    if not data:
        return jsonify({"status": "error", "message": "No JSON received"}), 400

    # Extract and validate data
    try:
        customer_id = data.get('customer_id')
        product_list = data.get('products', [])
        amount_paid = data.get('amount_paid')

        # Checking null iteam 
        if not customer_id:
            return jsonify({"status": "error", "message": "Please Select Customer!"}), 400

        if not product_list:
            return jsonify({"status": "error", "message": "Please select at least one product!"}), 400
        
        if not amount_paid:
            return jsonify({"status": "error", "message": "Please Enter Amount"}), 400
        
        customer_id = int(data.get('customer_id'))
        amount_paid = float(data.get('amount_paid'))
        
        if amount_paid < 0:
            return jsonify({"status": "error", "message": "Amount paid cannot be negative!"}), 400
        
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid data format!"}), 400

    # Billing Process
    total_amount = 0
    india_time = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
    billing = Billing(
        customer_id=customer_id,
        billing_date=india_time,
        total_amount=0,
        amount_paid=amount_paid,
        dues=0
    )
    db.session.add(billing)
    db.session.flush()

    for product_data in product_list:
        product_id = product_data['prodId']
        quantity = product_data['quantity']

        product = Products.query.filter_by(user_id=user.id, id=product_id).first()

        if product and product.prod_quantity >= quantity:
            total_price = product.prod_sell_price * quantity
            total_amount += total_price

            product.prod_quantity -= quantity

            bill_detail = BillingDetails(
                billing_id=billing.id,
                product_id=product.id,
                quantity=quantity,
                total_price=total_price
            )
            db.session.add(bill_detail)
        else:
            db.session.rollback()
            return jsonify({"status": "error", "message": f"Insufficient stock for {product.prod_name}!"}), 400

    # Update total amount & dues
    billing.total_amount = total_amount
    billing.dues = total_amount - amount_paid

    db.session.commit()
    return jsonify({"status": "success", "message": "Billing successful!"}), 200

# Get Data During Billing
@app.route('/get_customer_details/<int:customer_id>', methods=['GET'])
def get_customer_details(customer_id):
    customer = db.session.get(Customer, customer_id)
    billings =  Billing.query.filter_by(customer_id = customer_id).all()

    if billings:
        total_dues = sum(billing.dues for billing in billings)  # Summing dues
        dues = f"₹{total_dues}"
    else:
        dues = "₹0"

    if customer:
        # Set timezone to India (IST)
        ist = pytz.timezone('Asia/Kolkata')
        india_date = datetime.datetime.now(ist).strftime("%d-%b-%Y")  # Format: 12-Jan-2024
        india_time = datetime.datetime.now(ist).strftime("%I : %M %p")

        return jsonify({
            'customer_village': customer.customer_village,
            'customer_phone': customer.customer_mob_no,
            'today_date': india_date,
            'today_time': india_time,
            'customer_dues': dues
        })
    return jsonify({'error': 'Customer not found'}), 404

#Invoice
@app.route('/billing_history', methods=['GET', 'POST'])
def billing_history():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()
        customer_billing = (
            db.session.query(Customer, Billing)
            .join(Billing, Billing.customer_id == Customer.id)
            .filter(Customer.user_id == user.id)
            .order_by(Billing.id.desc())
            .all()
        )

        return render_template('billing_history.html', title='Billing History', current_page = 'billing_history', user=user, customer_billing=customer_billing, messages=messages)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')


#Contact_us
@app.route('/about_us')
def about_us():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()
        return render_template('about_us.html', title='About Us', current_page = 'about_us', user=user, messages=messages)
    else:
        return render_template('about_us.html', title='About Us', current_page = 'about_us')
    

#Contact_us
@app.route('/contact_us', methods=['GET','POST'])
def contact_us():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        messages = Contact_us.query.order_by(Contact_us.id.desc()).all()
        if request.method == 'POST':
            email = request.form['email']
            subject = request.form['subject']
            message = request.form['message']

            new_data = Contact_us(email=email, subject=subject, message=message)
            db.session.add(new_data)
            db.session.commit()    

            flash('Message Send Successful.', 'success')
        return render_template('contact_us.html', title='Contact Us', current_page = 'contact_us', user=user, messages=messages)
    else:
        if request.method == 'POST':
            email = request.form['email']
            subject = request.form['subject']
            message = request.form['message']

            new_data = Contact_us(email=email, subject=subject, message=message)
            db.session.add(new_data)
            db.session.commit()    

            flash('Message Send Successful.', 'success')
        return render_template('contact_us.html', title='Contact Us', current_page = 'contact_us')


#Deleting Contact Us Message
@app.route('/delete_message/<int:id>', methods=['GET'])
def delete_message(id):
    if 'email' in session:
        message = Contact_us.query.filter_by(id=id).first()
        if not message :
            flash('Message not found.', 'error')
            return redirect('/contact_us')

        try:
            db.session.delete(message)
            db.session.commit()
            flash('Message deleted successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while deleting the message. Please try again.', 'error')
            print(f"SQLAlchemyError: {e}")

        return redirect('/contact_us')
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#Logout Page
@app.route('/logout')
def logout():
    session.pop('email', None)
    flash('You have been logged out.', 'info')
    return redirect('/login')



if __name__ == '__main__':
    app.run(debug=True)
