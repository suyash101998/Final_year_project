from enum import Flag
from uuid import uuid4
from logging import debug
from datetime import datetime
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, url_for, redirect, session, flash, jsonify
import sqlite3 as sql
from profanityfilter import ProfanityFilter
from textblob import TextBlob
import collections
from collections import Counter
import wordcloud
from wordcloud import WordCloud, STOPWORDS
from random import randint
import os
import re
import json
import string
from functools import wraps
currentdirectory = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "static/upload"
app.config['TEMPLATES_AUTO_RELOAD'] = True
ALLOWED_EXTENSIONS = {'csv', 'xls'}
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
global temp
temp = False

pf = ProfanityFilter()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' is session:
            return f(*args, **kwargs)
        else:
            return 'cannot access'
    return decorated_function


@app.route("/")
def main():
    return render_template('landing.html', flag=temp)


@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    if request.method == 'POST':
        print("Breakpoint")
        print(request)
        email = request.form['username']
        print(email)
        password = request.form['password']
        print(password)
        with sql.connect("mainData.db") as con:
            con.row_factory = sql.Row
            cur = con.cursor()
            cur.execute("select * from UserTable where email=(?)", [email])
            res = cur.fetchone()
            print(res)
        con.close()
        if res is None:
            return "Invalid username"
        else:
            pwd = res['password']
            user = res['userType']
            wardNum = res['WardNum']
            session['wardNum']=wardNum
            
            print(pwd)
            if (password == pwd):
                session['logged_in'] = True
                global temp
                temp = True
                if (user == 'mayor'):
                    session['userType'] = 'mayor'
                elif (user == 'wc'):
                    session['userType'] = 'wc'
                else:
                    session['userType'] = "citizen"
                print("this is", temp)
                session['email'] = res['email']
                # return 'You are now logged in', 'success'

                return redirect(url_for('profile'))

            else:
                return "Invalid password"


@app.route("/bulksignup", methods=['POST', 'GET'])
def bulksignup():
    if not temp:
        return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template('bulk_signup.html', flag=temp)
    if request.method == "POST":
        print(request.files)
        
        print(request.files["upload"])
        uploaded = request.files["upload"]
        uploaded.save(os.path.join(
            app.config['UPLOAD_FOLDER'], uploaded.filename))
        # data = extract_data(os.path.join(app.config['UPLOAD_FOLDER'], uploaded.filename))
        # os.remove(os.path.join(app.config['UPLOAD_FOLDER'], uploaded.filename))
        with sql.connect("mainData.db") as con:
            
            filterData = []
            with open(os.path.join(
                app.config['UPLOAD_FOLDER'], uploaded.filename),'r') as data:
                # print(data.read())
                for i in data.readlines() :
                    temparray = i.split(',')[1:-1:]
                    tempt= {'Email':temparray[4],'FullName':temparray[0],'ContactNum':temparray[1],'WardNum':temparray[2],'WardName':temparray[3],'Password':temparray[0]+'123'}
                    cur = con.cursor()
                    cur.execute(
                    "INSERT into UserTable2 (FullName, ContactNum,WardNum,WardName,Password,Email,userType) values (?,?,?,?,?,?,?)", (tempt['FullName'], tempt['ContactNum'], tempt['WardNum'], tempt['WardName'],tempt['Password'],tempt['Email'],"citizen"))
                    con.commit()
                    filterData.append(tempt)
                print(filterData[1])
        # con.close()
        return redirect(url_for('bulksignup'))



@app.route("/profile")
def profile():
    # print(session['logged_in'])
    if not temp:
        return redirect(url_for('login'))
    else:
        userType = session['userType']
        with sql.connect("mainData.db") as con:
            cur = con.cursor()
            cur.execute("select * from UserTable where email=(?)",
                        [session['email']])
            # cur.execute("select * from UserTable where email=(?)",session['email'])
            res = cur.fetchall()
            print(res)
            return render_template('profile.html', flag=temp, res=res, userType=userType)
        con.close()


