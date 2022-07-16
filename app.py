from http import client
from flask import Flask, url_for, session
from flask import render_template, redirect
from authlib.integrations.flask_client import OAuth
import pymongo


app = Flask(__name__,template_folder='template')
app.secret_key = '!secret'
app.config.from_object('config')

try:
    mongo = pymongo.MongoClient(
        host = "localhost",
        port = 27017,
        serverSelectionTimeoutMS = 1000
    )
    db = mongo.tallycodebrewers
    mongo.server_info()
except:
    print("Error connecting to the DB")

# database collection here
admin = db.admin
quiz = db.quiz
user = db.user


#conif here
CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id= '999097678090-v86dv9cu26b7divijtn4bjjkug54pqlj.apps.googleusercontent.com',
    client_secret= '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',
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

#admin side login
@app.route('/')
def homepage():
    if 'user' in session:
        user = session.get('user')
        return user
    return render_template('login.html')
    # return render_template('home.html', user=user)

#admin side login
@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

#admin side login
@app.route('/authorize')
def authorize():
    token = oauth.google.authorize_access_token()
    user = token.get('userinfo')
    if user:
        session['user'] = user
    if admin.find_one({'user_email': user['email']})==None:
        admin.insert_one({'user_email': user['email'], 'user_name': user['name']})
    return redirect('/')

#admin side login
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


# admin post_quiz page
@app.route('/post_quiz')
def post_quiz():
    pass

#admin whole quiz page
@app.route('/quizzes')
def quizzes():
    current_user = session.get('user')
    current_user_email = current_user['email']
    user_data = admin.find_one({'user_email': current_user_email })
    quiz_details = []
    print('quizzes' in user_data)
    if 'quizzes' in user_data:
        for each_quiz in user_data['quizzes']:
            data = quiz.find_one({'_id':each_quiz})
            quiz_details.append({'name': data['name'], 'date_added': 'yet' , 'valid_upto': 'to add' })
        print(quiz_details)
        return render_template('quiz_data.html',all_quiz=quiz_details)
    else:
        return render_template('quiz_data.html')



if __name__ == '__main__':
    app.run(debug=True)