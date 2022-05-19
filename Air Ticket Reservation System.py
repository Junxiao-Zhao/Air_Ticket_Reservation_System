#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
from flask_session import Session
from dateutil.relativedelta import relativedelta
import pymysql.cursors
from datetime import datetime, date, timedelta
import hashlib

#Initialize the app from Flask
app = Flask(__name__)
app.config['secret_key'] = '123456'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
#Configure MySQL
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db='air_ticket_reservation_system',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

#The welcome page, link to filghtSearch, flightStatus, login, register
@app.route('/')
def hello():
    session['username'] = None
    session['identity'] = None
    return render_template('hello.html')

#The flightSearch page
@app.route('/flightSearch')
def flightSearch():
    return render_template('flightSearch.html', username=session['username'], identity=session['identity'])

#seach flights
@app.route("/searchFlight", methods=['GET', 'POST'])
def searchFlight():
    #grabs information from the forms
    departure = request.form["departure"]
    destination = request.form["destination"]
    date = datetime.strptime(request.form["date"], "%Y-%m-%d")
    
    #cursor used to send queries
    cursor = conn.cursor()
	#executes query
    query = 'SELECT * FROM `flight` WHERE (departure_airport = %s OR departure_airport IN (SELECT airport_name FROM `airport` WHERE airport_city = %s)) AND (arrival_airport = %s OR arrival_airport IN (SELECT airport_name FROM `airport` WHERE airport_city = %s)) AND departure_time BETWEEN %s AND %s'
    cursor.execute(query, (departure, departure, destination, destination, date, date+timedelta(days=1)))
    #stores the results in a variable
    data = cursor.fetchall()
    cursor.close()
    error = None

    #if data is not NULL
    if data:
        return render_template('flightSearch.html', error=error, posts=data, username=session['username'], identity=session['identity'])
    else:
        error = "No Flights Found"
        return render_template('flightSearch.html', error=error, posts=data, username=session['username'], identity=session['identity'])

#book flights
@app.route("/purchaseFlight", methods=['GET', 'POST'])
def purchaseFlight():
    #cursor used to send queries
    cursor = conn.cursor()

    #grabs information from the forms
    air_name = request.form["air_name"]
    f_num = request.form["f_num"]

    if (session['identity']=='customer'):
        email = session['username']
        ba_id = None

    elif (session['identity']=='ba'):
        email = request.form["email"]
        ba_id = session['ba_id']

        #check whether work for this airline
        work = 'SELECT airline_name FROM `booking_agent_work_for` WHERE email = %s'
        cursor.execute(work, (session["username"]))
        company = cursor.fetchall()
        could_buy = False

        for each in company:
            if each['airline_name'] == air_name:
                could_buy = True

        if not could_buy:
            error = 'This Booking Agent does not work for %s!' %air_name
            return render_template('flightSearch.html', error2=error, username=session['username'], identity=session['identity'])


    #get the airplane id and departure time
    get_id = 'SELECT airplane_id, departure_time FROM flight WHERE airline_name = %s AND flight_num = %s'
    cursor.execute(get_id, (air_name, f_num))
    data = cursor.fetchone()
    air_id = data['airplane_id']
    depart_time = data['departure_time']
    #ckeck the departure time
    if depart_time < datetime.now():
        cursor.close()
        error = 'The flight has finished!'
        return render_template('flightSearch.html', error2=error, username=session['username'], identity=session['identity'])

    #get the number of already booked seats
    booked = 'SELECT COUNT(*) FROM ticket WHERE airline_name = %s AND flight_num = %s'
    cursor.execute(booked, (air_name, f_num))
    booked_num = cursor.fetchone()['COUNT(*)']

    #get the seats number of that airplace
    seats = 'SELECT seats FROM airplane WHERE airplane_id = %s'
    cursor.execute(seats, (air_id))
    seat_num = cursor.fetchone()['seats']
    
    #if there's no seats left
    if not (booked_num - seat_num):
        cursor.close()
        error = "No tickets left! Please choose another flight!"
        return render_template('flightSearch.html', error2=error, username=session['username'], identity=session['identity'])
    
    #purchase the ticket
    else:
        #get the maximum ticket id
        get_max = 'SELECT MAX(ticket_id) AS max FROM `ticket`'
        cursor.execute(get_max)
        try:
            ticket_id = int(cursor.fetchone()['max']) + 1
        except:
            ticket_id = 1
        #insert a new ticket
        ticket = 'INSERT INTO `ticket` VALUES(%s,%s,%s)'
        cursor.execute(ticket, (ticket_id, air_name, f_num))
        purchase = 'INSERT INTO `purchases` VALUES(%s,%s,%s,%s)'
        cursor.execute(purchase, (ticket_id, email, ba_id, datetime.date(datetime.now())))
        conn.commit()
        cursor.close()
        return render_template('flightSearch.html', status='success', username=session['username'], identity=session['identity'])

#get the upcoming flights
def upcoming(ID):
    #cursor used to send queries
    cursor = conn.cursor()

    if (ID=='customer'):
        info = session['username']
        query = 'SELECT ticket_id, F.* FROM `flight` AS F NATURAL JOIN `ticket` NATURAL JOIN `purchases` WHERE customer_email = %s AND F.departure_time > %s'

    elif (ID=='ba'):
        info = session['ba_id']
        query = 'SELECT ticket_id, F.* FROM `flight` AS F NATURAL JOIN `ticket` NATURAL JOIN `purchases` WHERE booking_agent_id = %s AND booking_agent_id IS NOT NULL AND F.departure_time > %s'

    cursor.execute(query, (info, date.today()))
    data = cursor.fetchall()
    cursor.close()

    return data

