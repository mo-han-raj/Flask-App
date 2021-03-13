import requests as req
from requests.exceptions import HTTPError
import pandas as pd
import json
from flask import Flask,render_template,request,url_for
import datetime
from datetime import timedelta
from flask_pymongo import PyMongo
import io
import base64
from pymongo import MongoClient


application = Flask(__name__,template_folder='templates')
application.config['DEBUG'] = True
application.config['MONGO_DBNAME'] = 'Data' # name of database on mongo
application.config["MONGO_URI"] = "mongodb+srv://Admin:mohly000@cluster0.hd4ho.mongodb.net/Data?retryWrites=true&w=majority"
mongo = PyMongo(application)

@application.route('/')
def index():
    return render_template('home.html')

@application.route('/search')
def search():
    return render_template("search.html")

@application.route('/searchresult', methods=['POST','GET'])
def searchresult():
    if request.method=='POST':
        d = request.form['Date']
        date = datetime.datetime.strptime(d, "%Y-%m-%d")
        dfrom = str(date.year)+"-"+str(date.month)+'-'+str(date.day)
        date = date + timedelta(days=1)
        dto = str(date.year)+"-"+str(date.month)+'-'+str(date.day)
        url = 'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={}&endtime={}'
        url = url.format(dfrom,dto)
        try:
            r = req.get(url)
            data = r.json()
            df = pd.DataFrame(data['features'])
            new = pd.DataFrame(list(df['properties']))
            sd = pd.DataFrame(new,columns=['place','mag','time','tsunami','type'])
            sd = sd.dropna()
            sd['country'] = sd['place']
            sd['location'] = sd['place']
            sd['country'] = [i.split(',')[len(i.split(','))-1] for i in sd['country']]
            sd['location'] = [i.split(',')[0] for i in sd['location']]
            sd = sd.drop(columns=['place'],axis=1)
            sd['date'] = sd['time']
            sd['date'] = [datetime.datetime.utcfromtimestamp(i/1000).replace(tzinfo=datetime.timezone.utc).date() for i in sd['date']]
            sd['time'] = [datetime.datetime.utcfromtimestamp(i/1000).replace(tzinfo=datetime.timezone.utc).time().strftime('%H:%M') for i in sd['time']]
            #print(sd.head())
        except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
        except Exception as err:
            print(f'Other error occurred: {err}')
        return render_template('searchresult.html',  tables=[sd.to_html(classes='MyTable')], titles=sd.columns.values)
@application.route('/analytics')
def analytics():
    return render_template("analytics.html")
    
@application.route('/analyticsresult',methods =['GET','POST'])    
def analyticsresult():
    if request.method=='POST':
        y = request.form['year']
        data = mongo.db.seismic.find({'year':y})
        sd = pd.DataFrame(list(data))
        plot1 = io.BytesIO()
        plot2 = io.BytesIO()
        pie = sd.groupby('type').count()
        piechart = pie.plot.pie(y='mag',figsize=(10,5),fontsize=20).get_figure()
        #s1 = 'image/plot1.png'
        #s1path = url_for('static',filename=s1)
        piechart.savefig(plot1, dpi=300,transparent=True,bbox_inches='tight')
        plot1.seek(0)
        a=sd.groupby('country').count().sort_values(by='type',ascending=False)[1:10]
        bar = a.plot.bar(y='type',figsize=(10, 5),fontsize=20).get_figure()
        #s2 = 'image/plot2.png'
        #s2path = url_for('static',filename=s2)
        bar.savefig(plot2, dpi=300,transparent=True,bbox_inches='tight')
        plot2.seek(0)
        plot1_url = base64.b64encode(plot1.getvalue()).decode('utf8')
        plot2_url = base64.b64encode(plot2.getvalue()).decode('utf8')
        return render_template('analyticsresult.html',year=y,p1=plot1_url,p2=plot2_url)
@application.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
   application.run()
    