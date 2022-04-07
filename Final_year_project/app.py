from flask import Flask, session, render_template,request,redirect,g,url_for

import os
app = Flask(__name__)

app.secret_key = os.urandom(25)


@app.route('/login', methods = ["POST"/"GET"])
def index():
    if request.method == 'POST':
        session.pop('user', None) #Drop the session before post request

        if request.form['Password'] == 'shivam123': #Use database here in future
            session['user'] = request.form['Username']
            return redirect(url_for('proff'))

    return render_template('login.html')

@app.route('/proff')
def proff():
    if g.user:
        return render_template('profile.html', user=session['user'])
    return redirect(url_for('index'))

@app.before_request
def before_request():
    g.user = None

    if 'user' in session:
        g.user = session['user']

@app.route('/dropsession')
def dropsession():
    session.pop('user', None)
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