#Refund
@app.route('/refund')
def refund():
    post = upcoming(session['identity'])
    return render_template('refund.html', posts=post)

#Refund Flights
@app.route('/refundFlight', methods=['GET', 'POST'])
def refundFlight():
    #grabs information from the forms
    ticket_id = request.form['ticket_id']

    #cursor used to send queries
    cursor = conn.cursor()

    #delete purchases
    del_pur = 'DELETE FROM `purchases` WHERE ticket_id = %s'
    cursor.execute(del_pur,(ticket_id))
    conn.commit()
    #delete ticket
    del_ticket = 'DELETE FROM `ticket` WHERE ticket_id = %s'
    cursor.execute(del_ticket,(ticket_id))
    conn.commit()
    cursor.close()

    post = upcoming(session['identity'])
    return render_template('refund.html', posts=post, status="success")

#The flightStatus page
@app.route("/flightStatus")
def flightStatus():
    return render_template('flightStatus.html', username=session['username'])

#search status
@app.route("/searchStatus", methods=['GET', 'POST'])
def searchStatus():
    #grabs information from the forms
    flight_num = request.form["flight_num"]
    date = datetime.strptime(request.form["date"], "%Y-%m-%d")

    #cursor used to send queries
    cursor = conn.cursor()
	#search the flights
    query = 'SELECT * FROM `flight` WHERE flight_num = %s AND ((departure_time BETWEEN %s AND %s) OR (arrival_time BETWEEN %s AND %s))'
    cursor.execute(query, (flight_num, date, date+timedelta(days=1), date, date+timedelta(days=1)))
    data = cursor.fetchall()
    cursor.close()
    error = None

    #if data is not NULL
    if data:
        return render_template('flightStatus.html', error=error, posts=data, username=session['username'])
    else:
        error = "Flights Not Found"
        return render_template('flightStatus.html', error=error, posts=data, username=session['username'])

#Display the upcoming flights
@app.route("/flightView")
def flightView():
    #cursor used to send queries
    cursor = conn.cursor()

    #search the upcoming flights
    if (session['identity']=='customer'):
        query = 'SELECT P.customer_email AS username, F.* FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE customer_email = %s AND F.departure_time > %s ORDER BY F.departure_time ASC'
        cursor.execute(query, (session['username'], datetime.now()))

    elif (session['identity']=='ba'):
        query = 'SELECT P.customer_email AS username, F.* FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE P.booking_agent_id = %s AND P.booking_agent_id IS NOT NULL AND F.departure_time > %s ORDER BY F.departure_time ASC'
        cursor.execute(query, (session['ba_id'], datetime.now()))
    
    else:
        query = 'SELECT * FROM `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND departure_time BETWEEN %s AND %s ORDER BY departure_time ASC'
        cursor.execute(query, (session['username'], datetime.now(), datetime.now()+timedelta(days=30)))

    data = cursor.fetchall()
    cursor.close()

    return render_template('flightView.html', type="Upcoming Flights", posts=data)

#Display the Flights in the specified range
@app.route("/viewFlight", methods=['GET', 'POST'])
def viewFlight():
    #grabs information from the forms
    start = request.form["from"]
    to = request.form["to"]
    
    #check the dates
    if start > to:
        return render_template('flightView.html', type="View My Flights", error='The start date should be prior to the end date!')

    #cursor used to send queries
    cursor = conn.cursor()

    #search my flights in the date range
    if (session['identity']=='customer'):
        query = 'SELECT P.customer_email AS username, F.* FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE customer_email = %s AND F.departure_time BETWEEN %s AND %s ORDER BY F.departure_time ASC'
        cursor.execute(query, (session['username'], start, datetime.strptime(to, "%Y-%m-%d")+timedelta(days=1)))
    
    elif (session['identity']=='ba'):
        query = 'SELECT P.customer_email AS username, F.* FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE P.booking_agent_id = %s AND P.booking_agent_id IS NOT NULL AND F.departure_time BETWEEN %s AND %s ORDER BY F.departure_time ASC'
        cursor.execute(query, (session['ba_id'], start, datetime.strptime(to, "%Y-%m-%d")+timedelta(days=1)))

    else:
        query = 'SELECT * FROM `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND departure_time BETWEEN %s AND %s ORDER BY departure_time ASC'
        cursor.execute(query, (session['username'], start, datetime.strptime(to, "%Y-%m-%d")+timedelta(days=1)))

    data = cursor.fetchall()
    cursor.close()

    title = "From %s to %s" %(start, to)
    return render_template('flightView.html', type=title, posts=data)

#Display the commission in the past 30 days
@app.route("/commission")
def commission():
    #cursor used to send queries
    cursor = conn.cursor()

    #default retrieve the commission in the past 30 days
    query = 'SELECT SUM(price*0.1) AS sum, AVG(price*0.1) as avg, COUNT(price) as num FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE P.booking_agent_id = %s AND P.booking_agent_id IS NOT NULL AND P.purchase_date BETWEEN %s AND %s'
    cursor.execute(query, (session['ba_id'], datetime.now()-timedelta(days=30), datetime.now()))
    data = cursor.fetchone()
    cursor.close()

    if data['sum'] is None:
        data['sum'] = 0
        data['avg'] = 0

    m = "In the past 30 days, total commission: %.2f, average commission: %.2f, and total number of tickets sold: %d" %(data['sum'], data['avg'], data['num'])
    return render_template('commission.html', message=m)

