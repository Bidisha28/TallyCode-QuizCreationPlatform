from cgi import test
from crypt import methods
from datetime import date, datetime
from unicodedata import name
import bcrypt
from flask import Flask, flash, jsonify, request, url_for, session
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
questions_db = db.questions
test_taker = db.testtakers

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
        return render_template('home.html', name=user['name'])
    return render_template('login.html')
    # return render_template('home.html', user=user)


#admin side register
@app.route('/register',methods=['POST','GET'])
def register():
    if request.method=='POST':
        if admin.find_one({'user_email': request.form.get('email')})==None:
            if admin.find_one({'user_name': request.form.get('name')})==None:
                if request.form.get('pass')==request.form.get('pass2'):
                    hashpass = bcrypt.hashpw(request.form['pass'].encode('utf-8'),bcrypt.gensalt())
                    admin.insert_one({'user_email': request.form.get('email'), 'user_name': request.form.get('name'), 'pwd': hashpass })
                    session['user'] = {'email':request.form.get('email'), 'name':request.form.get('name') }
                    return redirect('/')
    return render_template('Register.html')


#admin normal login page
@app.route('/login', methods=['POST','GET'])
def login():
    if request.method=='POST':
        login_user = admin.find_one({'user_name': request.form['name']})
        if login_user:
            if bcrypt.hashpw(request.form['pass'].encode('utf-8'), login_user['pwd']) == login_user['pwd']:
                session['user'] = {'email':login_user['user_email'], 'name':request.form.get('name') }
                return redirect('/')
    return redirect('/')


#admin side google login
@app.route('/google_login' )
def google_login():
    redirect_uri = url_for('authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

#admin side login through google accounts
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
@app.route('/post_quiz',methods=['POST','GET'])
def post_quiz():
    current_user = session.get('user')
    current_user_email = current_user['email']
    user_data = admin.find_one({'user_email': current_user_email })
    if request.method == 'POST':
        questions_obj = questions_db.find({'admin': user_data['_id']})
        questions=[]
        for doc in questions_obj:
            questions.append(doc['question'])
        questions_db.drop()
        quiz_id = quiz.insert_one({'admin':user_data['_id'],'quiz_name': request.form.get('quiz_name') ,'date_added': request.form.get('date_added') , 'valid_upto': request.form.get('valid_upto'),'question':questions}).inserted_id
        # quiz_id = quiz.insert_one({'admin':user_data['_id'],'quiz_name': request.form.get('quiz_name') }).inserted_id
        if 'quizzes' in user_data:
            admin.update_one({'_id':user_data['_id']}, {'$push': {'quizzes': quiz_id}})
        else:
            admin.find_one_and_update({'_id':user_data['_id']},{'$set': {'quizzes': [quiz_id]} })
        return redirect('/')
    else:
        questions_obj = questions_db.find({'admin': user_data['_id']})
        questions=[]
        for doc in questions_obj:
            questions.append(doc['question'])
        return render_template('post_quiz.html',questions = questions, name=current_user['name'])


@app.route('/add',methods=['POST','GET'])
def add():
    if request.method=='POST':
        current_user = session.get('user')
        current_user_email = current_user['email']
        user_data = admin.find_one({'user_email': current_user_email })
        questions_db.insert_one({'admin':user_data['_id'],
         'question':[request.form.get('question') ,
         request.form.get('option1'),
         request.form.get('option2'),
         request.form.get('option3') ,
         request.form.get('option4') ,
         request.form.get('answer'),request.form.get('dropdown')]})
        return redirect('/post_quiz')
    # return  render_template('add_question.html')



#admin whole quiz page
@app.route('/quizzes')
def quizzes():
    current_user = session.get('user')
    current_user_email = current_user['email']
    user_data = admin.find_one({'user_email': current_user_email })
    quiz_details = []
    if 'quizzes' in user_data:
        for each_quiz in user_data['quizzes']:
            data = quiz.find_one({'_id':each_quiz})
            quiz_details.append({'name': data['quiz_name'], 'date_added': data['date_added'] , 'valid_upto': data['valid_upto'] })
            # quiz_details.append({'name': data['quiz_name']})
        return render_template('quiz_data.html',all_quiz=quiz_details,name=current_user['name'])
    else:
        return render_template('quiz_data.html',name=current_user['name'])


#test_taker data here
@app.route('/view_data/<quiz_name>')
def view_data(quiz_name):
    current_user = session.get('user')
    qd = quiz.find_one({'quiz_name':quiz_name})
    print(qd['_id'])
    takers = test_taker.find({'quiz_id':qd['_id']}).sort('score',pymongo.DESCENDING)
    test_data = []
    for doc in takers:
        test_data.append({'name':doc['name'],'score':doc['score'],'quiz_name': quiz_name, 'email': doc['email']})
    return render_template('test_Taker_data.html',name=current_user['name'],takers = test_data)


#quiz taker side
@app.route('/<quiz_name>/<name>',methods=['POST','GET'])
def take_quiz(quiz_name,name):
    quiz_data = quiz.find_one({'quiz_name':quiz_name})
    questions = quiz_data['question']
    if request.method=='POST':
        l=[]
        total_score = 0
        score = 0
        for q in (questions):
            l.append(request.form.get(q[0]))
            total_score+=int(q[6])
            if l[-1] == q[5]:
                score+=int(q[6])
        test_taker.insert_one({'quiz_id': quiz_data['_id'],'name': name, 'answers': l, 'score':score, 'total_score': total_score, 'email': '-'})
        return redirect(url_for('result',quiz_name=quiz_name,name=name))
    return render_template('question.html',questions=questions,quiz_name=quiz_name,name=name)

#after quiz
@app.route('/result/<quiz_name>/<name>',methods=['GET','POST'])
def result(quiz_name,name):
    quiz_data = quiz.find_one({'quiz_name':quiz_name})
    data = test_taker.find_one({'quiz_id':quiz_data['_id'],'name':name})
    message = ''
    percentage = (data['score']/data['total_score'])*100
    if percentage >= 80:
        message+=f'Congrats you have performed well in the exam scoring {percentage}%'
    elif percentage>=40 and percentage<=80:
        message+=f'Congrats you have qualified the exam with {percentage}%'
    else:
        message+=f'Sorry you didnt qualify'
    if request.method =='POST':
        email = request.form.get('email')
        feedback = request.form.get('feedback')
        print(email,feedback)
        test_taker.update_one({'name': name},{'$set': {'email': email}})
        return redirect('https://www.google.com/')
    return render_template('afterquiz1.html',score=data['score'],total_score=data['total_score'],name=name,message=message, percentage=percentage,quiz_name=quiz_name)



@app.route('/<quiz_name>/gen',methods=['GET','POST'])
def gen(quiz_name):
    if request.method =='POST':
        name = request.form.get('name')
        quiz_id = quiz.find_one({'quiz_name':quiz_name})
        start = quiz_id['date_added']
        end = quiz_id['valid_upto']
        tt = test_taker.find({'quiz_id':quiz_id['_id']})
        names = []
        for id in tt:
            names.append(id['name'])
        if name in names:
            message = 'Try another name. its already taken by other user'
            return render_template('quiz_template1.html',quiz_name=quiz_name,message=message)
        return redirect(url_for('take_quiz',quiz_name=quiz_name,name=name))
    message=""
    # quiz_id = quiz.find_one({'quiz_name':quiz_name})
    # start = quiz_id['date_added']
    # print(start)
    # end = quiz_id['valid_upto']
    # print(datetime.now())
    return render_template('quiz_template1.html',quiz_name=quiz_name,message=message)



if __name__ == '__main__':
    app.run(debug=True)