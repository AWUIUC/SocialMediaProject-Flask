#####################################################################################
#################################### GENERAL IMPORTS AND CREATE+CONFIGURE APP #######
#####################################################################################
import os # for view save_picture
from PIL import Image #PIL is from Pillow and is used for image resizing when user uploads profile picture

from flask import Flask

from flask_sqlalchemy import SQLAlchemy                             # db setup
from flask_script import Manager                                    # db migrations
from flask_migrate import Migrate, MigrateCommand                   # db migrations
from flask_bcrypt import Bcrypt                                     # user registrations: for hashing passwords AND checking password hashes
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required # for login managing in sessions
from flask_mail import Mail, Message                                # for password reset
from flask import render_template, url_for, flash, redirect, request  # general functions needed
from datetime import datetime                                       # for time of user sign up
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer # for user password reset token
from flask_socketio import SocketIO, send, emit, join_room, leave_room # for chat app functionality
from time import localtime, strftime                                 # for time to display in chat
from time import gmtime # for creating utctime objects to be stored in private messages table (to record when private messages are sent)


# create and configure the app
app = Flask(__name__)
app.config['SECRET_KEY']="REDACTED"
app.config['SQLALCHEMY_DATABASE_URI']="REDACTED"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=True
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' #function name of route is passed into here (same thing we put into url_for)
login_manager.login_message_category = 'info'

# Initialize Flask-SocketIO
socketio = SocketIO(app)

# PREDEFINED VARIABLES FOR CHATTING/MESSAGING
ROOMS=["lounge", "news", "games", "coding"]
sid_database = {}

# PREDEFINED VARIABLES FOR RANDOM USER MATCHING
daily_random_numbers = [1, 2, 3, 4, 5]

app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "REDACTED"
app.config['MAIL_PASSWORD'] = "REDACTED"
mail = Mail(app)

################################################# SETUP FOR RANDOM NUMBER GENERATION EVERY 24 HOURS ###############################
from apscheduler.schedulers.background import BackgroundScheduler
import random

def tick():
    try:
        num_users = User.query.count()
        num_users_plus_one = num_users + 1
        # in order to do random sampling without replacement, we use random.sample
        # random.sample(population, k) will return a k length list of unique elements chosen from population
        # here we are choosing 10 numbers at random from a range of 1 to the num_users
        # keep in mind that we are purposely using num_users_plus_one
        # ex: the code below will print 1, 2, 3, 4, 5, 6, 7, and 8, BUT NOT 9!!!!!
        #   temp = range(1, 9)
        #   for var in temp:
        #     print(var)
        # thus since range is not inclusive of the last element, we use the last_element plus one in using range
        toReplace = random.sample(range(1, num_users_plus_one), 5)
        daily_random_numbers[0] = toReplace[0]
        daily_random_numbers[1] = toReplace[1]
        daily_random_numbers[2] = toReplace[2]
        daily_random_numbers[3] = toReplace[3]
        daily_random_numbers[4] = toReplace[4]
    except ValueError:
        print('Sample size exceeded population size.')

scheduler = BackgroundScheduler()
scheduler.add_job(tick, 'interval', seconds=5)
scheduler.start()

####################################################################################################################################

if __name__=='__main__':
    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()

    socketio.run(app, debug=True)
    manager.run()



##################################################################################################
##################################### MODELS #####################################################
##################################################################################################
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)

    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)


    interests_and_hobbies = db.Column(db.String(180), nullable=False, default='')
    courses   = db.Column(db.String(180), nullable=False, default='')
    major     = db.Column(db.String(180), nullable=False, default='')

    def get_reset_token(self, expires_sec=1800):                                # expires_sec=1800 is 30 minutes that token is valid for
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id' : self.id}).decode('utf-8')

    @staticmethod                                                               # static method tells python not to expect self as an argument
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}', '{self.first_name}', '{self.last_name}')"

class Friends(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    friend_one = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_two = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    status = db.Column(db.Integer, nullable=False) #0 for pending, 1 for accepted
                                                   # later: 1 for declined and 2 for blocked


    def __repr__(self):
        return f"User('{self.id}', '{self.friend_one}', '{self.friend_two}', '{self.status}')"

class PrivateMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
    recipient_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
    message = db.Column(db.String(2000))
    time_sent = db.Column(db.DateTime)                        # THIS IS UTC TIME DO NOT FORGET THIS!!!!!!!!!!!!!
####################################################################################
############################################# FORMS ################################
####################################################################################


from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError

class RegistrationForm(FlaskForm):
    first_name = StringField('First name', validators=[DataRequired()])
    last_name = StringField('Last name', validators=[DataRequired()])

    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different email.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account associated with that email. You must register first. ')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])

    interests_and_hobbies = StringField('Interests and Hobbies', validators=[Length(min=0, max=180)])
    courses = StringField('Courses', validators=[Length(min=0, max=180)])
    major = StringField('Major', validators=[Length(min=0, max=180)])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])

    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different username.')

class EmailSearchForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired()])
    #submit = SubmitField('Submit button #1 here')

class NameSearchForm(FlaskForm):
    first_name = StringField('First name', validators=[DataRequired(), Length(min=2, max=20)])
    last_name  = StringField('Last name', validators=[DataRequired(), Length(min=2, max=20)])
    #submit     = SubmitField('Submit button #2 here')

############################################ SETUP DONE ################################
########################################################################################
########################################################################################
@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    else:
        form = RegistrationForm()
        if form.validate_on_submit():
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(first_name = form.first_name.data, last_name = form.last_name.data,
                        username=form.username.data, email=form.email.data, password=hashed_password)
            db.session.add(user)
            db.session.commit()

            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('login'))
        return render_template('auth/register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    else:
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data): #simultaneously check user exists and password is same as in database
                login_user(user, remember=form.remember.data)

                next_page = request.args.get('next')                           # allows us to redirect (after login) if user was originally trying to go to a restricted page

                return redirect(next_page) if next_page else redirect(url_for('home'))
            else:
                flash('Login unsuccessful. Please try again. ', 'danger')
        return render_template('auth/login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('welcome'))

#route where user enters an email to request a token for pw reset
@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('auth/reset_request.html', title='Reset Password', form=form)

#route where user actually resets password with active token
@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()

        flash('Your password has been changed. Your are now able to log in!', 'success')
        return redirect(url_for('login'))
    return render_template('auth/reset_token.html', title='Reset Password', form=form)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                sender="REDACTED",
                recipients=[user.email]) #subject line, sender, list of recipients,

    # f string is used for email body since we are using python 3.6 or higher; otherwise we would need to use string formatting
    msg.body=f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request, then simply ignore this email and no changes will be made.