#Display the commission in the specified range
@app.route("/viewCommission", methods=['GET', 'POST'])
def viewCommission():
    #grabs information from the forms
    start = request.form["from"]
    to = request.form["to"]

    #cursor used to send queries
    cursor = conn.cursor()

    #retrieve the commission in the specified range
    query = 'SELECT SUM(price*0.1) AS sum, AVG(price*0.1) as avg, COUNT(price) as num FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE P.booking_agent_id = %s AND P.booking_agent_id IS NOT NULL AND P.purchase_date BETWEEN %s AND %s'
    cursor.execute(query, (session['ba_id'], start, to))
    data = cursor.fetchone()
    cursor.close()

    m = "From %s to %s, total commission: %.2f, average commission: %.2f, and total number of tickets sold: %d" %(start, to, data['sum'], data['avg'], data['num'])
    return render_template('commission.html', message=m)

#Top 5 customers based on number of tickets bought from the booking agent in the past 6 months
@app.route("/topCustomerT")
def topCustomerT():
    #cursor used to send queries
    cursor = conn.cursor()
    
    #retrieve the customers based on number of tickets bought from the booking agent in the past 6 months
    query = 'SELECT customer_email, COUNT(customer_email) AS num FROM `purchases` WHERE booking_agent_id = %s AND booking_agent_id IS NOT NULL AND purchase_date BETWEEN %s AND %s GROUP BY customer_email ORDER BY COUNT(customer_email) DESC'
    cursor.execute(query, (session['ba_id'], datetime.strftime(date.today()-relativedelta(months=5),"%Y-%m-01"), date.today()))
    data = cursor.fetchall()
    cursor.close()

    email_list = []
    num = []
    for each in data:
        email_list.append(each['customer_email'])
        num.append(str(each['num']))

    data_x = ",".join(email_list[:5])
    data_y = ",".join(num[:5])
    m = "The top 5 customers who bought most tickets in the last 6 months"

    return render_template('topCustomerT.html', x=data_x, y=data_y, message=m)

#Top 5 customers based on number of tickets bought from the booking agent in the specified range
@app.route("/topT", methods=['GET', 'POST'])
def topT():
    #grabs information from the forms
    start = request.form["from"]
    to = request.form["to"]

    #cursor used to send queries
    cursor = conn.cursor()
    
    #retrieve the customers based on number of tickets bought from the booking agent in the past 6 months
    query = 'SELECT customer_email, COUNT(customer_email) AS num FROM `purchases` WHERE booking_agent_id = %s AND booking_agent_id IS NOT NULL AND purchase_date BETWEEN %s AND %s GROUP BY customer_email ORDER BY COUNT(customer_email) DESC'
    cursor.execute(query, (session['ba_id'], start, to))
    data = cursor.fetchall()
    cursor.close()

    email_list = []
    num = []
    for each in data:
        email_list.append(each['customer_email'])
        num.append(str(each['num']))

    data_x = ",".join(email_list[:5])
    data_y = ",".join(num[:5])
    m = "The top 5 customers who bought most tickets in the range from %s to %s" %(start, to)

    return render_template('topCustomerT.html', x=data_x, y=data_y, message=m)

#Top 5 customers based on amount of commission received in the last year
@app.route("/topCustomerC")
def topCustomerC():
    #cursor used to send queries
    cursor = conn.cursor()
    
    #retrieve the customers based on amount of commission received in the last year
    query = 'SELECT customer_email, SUM(price*0.1) AS sum FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE P.booking_agent_id = %s AND P.booking_agent_id IS NOT NULL AND P.purchase_date BETWEEN %s AND %s GROUP BY customer_email ORDER BY sum DESC'
    cursor.execute(query, (session['ba_id'], datetime.strftime(date.today()-relativedelta(months=11),"%Y-%m-01"), date.today()))
    data = cursor.fetchall()
    cursor.close()

    email_list = []
    num = []
    for each in data:
        email_list.append(each['customer_email'])
        num.append(str(each['sum']))

    data_x = ",".join(email_list[:5])
    data_y = ",".join(num[:5])
    m = "The top 5 customers who contributed the most commission in the last year"

    return render_template('topCustomerC.html', x=data_x, y=data_y, message=m)

#Top 5 customers based on amount of commission receivedt in the specified range
@app.route("/topC", methods=['GET', 'POST'])
def topC():
    #grabs information from the forms
    start = request.form["from"]
    to = request.form["to"]

    #cursor used to send queries
    cursor = conn.cursor()
    
    #retrieve the customers based on amount of commission received in the specified range
    query = 'SELECT customer_email, SUM(price*0.1) AS sum FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE P.booking_agent_id = %s AND P.booking_agent_id IS NOT NULL AND P.purchase_date BETWEEN %s AND %s GROUP BY customer_email ORDER BY sum DESC'
    cursor.execute(query, (session['ba_id'], start, to))
    data = cursor.fetchall()
    cursor.close()

    email_list = []
    num = []
    for each in data:
        email_list.append(each['customer_email'])
        num.append(str(each['sum']))

    data_x = ",".join(email_list[:5])
    data_y = ",".join(num[:5])
    m = "The top 5 customers who who contributed the most commission in the range from %s to %s" %(start, to)

    return render_template('topCustomerT.html', x=data_x, y=data_y, message=m)

#Track my spending
@app.route("/spendingTrack")
def spendingTrack():
    username = session['username']

    #cursor used to send queries
    cursor = conn.cursor()

    #default retrieve the spending of the past year
    query = 'SELECT SUM(F.price) AS Amount, DATE_FORMAT(purchase_date, "%%Y-%%m") AS Month FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE customer_email = %s AND P.purchase_date BETWEEN %s AND %s GROUP BY DATE_FORMAT(purchase_date, "%%Y%%m")'
    cursor.execute(query, (username, datetime.strftime(date.today()-relativedelta(months=11),"%Y-%m-01"), date.today()))
    data = cursor.fetchall()
    cursor.close()

    #calculate the total spending and the last six months spending
    month = [(date.today()-relativedelta(months=i)).strftime("%Y-%m") for i in range(11,-1,-1)]
    amount = dict(zip(month,['0']*12))

    total = 0
    for each in data:
        total += each["Amount"]
        amount.update({str(each["Month"]):str(each["Amount"])})
    
    data_x = ','.join(list(amount.keys())[5:-1])
    data_y = ','.join(list(amount.values())[5:-1])

    return render_template('/spendingTrack.html', name=username, range='in the past year', x=data_x, y=data_y, money=total)