@app.route("/form", methods=['POST', 'GET'])
def form():
    if not temp:
        return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template('form2.html', flag=temp,ward = session['wardNum'])
    if request.method == "POST":
        FullName = request.form["name"]
        FullName = FullName.lower()
        with sql.connect("mainData.db") as con:
            cur = con.cursor()
            cur.execute(
                "select UserId, WardNum, WardName ,FullName from UserTable where lower(FullName)=(?) limit 1", [FullName])
            user = cur.fetchall()
            print(user)
        UserId = user[0][0]
        WardNum = user[0][1]
        WardName = user[0][2]
        FullName = user[0][3]
        con.close()
        ContactNum = request.form["contact_number"]
        CompCat = request.form["role"]
        CompDesc = request.form["description"]
        if not(pf.is_clean(CompDesc)):
            CompDesc = "Your service is bad"
        CompDesc = CompDesc.split(r'\n')
        CompDesc = ' '.join(CompDesc)
        CompDesc = CompDesc.lower()
        CompDesc = re.sub('\n', '', CompDesc)
        CompDesc = re.sub('[''""...]', '', CompDesc)
        CompDesc = re.sub(r'#', '', CompDesc)
        CompDesc = re.sub('\[.*?\n]', '', CompDesc)
        CompDesc = re.sub('[%s]' % re.escape(string.punctuation), '', CompDesc)
        CompDesc = re.sub('\w*\d\w*', '', CompDesc)
        analysis = TextBlob(CompDesc)
        senval = round(analysis.sentiment.polarity, 2)
        Date = request.form["date"]
        # l = Date.split('-')
        # print(l)
        # if l[1][0] == '0':
        #     l[1] = l[1][1]
        # strDate = l[1]+'/'+l[2]+'/'+l[0]
        with sql.connect("mainData.db") as con:
            cur = con.cursor()
            cur.execute(
                "INSERT into ComplaintTable (FullName, UserID, ContactNum,WardNum,WardName,CompCat,CompDesc,date,senval) values (?,?,?,?,?,?,?,?,?)", (FullName, UserId, ContactNum, WardNum, WardName, CompCat, CompDesc, Date, senval))
            con.commit()
            # msg = "Feedback successfully Added"
        con.close()
        return render_template('form2.html', flag=temp,ward = session['wardNum'])


