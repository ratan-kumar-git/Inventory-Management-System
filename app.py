from flask import Flask, render_template, request, redirect, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from io import BytesIO
import bcrypt

app = Flask(__name__)

# Make Connection with Data Base
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.secret_key = 'Bablu@12345'

db = SQLAlchemy(app)


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
    

with app.app_context():
    db.create_all()


# Home Page
@app.route('/')
def index():
    return render_template('home.html', title='Home')

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
        return render_template('billing.html', title='Billing', current_page = 'billing', user=user)
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