#Track my spending in the specified range
@app.route("/trackSpending", methods=['GET', 'POST'])
def trackSpending():
    username = session['username']
    #grabs information from the forms
    start = request.form["from"]
    to = request.form["to"]

    #cursor used to send queries
    cursor = conn.cursor()
    #retrieve the spending of in the specified range
    query = 'SELECT SUM(F.price) AS Amount, DATE_FORMAT(purchase_date, "%%Y-%%m") AS Month FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE customer_email = %s AND P.purchase_date BETWEEN %s AND %s GROUP BY DATE_FORMAT(purchase_date, "%%Y%%m")'
    cursor.execute(query, (username, start, to))
    data = cursor.fetchall()
    cursor.close()

    #calculate the total spending and the last six months spending
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(to, "%Y-%m-%d")
    num_month = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1

    month = [(datetime.strptime(start, "%Y-%m-%d")+relativedelta(months=i)).strftime("%Y-%m") for i in range(num_month)]
    amount = dict(zip(month,['0']*num_month))

    total = 0
    for each in data:
        total += each["Amount"]
        amount.update({str(each["Month"]):str(each["Amount"])})
    
    data_x = ','.join(amount.keys())
    data_y = ','.join(amount.values())
    Range = "from %s to %s" %(start, to)

    return render_template('/spendingTrack.html', name=username, range=Range, x=data_x, y=data_y, money=total)

#search the upcoming fligths in next 30 days
def upcoming_30():
    #cursor used to send queries
    cursor = conn.cursor()
    #retrieve the upcoming fligths in next 30 days
    query = 'SELECT * FROM `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND departure_time BETWEEN %s AND %s ORDER BY departure_time ASC'
    cursor.execute(query, (session['username'], datetime.today(), datetime.today()+timedelta(days=30)))
    upcoming = cursor.fetchall()
    cursor.close()

    return upcoming

#permission check
def check_permission(permission_type):
    #cursor used to send queries
    cursor = conn.cursor()

    #check whether the staff has the permission specified
    check = 'SELECT permission_type FROM `permission` WHERE username = %s'
    cursor.execute(check, (session['username']))
    data = cursor.fetchall()
    cursor.close()

    have_permission = False
    for each in data:
        have_permission = have_permission | (each['permission_type'] == permission_type)
    
    return have_permission

#Check the permission before create new flights
@app.route("/flightCreate")
def flightCreate():
    #check the permission
    have_permission = check_permission("Admin")
    
    #if don't have the permission, return error
    if not have_permission:
        error = 'Sorry, you do not have the permission to create new flights!'
        return render_template('flightCreate.html', error=error)
    #else default return the upcoming flights in the next 30 days'
    
    else:
        #cursor used to send queries
        cursor = conn.cursor()

        #get all the airports
        query = 'SELECT airport_name FROM `airport`'
        cursor.execute(query)
        data = cursor.fetchall()

        #get all the airplane ids of this airline
        ids = 'SELECT airplane_id FROM `airplane` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s)'
        cursor.execute(ids, (session['username']))
        air_ids = cursor.fetchall()
        cursor.close()

        session['airports'] = data
        session['air_ids'] = air_ids
        upcoming = upcoming_30()
        return render_template('flightCreate.html', posts=upcoming, airports=data, airplane_ids=air_ids)

#Create new flights
@app.route('/createFlight', methods=['GET', 'POST'])
def createFlight():
    #grabs information from the forms
    f_num = request.form["f_num"]
    departure = request.form["departure"]
    destination = request.form["destination"]
    #check the date format
    upcoming = upcoming_30()
    try:
        d_date = datetime.strptime(request.form["d_date"], '%Y-%m-%d %H:%M:%S')
        a_date = datetime.strptime(request.form["a_date"], '%Y-%m-%d %H:%M:%S')
    except:
        return render_template('flightCreate.html', posts=upcoming, error2='Please enter the correct datetime in the format: yyyy-mm-dd HH:MM:SS', airports=session['airports'], airplane_ids=session['air_ids'])

    #check price is positive
    price = float(request.form["price"])
    if price < 0:
        return render_template('flightCreate.html', posts=upcoming, error2='Price should not be negative!', airports=session['airports'], airplane_ids=session['air_ids'])

    status = request.form["status"]
    air_id = request.form["air_id"]

    #cursor used to send queries
    cursor = conn.cursor()

    try:
        #insert into `flight`
        create = 'INSERT INTO `flight` VALUES((SELECT airline_name FROM `airline_staff` WHERE username = %s),%s,%s,%s,%s,%s,%s,%s,%s)'
        cursor.execute(create,(session['username'],f_num,departure,d_date,destination,a_date,price,status,air_id))
        conn.commit()
        cursor.close()
    except:
        cursor.close()
        return render_template('flightCreate.html', posts=upcoming, error2='The flight number has already existed!', airports=session['airports'], airplane_ids=session['air_ids'])

    upcoming = upcoming_30()
    return render_template('flightCreate.html', posts=upcoming, status="success", airports=session['airports'], airplane_ids=session['air_ids'])