@app.route("/wc/<ward>")
def ward_com(ward):
    if not temp:
        return redirect(url_for('login'))
    else:
        months=['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        res = ['']
        
        
        with sql.connect("mainData.db") as con:
            cur = con.cursor()
            result=cur.execute(
                "SELECT DISTINCT(substr(date, 6, 2)) FROM ComplaintTable WHERE WardNum=(?);",[ward])
            result = result.fetchall()
            print(result)
            for i in result :
                res.append(months[int(i[0])])
                
        con.close()
        print(res)
        date = ['']
        for i in result :
            date.append(f'{randint(1, 28)}/{i[0]}/2020')
        return render_template('wc.html', flag=temp ,date=date[1:],res=res[1:],ward=ward)
@app.route("/mayor")
def mayor():
    if not temp:
        return redirect(url_for('login'))
    else:
        str1 = ''
        arr1 = []
        res = ['']
        with sql.connect("mainData.db") as con:
            cur = con.cursor()
            result=cur.execute(
                "SELECT DISTINCT(WardNum) FROM ComplaintTable;")
            result = result.fetchall()
            print(result)
            for i in result :
                res.append(int(i[0]))
                result2 = cur.execute("SELECT count(*) as k,CompCat FROM ComplaintTable WHERE senval <0 AND WardNum = ? GROUP BY CompCat ORDER BY k DESC LIMIT 1;",[int(i[0])])    
                result2 = result2.fetchall()
                key = result2[0][1]
                key1 = result2[0][0]
                for j in range(0, key1):
                    str1 = str1 + key + " "
                    arr1.append(key)
        wordcloud = WordCloud(width = 800, height = 800,
        background_color ='white',
        min_font_size = 10,collocations=False).generate(str1)
        counts = Counter(arr1)
        max=counts.most_common(20)
        maxNegate = max[0][0]
        print(max,maxNegate)
        print(",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,")
        plt.figure(figsize = (6, 6), facecolor = None)
        plt.imshow(wordcloud,interpolation='bilinear')
        plt.axis("off")
        plt.tight_layout(pad = 0)
        plt.savefig('static/graph1.png')
        con.close()
        return render_template('mayor.html', flag=temp,res=res[1:],max2 = maxNegate)


@app.route("/graph/<month>/<wardNumber>", methods=['POST', 'GET'])
def graph(month, wardNumber):
    if not temp:
        return redirect(url_for('login'))
    else:
        MonthDic = {"January":'01', "February":'02' , "March":'03' , "April":'04', "May":'05', "June": '06',"July":'07', "August":'08', "September":'09', "October":'10', "November":'11', "December":'12'}
        MonthForQuery= MonthDic[month]
        if request.method == 'GET':
            a = []
            k = ''
            with sql.connect("mainData.db") as con:
                cur = con.cursor()
                if (session['userType'] == 'mayor'):
                    result = cur.execute("SELECT CompCat, Count(*) AS freq FROM ComplaintTable WHERE (substr(date, 6, 2))= (?) AND WardNum = (?) GROUP BY CompCat ORDER BY freq DESC LIMIT 8;",(MonthForQuery,wardNumber))
                else:
                    result = cur.execute("SELECT CompCat, Count(*) AS freq FROM ComplaintTable WHERE (substr(date, 6, 2))= (?) AND WardNum = (?) GROUP BY CompCat ORDER BY freq DESC LIMIT 8;",(MonthForQuery, session['wardNum']))
                result = result.fetchall()
                print(MonthForQuery)
                print(result)
                if (session['userType'] == 'mayor'):
                    res1 = cur.execute("SELECT senval,CompCat FROM ComplaintTable WHERE WardNum= (?) AND (substr(date, 6, 2))= (?);",(wardNumber,MonthForQuery))
                else:
                    res1 = cur.execute("SELECT senval,CompCat FROM ComplaintTable WHERE WardNum= (?) AND (substr(date, 6, 2))= (?);",(session['wardNum'],MonthForQuery))
                res1 = res1.fetchall()
                if(res1 != []):

                   
                    for j in res1:
                        senval = j[0]
                        y = j[1]
                        
                        if (senval >= -0.33 and senval < 0):
                            if(y == 'Water Supply'):
                                y = 'Water_Supply'
                            elif(y == 'Stray Animals'):
                                y = 'Stray_Animals'
                            k = k+y+' '
                            a.append(y)
                        elif (senval >= -0.66 and senval < -0.33):
                            
                            if(y == 'Water Supply'):
                                y = 'Water_Supply'
                            elif(y == 'Stray Animals'):
                                y = 'Stray_Animals'
                            k = k+y+' '
                            a.append(y)
                        elif (senval >= -1 and senval < -0.66):
                            
                            if(y == 'Water Supply'):
                                y = 'Water_Supply'
                            elif(y == 'Stray Animals'):
                                y = 'Stray_Animals'
                            k = k+y+' '
                            a.append(y)
            wordcloud = WordCloud(width = 800, height = 800,
            background_color ='white',
            min_font_size = 10,collocations=False).generate(k)
            counts = Counter(a)
            max=counts.most_common(20)
            maxNegate = max[0][0]
            print(max,maxNegate)
            print(",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,")
            plt.figure(figsize = (6, 6), facecolor = None)
            plt.imshow(wordcloud,interpolation='bilinear')
            plt.axis("off")
            plt.tight_layout(pad = 0)
            plt.savefig(os.path.join(
            app.config['UPLOAD_FOLDER']))
            
                
            print('break')
            print(k,a)   
            return render_template('charts.html', flag=temp,result=result,month=month,wardNumber=session['wardNum'],major_prob=maxNegate)
        if request.method == "POST":
            CompCat = request.form['CompCat']
            print(CompCat)
            

            with sql.connect("mainData.db") as con:
                cur = con.cursor()
                result = cur.execute(
                    "SELECT senval,CompCat FROM ComplaintTable WHERE CompCat = (?) AND WardNum= (?) AND (substr(date, 6, 2))= (?) ;", (CompCat,session['wardNum'],MonthForQuery))

                def percentage(part, whole):
                    if(whole != 0):
                        temp = 100 * float(part) / float(whole)
                        return format(temp, '.2f')
                positive = 0
                wpositive = 0
                spositive = 0
                negative = 0
                wnegative = 0
                snegative = 0
                neutral = 0
                result = result.fetchall()
                if(result != []):

                    res = len(result)
                    for j in result:
                        senval = j[0]
                       
                        if (senval == 0):
                            neutral += 1
                        elif (senval > 0 and senval <= 0.33):
                            wpositive += 1
                        elif (senval > 0.33 and senval <= 0.66):
                            positive += 1
                        elif (senval > 0.66 and senval <= 1):
                            spositive += 1
                        elif (senval >= -0.33 and senval < 0):
                            wnegative += 1
                            
                            
                        elif (senval >= -0.66 and senval < -0.33):
                            negative += 1
                            
                        elif (senval >= -1 and senval < -0.66):
                            snegative += 1
                            

                    positive = percentage(positive, res)
                    wpositive = percentage(wpositive, res)
                    spositive = percentage(spositive, res)
                    negative = percentage(negative, res)
                    wnegative = percentage(wnegative, res)
                    snegative = percentage(snegative, res)
                    neutral = percentage(neutral, res)
                    

            li = {"list": [CompCat, positive, wpositive,
                           spositive, negative, wnegative, snegative, neutral]}
            return jsonify(li)

@app.route("/logout")
def logout():
    global temp
    temp = False
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
