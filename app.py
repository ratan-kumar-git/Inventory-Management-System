from flask import Flask, render_template, request, redirect, flash, session, send_file, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
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

# Create Database with the name of "User"
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

# Create Database for Customer
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

class Products(db.Model):
    prod_id = db.Column(db.Integer, primary_key=True)
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

class BillingDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    billing_id = db.Column(db.Integer, db.ForeignKey('billing.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.prod_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    # Relationships
    billing = db.relationship('Billing', backref=db.backref('details', lazy=True, cascade="all"))
    product = db.relationship('Products', backref=db.backref('billing_details', lazy=True, cascade="all"))

with app.app_context():
    db.create_all()


# Home Page
@app.route('/')
def index():
    return render_template('home.html', title='Home')


# @app.route('/search', methods=['GET'])
# def search():
#     if 'email' in session:
#         user = User.query.filter_by(email=session['email']).first()
#         query = request.args.get('q', '')

#         if query:
#             results = Products.query.filter(
#                 Products.user_id == user.id,
#                 Products.prod_name.ilike(f"%{query}%")
#             ).limit(5).all()

#             suggestions = [product.prod_name for product in results]
#             return jsonify(suggestions)

#         return jsonify([])
#     else:
#         flash('You need to login first.', 'error')
#         return redirect('/login')


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
        if user and user.check_password(password):
            session['email'] = user.email
            return redirect('/dashboard')
        else:
            error = 'Invalid email or password. Please try again.'
            flash(error, 'error')
    return render_template('login.html', title='Login Page')


#Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        return render_template('dashboard.html', title='Dashboard', current_page = 'dashboard', user=user)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#Customer
@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
    
        # Get page number from request arguments, default to 1
        page = request.args.get('page', 1, type=int)
        
        # Paginate products (10 per page)
        customers = Customer.query.filter(Customer.user_id == user.id).paginate(page=page, per_page=10)
        total_customer = Customer.query.filter(Customer.user_id == user.id).count()

        return render_template('customer.html', title='Customer', current_page='customer', 
                               user=user, customers=customers, total_customer=total_customer, min=min, enumerate=enumerate)

    else:
        flash('You need to login first.', 'error')
        return redirect('/login')
    
#Download Excel
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


#add_customer
@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        if request.method == 'POST':
            customer_name = request.form['customer_name']
            customer_village = request.form['customer_vill_name']
            customer_mob_no = request.form['mobile_number']
        
            new_data = Customer(user_id=user.id, customer_name=customer_name, customer_village=customer_village, customer_mob_no=customer_mob_no)
            db.session.add(new_data)
            db.session.commit()
            flash('Customer Added Successful.', 'success')

        return render_template('add_customer.html', title='Add Customer', current_page = 'add_customer', user=user)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')

#Products
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        # products = Products.query.filter(Products.user_id == user.id).all()

        # Get page number from request arguments, default to 1
        page = request.args.get('page', 1, type=int)
        
        # Paginate products (10 per page)
        products = Products.query.filter(Products.user_id == user.id).paginate(page=page, per_page=10)
        total_product = Products.query.filter(Products.user_id == user.id).count()

        return render_template('product.html', title='Products', current_page='products', 
                               user=user, products=products, total_product=total_product, min=min, enumerate=enumerate)

    else:
        flash('You need to login first.', 'error')
        return redirect('/login')
    
#Download Excel
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

#Products
@app.route('/add_product', methods=['GET', 'POST'])
def add_products():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()

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
        return render_template('add_product.html', title='Add Products', current_page = 'add_product', user=user)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')
    
@app.route('/edit_product/<int:prod_id>', methods=['GET'])
def edit_product(prod_id):
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        product = Products.query.filter_by(prod_id=prod_id, user_id=user.id).first()

        if not product :
            flash('Data not found or you do not have permission to edit this data.', 'error')
            return redirect('/products')
        
        return render_template('edit_product.html', title='Edit Product', user=user, product=product)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')
    

@app.route('/update_data/<int:prod_id>', methods=['POST'])
def update_data(prod_id):
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        product = Products.query.filter_by(prod_id=prod_id, user_id=user.id).first()

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


@app.route('/delete_product/<int:prod_id>', methods=['GET'])
def delete_product(prod_id):
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        if not user:
            flash('User not found.', 'error')
            return redirect('/login')

        product = Products.query.filter_by(prod_id=prod_id, user_id=user.id).first()
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


        return render_template('billing.html', title='Billing', current_page = 'billing', user=user, customers=customers, products=products)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')
    

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


@app.route('/admin/billing', methods=['GET', 'POST'])
def create_bill():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()

        if request.method == 'POST':
            print(request.form)  # Debugging Step

            customer_id = request.form.get('customer_id')
            product_ids = request.form.getlist('product_id')  # ✅ Fix applied
            amount_paid = float(request.form.get('amount_paid', 0))

            if not customer_id or not product_ids:
                flash("Please select a customer and at least one product!", "danger")
                return redirect(url_for('create_bill'))

            # Process Billing
            total_amount = 0
            billing = Billing(customer_id=customer_id, billing_date=india_time, total_amount=0, amount_paid=amount_paid, dues=0)
            db.session.add(billing)
            db.session.flush()  # Get billing ID before committing

            for product_id in product_ids:
                quantity = int(request.form.get(f'quantity_{product_id}', 0))  # ✅ Fix applied
                product = db.session.get(Products, product_id)

                if product and product.prod_quantity >= quantity:
                    total_price = product.prod_sell_price * quantity
                    total_amount += total_price

                    # Deduct stock
                    product.prod_quantity -= quantity

                    # Add to BillingDetails
                    bill_detail = BillingDetails(
                        billing_id=billing.id,
                        product_id=product.prod_id,
                        quantity=quantity,
                        total_price=total_price
                    )
                    db.session.add(bill_detail)
                else:
                    flash(f"Insufficient stock for {product.prod_name}!", "danger")
                    return redirect(url_for('create_bill'))

            # Calculate dues
            billing.total_amount = total_amount
            billing.dues = total_amount - amount_paid

            db.session.commit()
            flash("Billing successful!", "success")
            return redirect(url_for('create_bill'))
        
        customers = Customer.query.filter_by(user_id=user.id).all()
        products = Products.query.filter_by(user_id=user.id).all()
        return render_template('billing_org.html', customers=customers, products=products)
    
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')


#Invoice
@app.route('/invoice', methods=['GET', 'POST'])
def invoice():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        return render_template('invoice.html', title='Invoice', current_page = 'invoice', user=user)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')


#Contact_us
@app.route('/about_us')
def about_us():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        return render_template('about_us.html', title='About Us', current_page = 'about_us', user=user)
    else:
        flash('You need to login first.', 'error')
        return redirect('/login')
    

#Contact_us
@app.route('/contact_us', methods=['GET', 'POST'])
def contact_us():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        return render_template('contact_us.html', title='Contact Us', current_page = 'contact_us', user=user)
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