#Status Change
@app.route('/statusChange')
def statusChange():
    #check the permission
    have_permission = check_permission('Operator')

    #if don't have the permission, return error
    if not have_permission:
        error = "Sorry, you do not have the permission to change flights' status!"
        return render_template('statusChange.html', error=error)
    #else return the flight numbers
    else:
        #cursor used to send queries
        cursor = conn.cursor()

        #select all the flight numbers
        query = 'SELECT flight_num FROM `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s)'
        cursor.execute(query, (session['username']))
        data = cursor.fetchall()
        cursor.close()
        session['flight_num'] = data
        return render_template('statusChange.html', f_num=data)

#Change status
@app.route('/changeStatus', methods=['GET', 'POST'])
def changeStatus():
    #grabs information from the forms
    f_num = request.form['f_num']
    status = request.form["status"]

    #cursor used to send queries
    cursor = conn.cursor()

    #update status
    update = 'UPDATE `flight` SET status = %s WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND flight_num = %s'
    cursor.execute(update,(status, session['username'],f_num))
    conn.commit()
    cursor.close()

    return render_template('statusChange.html', f_num=session['flight_num'], status='success')

#Airplane Add
@app.route('/airplaneAdd')
def airplaneAdd():
    #check the permission
    have_permission = check_permission("Admin")

    #if don't have the permission, return error
    if not have_permission:
        error = "Sorry, you do not have the permission to add new airplanes!"
        return render_template('airplaneAdd.html', error=error)
    #else continue to add new airplanes
    else:
        #cursor used to send queries
        cursor = conn.cursor()

        #get all the airplanes
        query = 'SELECT * FROM `airplane` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s)'
        cursor.execute(query, (session['username']))
        data = cursor.fetchall()
        session['airplanes'] = data
        cursor.close()

        return render_template('airplaneAdd.html', posts=data)

#Add airplanes
@app.route('/addAirplane', methods=['GET', 'POST'])
def addAirplane():
    #grabs information from the forms
    air_id = request.form['air_id']
    seat_num = request.form["seats"]

    try:
        #cursor used to send queries
        cursor = conn.cursor()

        #insert new airplane
        query = 'INSERT INTO `airplane` VALUES((SELECT airline_name FROM `airline_staff` WHERE username = %s),%s,%s)'
        cursor.execute(query, (session['username'],air_id,seat_num))
        conn.commit()
    
    #return error if the airplane id has already existed
    except:
        cursor.close()
        return render_template('airplaneAdd.html', error2="The airplane id has already existed!", posts=session['airplanes'])
        
    #if not, return all the airplanes
    info = 'SELECT * FROM `airplane` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s)'
    cursor.execute(info,(session['username']))
    data = cursor.fetchall()
    cursor.close()

    return render_template('airplaneAdd.html', posts=data, status='success')

#Airport Add
@app.route('/airportAdd')
def airportAdd():
    #check the permission
    have_permission = check_permission("Admin")

    #if don't have the permission, return error
    if not have_permission:
        error = "Sorry, you do not have the permission to add new airports!"
        return render_template('airportAdd.html', error=error)
    #else continue to add new airports
    else:
        return render_template('airportAdd.html')

#Add airports
@app.route('/addAirport', methods=['GET', 'POST'])
def addAirport():
    #grabs information from the forms
    name = request.form['airport_name']
    city = request.form["airport_city"]

    try:
        #cursor used to send queries
        cursor = conn.cursor()

        #insert new airport
        query = 'INSERT INTO `airport` VALUES(%s,%s)'
        cursor.execute(query, (name,city))
        conn.commit()
        cursor.close()
    
    #return error if the airport name has already existed
    except:
        return render_template('airportAdd.html', error2="This airport has already existed!")

    return render_template('airportAdd.html', status='success')

#Top 5 booking agents based on number of tickets sold in the past month
@app.route("/topBA")
def topBAT():
    #cursor used to send queries
    cursor = conn.cursor()
    
    #retrieve the booking agents based on number of tickets sold
    query = 'SELECT email, COUNT(email) AS num FROM `booking_agent_work_for` NATURAL JOIN `booking_agent` NATURAL JOIN `purchases` NATURAL JOIN `ticket` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s GROUP BY email ORDER BY COUNT(email) DESC'
    #in the past month
    cursor.execute(query, (session['username'], date.today()-relativedelta(months=1), date.today()))
    past_month = cursor.fetchall()[:5]
    #in the past year
    cursor.execute(query, (session['username'], date.today()-relativedelta(years=1), date.today()))
    past_year = cursor.fetchall()[:5]

    #retrieve the booking agents based on amount of commission received for the last year
    query2 = 'SELECT email, SUM(price*0.1) as amount FROM `booking_agent_work_for` NATURAL JOIN `booking_agent` NATURAL JOIN `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s GROUP BY email ORDER BY amount DESC'
    cursor.execute(query2, (session['username'], datetime.strftime(date.today()-relativedelta(years=1), "%Y-01-01"), datetime.strftime(date.today()-relativedelta(years=1), "%Y-12-31")))
    com = cursor.fetchall()[:5]
    cursor.close()

    return render_template('topBA.html', past_monthT=past_month, past_yearT=past_year, com=com)

#view the flights of the most frequent customer
@app.route('/topCust')
def topCust():
    #cursor used to send queries
    cursor = conn.cursor()

    #select the most frequent customer(s) in the last year
    f = 'WITH freq AS (SELECT customer_email, COUNT(customer_email) AS num FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND departure_time BETWEEN %s AND %s GROUP BY customer_email) SELECT customer_email FROM freq WHERE num = (SELECT MAX(num) FROM freq)'
    cursor.execute(f, (session['username'], datetime.strftime(date.today()-relativedelta(years=1), "%Y-01-01"), datetime.strftime(date.today()-relativedelta(years=1), "%Y-12-31")))
    data = cursor.fetchall()

    #select all the customers who took this airline's flight
    query = 'SELECT DISTINCT customer_email FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND departure_time BETWEEN %s AND %s' 
    cursor.execute(query, (session['username'], datetime.strftime(date.today()-relativedelta(years=1), "%Y-01-01"), datetime.strftime(date.today()-relativedelta(years=1), "%Y-12-31")))
    emails = cursor.fetchall()
    cursor.close()

    freq = []
    for each in data:
        freq.append(each['customer_email'])
    freq = ",".join(freq)

    m = 'The most frequent customer(s) in the past year: %s' %freq
    session['c_emails'] = emails

    return render_template('topCust.html', type=m, lists=emails)