'''
    mail.send(msg)

@app.route("/")
def welcome():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('auth/welcome.html')

"""
@app.route('/about-and-faq')
def AboutAndFAQ():
    return render_template('auth/about_and_faq.html')
"""

@app.route("/home")
@login_required
def home():
    total_num_users = User.query.count()
    current_user_id = current_user.id
    offset_user_ids = []
    for number in daily_random_numbers:
        offset_user_ids.append((number%total_num_users)+1)
    name_id_dictionary = {}
    for number in offset_user_ids:
        potential_friend = User.query.get(number)
        full_name_of_potential_friend = potential_friend.first_name + " " + potential_friend.last_name
        name_id_dictionary[full_name_of_potential_friend] = number
    return render_template('auth/home.html', potential_friends_dictionary = name_id_dictionary)

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    f_name, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext      #picture_fn is picture file name
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route("/update_profile", methods=['GET', 'POST'])
@login_required
def update_profile():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.interests_and_hobbies = form.interests_and_hobbies.data
        current_user.courses = form.courses.data
        current_user.major = form.major.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('update_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.interests_and_hobbies.data = current_user.interests_and_hobbies
        form.courses.data = current_user.courses
        form.major.data = current_user.major
    image_file = url_for('static', filename='profile_pics/'+ current_user.image_file)
    return render_template('social/update_profile.html', title='Update Profile', image_file=image_file, form = form)

@app.route("/profile/view/<int:user_id>", methods=['GET', 'POST'])
@login_required
def view_profile(user_id):
    user_to_view = load_user(user_id=user_id)

    already_added = Friends.query.filter_by(friend_one = current_user.id).filter_by(friend_two = user_id).first()

    if already_added is None:
        already_added = False
    else:
        already_added = True

    if user_to_view is None:
        image_file = None
    else:
        image_file = url_for('static', filename='profile_pics/'+ user_to_view.image_file)

    return render_template('social/view_profile.html', title='View Profile', other_user=user_to_view, image_file=image_file, already_added=already_added)


@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():
    search_email_form = EmailSearchForm()
    search_name_form = NameSearchForm()
    if search_email_form.validate_on_submit():
        toSearch = "%{}%".format(search_email_form.email.data)
        queried_users = User.query.filter(User.email.like(toSearch)).all()
        return render_template('search/search_users.html', search_email_form=search_email_form, search_name_form=search_name_form, queried_users=queried_users)
    if search_name_form.validate_on_submit():
        toSearch1 = "%{}%".format(search_name_form.first_name.data)
        toSearch2 = "%{}%".format(search_name_form.last_name.data)
        queried_users = User.query.filter(User.first_name.like(toSearch1)).filter(User.last_name.like(toSearch2)).all()
        return render_template('search/search_users.html', search_email_form=search_email_form, search_name_form=search_name_form, queried_users=queried_users)
    return render_template('search/search_users.html', search_email_form = search_email_form, search_name_form = search_name_form, queried_users=None)


@app.route("/profile/add/<int:user_id>", methods=['GET', 'POST'])
@login_required
def add_friend(user_id):
    curr_user_id = current_user.id
    other_user_id = user_id
    curr_status = 0

    toAdd = Friends(friend_one = curr_user_id, friend_two = other_user_id, status = curr_status)
    db.session.add(toAdd)
    db.session.commit()

    return redirect(url_for('view_profile', user_id = other_user_id))

@app.route("/friends/cancel_request/<int:user_id>", methods=['GET', 'POST'])
@login_required
def cancel_request(user_id):

    toDelete = Friends.query.filter_by(friend_one = current_user.id).filter_by(friend_two = user_id).first()
    db.session.delete(toDelete)
    db.session.commit()

    return redirect(url_for('view_friends'))

@app.route("/friends/decline_request/<int:user_id>", methods=['GET', 'POST'])
@login_required
def decline_request(user_id):
    toDelete = Friends.query.filter_by(friend_one = user_id).filter_by(friend_two = current_user.id).first()
    db.session.delete(toDelete)
    db.session.commit()

    return redirect(url_for('view_friends'))

@app.route("/friends/accept_request/<int:user_id>", methods=['GET', 'POST'])
@login_required
def accept_request(user_id):
    toModify = Friends.query.filter_by(friend_one = user_id).filter_by(friend_two = current_user.id).first()
    toModify.status = 1
    db.session.commit()

    return redirect(url_for('view_friends'))

@app.route("/friends/remove_friend/<int:user_id>", methods=['GET', 'POST'])
@login_required
def remove_friend(user_id):
    toDelete = Friends.query.filter_by(friend_one = current_user.id).filter_by(friend_two = user_id).first()
    if toDelete is None:
        toDelete = Friends.query.filter_by(friend_two = current_user.id).filter_by(friend_one = user_id).first()
    db.session.delete(toDelete)
    db.session.commit()

    return redirect(url_for('view_friends'))


@app.route("/friends/manage", methods=['GET', 'POST'])
@login_required
def view_friends():
    # friend_one is person request was made from
    # friend_two is person request was sent to
    sent_friend_requests = Friends.query.filter_by(friend_one = current_user.id).filter_by(status=0).all() #cancel button in table
    received_friend_requests = Friends.query.filter_by(friend_two = current_user.id).filter_by(status=0).all() #accept (change status) and decline button (delete relation)

    """
    for thing in sent_friend_requests:
        print(thing.id)
        print(thing.friend_one)
        print(thing.friend_two)
        print(thing.status)
    """

    #my friends where I (friend_one) sent friend request to them (friend_two)
    confirmed_friends_pt1 = Friends.query.filter_by(friend_one = current_user.id).filter_by(status=1).all()     # unfriend button in table (delete record)

    #my friends where I (friend_two) accepted friend request from them (friend_one)
    confirmed_friends_pt2 = Friends.query.filter_by(friend_two = current_user.id).filter_by(status=1).all()     # unfriend button in table (deletes record)

    return render_template('social/manage_friends.html', sent_friend_requests = sent_friend_requests, received_friend_requests=received_friend_requests, confirmed_friends_pt1=confirmed_friends_pt1, confirmed_friends_pt2=confirmed_friends_pt2)


#########################################################################################################
##################################### GROUP MESSAGING ###################################################
#########################################################################################################
@app.route("/chat", methods=['GET', 'POST'])
@login_required
def view_chat():
    return render_template('chat/chat_rooms.html', username=current_user.username, rooms=ROOMS)


# EVENT BUCKETS
@socketio.on('message')
def message(data):
    print(f"\n\n{data}\n\n")
    send({'msg': data['msg'], 'username': data['username'], 'time_stamp': strftime('%b-%d %I:%M%p', localtime()), 'room':data['room']})
    # emit('some-event', 'This is a custom event message')

@socketio.on('join')
def join(data):
    print(request.sid)
    join_room(data['room'])
    send({'msg': data['username']  + " has joined the " + data['room'] + " room."}, room=data['room'])

@socketio.on('leave')
def leave(data):
    leave_room(data['room'])
    send({'msg': data['username']  + " has left the " + data['room'] + " room."}, room=data['room'])

##############################################################################################################
################################### PRIVATE MESSAGING ########################################################
##############################################################################################################
@app.route("/privatechat", methods=['GET', 'POST'])
@login_required
def private_chat():
    #people = {}
    people = []

    #my friends where I (friend_one) sent friend request to them (friend_two)
    confirmed_friends_pt1 = Friends.query.filter_by(friend_one = current_user.id).filter_by(status=1).all()     # unfriend button in table (delete record)
    for friend in confirmed_friends_pt1:
        other_user = User.query.get(friend.friend_two)
        other_user_email = str(other_user.email)
        people.append(other_user_email)
        #people[other_user_email] = friend.id # people['id of your friend'] = id of your friendship

    #my friends where I (friend_two) accepted friend request from them (friend_one)
    confirmed_friends_pt2 = Friends.query.filter_by(friend_two = current_user.id).filter_by(status=1).all()     # unfriend button in table (deletes record)
    for friend in confirmed_friends_pt2:
        other_user = User.query.get(friend.friend_one)
        other_user_email = str(other_user.email)
        people.append(other_user_email)
        #people[other_user_email] = friend.id

    # Default chat room is the user with him/her self
    # So person can be automatically entered into a chat room with himself
    people.append(current_user.email)


    initial_messages_query_results = PrivateMessages.query.filter_by(sender_email = current_user.email).filter_by(recipient_email=current_user.email).all()
    initial_message_list = []
    for private_message_obj in initial_messages_query_results:
         tempVar = []
         tempVar.append(str(private_message_obj.sender_email))
         tempVar.append(str(private_message_obj.recipient_email))
         tempVar.append(str(private_message_obj.message))
         initial_message_list.append(tempVar)
    #print(initial_message_list)

    return render_template('chat/private_chat.html', user_email=current_user.email, friend_list=people, initial_messages=initial_message_list)


@socketio.on('add_or_update_sid')
def add_or_update_sid():
    #print("Before updating/adding: ")
    #print(sid_database)
    sid_database[current_user.email] = request.sid
    #print("After updating/adding: ")
    #print(sid_database)

@socketio.on('disconnect')
def remove_sid():
    #print('SOMEONE DISCONNECTED')
    if (sid_database.get(current_user.email) is not None):
        #print("Before popping: ")
        #print(sid_database)
        sid_database.pop(current_user.email)
        #print("After popping: ")
        #print(sid_database)

@socketio.on('private_message')
def private_message(payload):
    sender_email = current_user.email
    sender_session_id = request.sid

    recipient_actual_email = payload['recipient_email']
    try:
        recipient_session_id = sid_database[recipient_actual_email]
    except:
        recipient_session_id = None

    message = payload['message']

    if sender_session_id is recipient_session_id: # to handle case when person talking to him/herself, only emit once
        emit('receive_new_private_message', {'sender': sender_email, 'recipient': recipient_actual_email, 'message_data':message}, room = sender_session_id)
    else: # to handle case when person talking to someone not him/herself, emit twice
        if sender_session_id is not None:
            emit('receive_new_private_message', {'sender': sender_email, 'recipient': recipient_actual_email, 'message_data':message}, room = sender_session_id)
        if recipient_session_id is not None:
            emit('receive_new_private_message', {'sender': sender_email, 'recipient': recipient_actual_email, 'message_data':message}, room = recipient_session_id)

    print(sender_email)
    print(recipient_actual_email)
    print(message)

    MessageToAdd = PrivateMessages(sender_email=sender_email, recipient_email=recipient_actual_email, message=message, time_sent=gmtime())
    db.session.add(MessageToAdd)
    db.session.commit()

@socketio.on('get_message_history')
def get_message_history(dict_var):
    other_person_email = dict_var['recipient_user_email']

    initial_messages_query_1 = PrivateMessages.query.filter_by(sender_email=current_user.email).filter_by(recipient_email=other_person_email)
    initial_messages_query_2 = PrivateMessages.query.filter_by(sender_email=other_person_email).filter_by(recipient_email=current_user.email)

    # for the case that the user clicks on an email != his/her email
    initial_messages_query_results = initial_messages_query_1.union(initial_messages_query_2).order_by(PrivateMessages.time_sent.asc())

    # for the case that the user decides to click on his/her email
    if other_person_email == current_user.email:
        initial_messages_query_results = initial_messages_query_1

    for private_message_obj in initial_messages_query_results:
        emit('receive_new_private_message', {'sender': private_message_obj.sender_email,
                                            'recipient': private_message_obj.recipient_email,
                                            'message_data': private_message_obj.message },
                                            room = request.sid)