#search the taken flights for the specified customer
@app.route('/custTop', methods=['GET', 'POST'])
def custFlight():
    #grabs information from the forms
    c_email = request.form['c_email']

    #cursor used to send queries
    cursor = conn.cursor()

    #select all the flights the cutomer took
    query = 'SELECT * FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND customer_email = %s AND departure_time < %s'
    cursor.execute(query, (session['username'], c_email, datetime.today()))
    data = cursor.fetchall()
    cursor.close()

    m = '%s has taken the following flights:' %c_email

    return render_template('topCust.html', type=m, lists=session['c_emails'], posts=data)

#get the last date of last month
def month_last_date():
    month_last_day = (date.today()-relativedelta(months=1)).replace(day=28) + timedelta(days=4)
    return month_last_day - timedelta(days=month_last_day.day)

#Comparison of Revenue earned in the last year
@app.route('/compRY')
def compareRevenueY():
    #cursor used to send queries
    cursor = conn.cursor()

    #retrieve the direct sales
    direct = 'SELECT SUM(price) AS sum FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s AND booking_agent_id IS NULL'
    #retrieve the indirect sales
    indirect = 'SELECT SUM(price) AS sum FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s AND booking_agent_id IS NOT NULL'

    #direct
    cursor.execute(direct, (session['username'], datetime.strftime(date.today()-relativedelta(years=1), "%Y-01-01"), datetime.strftime(date.today()-relativedelta(years=1), "%Y-12-31")))
    data_d = cursor.fetchone()['sum']
    if not data_d:
        data_d = 0
    else:
        data_d = float(data_d)
    #indirect
    cursor.execute(indirect, (session['username'], datetime.strftime(date.today()-relativedelta(years=1), "%Y-01-01"), datetime.strftime(date.today()-relativedelta(years=1), "%Y-12-31")))
    data_in = cursor.fetchone()['sum']
    if not data_in:
        data_in = 0
    else:
        data_in = float(data_in)
    cursor.close()

    #check if no ticket sold
    m = None
    x = None
    y = None
    try:
        #calculate the percentage
        x = data_d/(data_d+data_in)
        y = data_in/(data_d+data_in)
    except:
        m = 'No Ticket sold in the last year!'

    return render_template('compR.html', x=x, y=y, time='year', error=m)

#Comparison of Revenue earned in the last month
@app.route('/compRM')
def compareRevenueM():
    #cursor used to send queries
    cursor = conn.cursor()

    #retrieve the direct sales
    direct = 'SELECT SUM(price) AS sum FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s AND booking_agent_id IS NULL'
    #retrieve the indirect sales
    indirect = 'SELECT SUM(price) AS sum FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s AND booking_agent_id IS NOT NULL'

    month_last_day = month_last_date()
    #direct
    cursor.execute(direct, (session['username'], datetime.strftime(date.today()-relativedelta(months=1), "%Y-%m-01"), month_last_day))
    data_d = cursor.fetchone()['sum']
    if not data_d:
        data_d = 0
    else:
        data_d = float(data_d)
    #indirect
    cursor.execute(indirect, (session['username'], datetime.strftime(date.today()-relativedelta(months=1), "%Y-%m-01"), month_last_day))
    data_in = cursor.fetchone()['sum']
    if not data_in:
        data_in = 0
    else:
        data_in = float(data_in)
    cursor.close()

    #check if no ticket sold
    m = None
    x = None
    y = None
    try:
        #calculate the percentage
        x = data_d/(data_d+data_in)
        y = data_in/(data_d+data_in)
    except:
        m = 'No Ticket sold in the last month!'

    return render_template('compR.html', x=x, y=y, time='month', error=m)

#Top 3 destinations
@app.route('/topDest')
def topDest():
    #cursor used to send queries
    cursor = conn.cursor()

    #select the top 3 destinations for last 3 months and last year
    query = 'SELECT arrival_airport, COUNT(arrival_airport) AS num FROM `purchases` NATURAL JOIN `flight` NATURAL JOIN `ticket` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND arrival_time BETWEEN %s AND %s GROUP BY arrival_airport ORDER BY num DESC'
    #last 3 months
    month_last_day = month_last_date()
    cursor.execute(query, (session['username'], datetime.strftime(date.today()-relativedelta(months=3), "%Y-%m-01"), datetime.strftime(date.today(), "%Y-%m-01")))
    data_m = cursor.fetchall()

    top_m  = []
    for each in data_m:
        top_m.append(each['arrival_airport'])
    top_m = ",".join(top_m[:3])

    #last year
    cursor.execute(query, (session['username'], datetime.strftime(date.today()-relativedelta(years=1), "%Y-01-01"), datetime.strftime(date.today()-relativedelta(years=1), "%Y-12-31")))
    data_y = cursor.fetchall()
    cursor.close()

    top_y = []
    for each in data_y:
        top_y.append(each['arrival_airport'])
    top_y = ", ".join(top_y[:3])

    return render_template('topDest.html', last_m=top_m, last_y=top_y)

#View Report
@app.route('/reportView')
def viewReport(): 
    #cursor used to send queries
    cursor = conn.cursor()

    #select the amount of tickets sold in the last month
    count_m = 'SELECT COUNT(ticket_id) AS num FROM `ticket` NATURAL JOIN `purchases` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s'
    #calculate the last day of last month
    month_last_day = month_last_date()
    #the amount of tickets sold in the last month
    cursor.execute(count_m, (session['username'], datetime.strftime(date.today()-relativedelta(months=1), "%Y-%m-01"), month_last_day))
    last_m = cursor.fetchone()['num']

    #select the amount of tickets sold in the last year -- month wise
    count_y = 'SELECT COUNT(ticket_id) AS num, DATE_FORMAT(purchase_date, "%%Y-%%m") AS Month FROM `ticket` NATURAL JOIN `purchases` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s GROUP BY DATE_FORMAT(purchase_date, "%%Y%%m")'
    cursor.execute(count_y, (session['username'], datetime.strftime(date.today()-relativedelta(years=1), "%Y-01-01"), datetime.strftime(date.today()-relativedelta(years=1), "%Y-12-31")))
    last_y = cursor.fetchall()

    month = [(date(date.today().year-1,1,1)+relativedelta(months=i)).strftime("%Y-%m") for i in range(12)]
    amount = dict(zip(month,['0']*12))

    total = 0
    for each in last_y:
        total += each["num"]
        amount.update({str(each["Month"]):str(each["num"])})
    
    data_x = ','.join(amount.keys())
    data_y = ','.join(amount.values())

    return render_template('reportView.html', x=data_x, y=data_y, t_m=last_m, t_y=total)

#View Report in the specified range
@app.route('/trackTickets', methods=['GET', 'POST'])
def trackTickets():
    #grabs information from the forms
    start = request.form['from']
    to = request.form['to']

    #cursor used to send queries
    cursor = conn.cursor()

    #select the amount of tickets sold in the specified range -- month wise
    count = 'SELECT COUNT(ticket_id) AS num, DATE_FORMAT(purchase_date, "%%Y-%%m") AS Month FROM `ticket` NATURAL JOIN `purchases` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s GROUP BY DATE_FORMAT(purchase_date, "%%Y%%m")'
    cursor.execute(count, (session['username'], start, to))
    data = cursor.fetchall()

    #calculate the total months in the specified range
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(to, "%Y-%m-%d")
    num_month = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1

    month = [(datetime.strptime(start, "%Y-%m-%d")+relativedelta(months=i)).strftime("%Y-%m") for i in range(num_month)]
    amount = dict(zip(month,['0']*num_month))

    total = 0
    for each in data:
        total += each["num"]
        amount.update({str(each["Month"]):str(each["num"])})
    
    data_x = ','.join(amount.keys())
    data_y = ','.join(amount.values())

    m = 'from %s to %s' %(start, to)

    return render_template('reportView.html', x=data_x, y=data_y, specified='True', message=m)

#Permission grant
@app.route('/permissionGrant')
def permissionGrant():
    #check the permission
    have_permission = check_permission('Admin')

    #if don't have the permission, return error
    if not have_permission:
        error = "Sorry, you do not have the permission to grant new permissions!"
        return render_template('permissionGrant.html', error=error)
    #else return the flight numbers
    else:
        #cursor used to send queries
        cursor = conn.cursor()

        #select all the staffs' usernames
        query = 'SELECT username FROM `airline_staff` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s)'
        cursor.execute(query, (session['username']))
        data = cursor.fetchall()
        cursor.close()
        session['staff_names'] = data

        return render_template('permissionGrant.html', names=data)

#Change status
@app.route('/grantPermission', methods=['GET', 'POST'])
def grantPermission():
    #grabs information from the forms
    name = request.form['username']
    permission = request.form["permission"]

    #cursor used to send queries
    cursor = conn.cursor()

    try:
        #insert the permission
        query = 'INSERT INTO `permission` VALUES (%s,%s)'
        cursor.execute(query,(name,permission))
        conn.commit()
        cursor.close()
    
    #return error if the staff has already had this permission
    except:
        return render_template('permissionGrant.html', names=session['staff_names'], error2='The staff has already had this permission!')

    return render_template('permissionGrant.html', names=session['staff_names'], status='success')

#Booking agent Add
@app.route('/baAdd')
def baAdd():
    #check the permission
    have_permission = check_permission("Admin")

    #if don't have the permission, return error
    if not have_permission:
        error = "Sorry, you do not have the permission to add booking agents!"
        return render_template('baAdd.html', error=error)
    #else continue to add new booking agents
    else:
        #cursor used to send queries
        cursor = conn.cursor()

        #get all the booking agents work for this company
        query = 'SELECT * FROM `booking_agent_work_for` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s)'
        cursor.execute(query, session['username'])
        data = cursor.fetchall()
        session['ba_emails'] = data
        cursor.close()

        return render_template('baAdd.html', posts=data)

#Add booking agents
@app.route('/addBA', methods=['GET', 'POST'])
def addBA():
    #grabs information from the forms
    email = request.form['email']

    try:
        #cursor used to send queries
        cursor = conn.cursor()

        #add booking agents
        query = 'INSERT INTO `booking_agent_work_for` VALUES(%s,(SELECT airline_name FROM `airline_staff` WHERE username = %s))'
        cursor.execute(query, (email,session['username']))
        conn.commit()
        cursor.close()
    
    #return error if the booking agent has already been added or does not exist
    except:
        return render_template('baAdd.html', error2="This booking agent has already been added or does not exist!", posts=session['ba_emails'])

    #cursor used to send queries
    cursor = conn.cursor()

    #get all the booking agents work for this company
    query = 'SELECT * FROM `booking_agent_work_for` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s)'
    cursor.execute(query, session['username'])
    data = cursor.fetchall()
    cursor.close()

    return render_template('baAdd.html', status='success', posts=data)

#The register page for customer
@app.route('/customerRegister')
def cusRegister():
	return render_template('/registerCustomer.html')

#register for Customer
@app.route('/registerCustomer', methods=['GET', 'POST'])
def registerCustomer():
    #grabs information from the forms
    Email = request.form["email"]
    name = request.form["name"]
    password = hashlib.md5(request.form["password"].encode(encoding='UTF-8')).hexdigest()
    building_num = request.form["building_num"]
    street = request.form["street"]
    city = request.form["city"]
    state = request.form["state"]
    phone_num = request.form["phone_num"]
    passport_num = request.form["passport_num"]
    passport_expir = datetime.strptime(request.form["passport_expir"], "%Y-%m-%d")
    country = request.form["country"]
    birth = datetime.strptime(request.form["birth"], "%Y-%m-%d")

    error = False

    #check the birthdate and the passport expiration date
    if datetime.now() > passport_expir:
        error = "Your passport has expired! Please enter a vaild passort!"
    elif datetime.now() < birth:
        error = "Please enter the valid birth date!"   
    
    if error:
        return render_template('/registerCustomer.html', error=error)
    else:
        #cursor used to send queries
        cursor = conn.cursor()
        try:
            ins = 'INSERT INTO `customer` VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
            cursor.execute(ins,(Email, name, password, building_num, street, city, state, phone_num, passport_num, passport_expir, country, birth))
            conn.commit()
            cursor.close()
            return render_template('/hello.html')
        except:
            error = "The email address has already been used!"
            return render_template('/registerCustomer.html', error=error)

#The register page for booking agent
@app.route('/baRegister')
def baRegister():
    #cursor used to send queries
    cursor = conn.cursor()
    #assign a unique booking agent id
    query = 'SELECT MAX(booking_agent_id) as m_id FROM `booking_agent`'
    cursor.execute(query)
    try:
        assigned_id = int(cursor.fetchone()['m_id']) + 1
    except:
        assigned_id = 1
    session['assign'] = assigned_id
    return render_template('/registerBA.html', assign=assigned_id)

#register for Booking Agent
@app.route('/registerBA', methods=['GET', 'POST'])
def registerBA():   
    #grabs information from the forms
    Email = request.form["email"]
    password = hashlib.md5(request.form["password"].encode(encoding='UTF-8')).hexdigest()
    #id = request.form["id"]

    #cursor used to send queries
    cursor = conn.cursor()
	
    try:
        ins = 'INSERT INTO `booking_agent` VALUES(%s,%s,%s)'
        cursor.execute(ins,(Email, password, session['assign']))
        conn.commit()
        cursor.close()
        return render_template('/hello.html')
    except:
        cursor.close()
        error = "The email address has already been used!"
        return render_template('/registerBA.html', error=error, assign=session['assign'])
        

#The register page for airline staff
@app.route('/staffRegister')
def staffRegister():
    #cursor used to send queries
    cursor = conn.cursor()
	#find all airlines
    query = 'SELECT airline_name FROM `airline`'
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    session['airline_names'] = data
    return render_template('/registerStaff.html', names=data)

#register for Airline Staff
@app.route('/registerStaff', methods=['GET', 'POST'])
def registerStaff():
    #grabs information from the forms
    user_name = request.form["email"]
    password = hashlib.md5(request.form["password"].encode(encoding='UTF-8')).hexdigest()
    fst_name = request.form["fst_name"]
    last_name = request.form["last_name"]
    birth = datetime.strptime(request.form["birth"], "%Y-%m-%d")
    air_name = request.form["air_name"]

    #ckeck whether is adult#
    if birth > datetime.now()-relativedelta(years=18):
        return render_template('/registerStaff.html', error="We only admit adults!", names=session['airline_names'])
    
    #cursor used to send queries
    cursor = conn.cursor()
	
    try:
        ins = 'INSERT INTO `airline_staff` VALUES(%s,%s,%s,%s,%s,%s)'
        cursor.execute(ins,(user_name, password, fst_name, last_name, birth, air_name))
        conn.commit()
        cursor.close()
        return render_template('/hello.html')
    except:
        cursor.close()
        return render_template('/registerStaff.html', error="The Username has already been used!", names=session['airline_names'])

#Login Page
@app.route('/login')
def login():
    return render_template("/login.html")

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form["email"]
    password = hashlib.md5(request.form["password"].encode(encoding='UTF-8')).hexdigest()
    Id = request.form["identity"]
    ba_id = request.form["id"]

	#cursor used to send queries
    cursor = conn.cursor()
    
    #determine the login identity
    if Id == "ba":
        query = 'SELECT * FROM booking_agent WHERE email = %s AND password = %s AND booking_agent_id = %s'
        cursor.execute(query, (username, password, ba_id))
    else:
        if Id == "customer":
            query = 'SELECT * FROM customer WHERE email = %s AND password = %s'
        else:
            query = 'SELECT * FROM airline_staff WHERE username = %s AND password = %s'
        cursor.execute(query, (username, password))
    
    data = cursor.fetchone()

    if data:
        #creates a session for the the user
		#session is a built in
        session['username'] = username
        session['identity'] = Id
        session['ba_id'] = ba_id
        session['Admin'] = str(check_permission("Admin"))
        session['Operator'] = str(check_permission("Operator"))
        return redirect(url_for('home'))
    else:
        error = "Login Failure! Please Check your input information!"
        return render_template('/login.html', error=error)

#Home Page after login
@app.route('/home')
def home():
    username = session['username']
    Id = session['identity']
    return render_template('home.html', username=username, identity=Id, admin=session['Admin'], operator=session['Operator'])

#Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')



if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)