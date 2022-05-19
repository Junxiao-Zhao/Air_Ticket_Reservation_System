-------------------Before login in-------------------

--1.View Public Info
    --Search for flights based on the departure airport/city, the arrival airport/city, and the date; raise error if no flights are found
    SELECT * FROM `flight` WHERE (departure_airport = %s OR departure_airport IN (SELECT airport_name FROM `airport` WHERE airport_city = %s)) AND (arrival_airport = %s OR arrival_airport IN (SELECT airport_name FROM `airport` WHERE airport_city = %s)) AND departure_time BETWEEN %s AND %s;

    --See the flights' status based on flight number, arrival/departure date; raise error if no flights are found
    SELECT * FROM `flight` WHERE flight_num = %s AND ((departure_time BETWEEN %s AND %s) OR (arrival_time BETWEEN %s AND %s));

--2.Register
    --Customer Register
        --Raise Error if the birth date is after today 
        --Raise Error if the passport has expired
        --Insert user info into the `customer`
        INSERT INTO `customer` VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
        --Raise Error if the email has already existed

    --Booking Agent Register
        --Auto assign a unique Booking Agent ID (= current maximum id + 1)
        SELECT MAX(booking_agent_id) as m_id FROM `booking_agent`;
        --Insert booking agent info into `booking_agent`
        INSERT INTO `booking_agent` VALUES(%s,%s,%s);
        --Raise Error if the email has already existed
    
    --Airline Staff Register
        --Select all the airlines for the staff to choose
        SELECT airline_name FROM `airline`;
        --Raise Error if the birth date entered indicated that the staff is not an adult
        --Insert the staff info into `airline_staff`
        INSERT INTO `airline_staff` VALUES(%s,%s,%s,%s,%s,%s);
        --Raise Error if the username has already existed

--3.Login
    --Customer Login
        --Check the email and password in `customer`
        SELECT * FROM `customer` WHERE email = %s AND password = %s;
        --Raise Error if we could not find
    
    --Booking Agent Login
        --Check the email, password and booking agent id in `booking_agent`
        SELECT * FROM `booking_agent` WHERE email = %s AND password = %s AND booking_agent_id = %s;
        --Raise Error if we could not find
    
    --Airline Staff Login
        --Check the username and password in `airline_staff`
        SELECT * FROM `airline_staff` WHERE username = %s AND password = %s;
        --Raise Error if we could not find


-------------------After login in-------------------

--Customer
    --1.View My flights
        --View the upcoming flights
        SELECT P.customer_email AS username, F.* FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE customer_email = %s AND F.departure_time > %s ORDER BY F.departure_time ASC;
        --Search for flights in the specified range; raise error if the start date is after the end date
        SELECT P.customer_email AS username, F.* FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE customer_email = %s AND F.departure_time BETWEEN %s AND %s ORDER BY F.departure_time ASC;

    --2.View flights' Status
        --See the flights' status based on flight number, arrival/departure date; raise error if no flights are found
        SELECT * FROM `flight` WHERE flight_num = %s AND ((departure_time BETWEEN %s AND %s) OR (arrival_time BETWEEN %s AND %s));

    --3.Purchase tickets
        --Check the departure time; raise error if the flight has finished
        SELECT airplane_id, departure_time FROM flight WHERE airline_name = %s AND flight_num = %s;
        --Get the number of tickets sold and the number of seats; raise error if no room left
        SELECT COUNT(*) FROM ticket WHERE airline_name = %s AND flight_num = %s;
        SELECT seats FROM airplane WHERE airplane_id = %s;
        --Auto generate the ticket id (= current maximum id + 1)
        SELECT MAX(ticket_id) AS max FROM `ticket`;
        --Insert ticket info into `ticket` and `purchases`
        INSERT INTO `ticket` VALUES(%s,%s,%s);
        INSERT INTO `purchases` VALUES(%s,%s,%s,%s);
    
    --4.Refund tickets
        --Get all upcoming flights booked by this customer
        SELECT ticket_id, F.* FROM `flight` AS F NATURAL JOIN `ticket` NATURAL JOIN `purchases` WHERE customer_email = %s AND F.departure_time > %s;
        --Delete the selected flights from `purchases` and `ticket`
        DELETE FROM `purchases` WHERE ticket_id = %s;
        DELETE FROM `ticket` WHERE ticket_id = %s;
    
    --5.Search for flights
        --Search for flights based on source city/airport name, destination city/airport name, date; raise error if no flights are found
        SELECT * FROM `flight` WHERE (departure_airport = %s OR departure_airport IN (SELECT airport_name FROM `airport` WHERE airport_city = %s)) AND (arrival_airport = %s OR arrival_airport IN (SELECT airport_name FROM `airport` WHERE airport_city = %s)) AND departure_time BETWEEN %s AND %s;

    --6.Track My Spending
        --Show total amount of money spent in the past year and a bar chart showing month wise money spent for last 6 months, or in the specified range
        SELECT SUM(F.price) AS Amount, DATE_FORMAT(purchase_date, "%%Y-%%m") AS Month FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE customer_email = %s AND P.purchase_date BETWEEN %s AND %s GROUP BY DATE_FORMAT(purchase_date, "%%Y%%m");

--Booking Agent
    --1.View My flights
        --Default display the upcoming flights
        SELECT P.customer_email AS username, F.* FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE P.booking_agent_id = %s AND P.booking_agent_id IS NOT NULL AND F.departure_time > %s ORDER BY F.departure_time ASC;
        --Search for flights in the specified range; raise error if the start date is after the end date
        SELECT P.customer_email AS username, F.* FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE P.booking_agent_id = %s AND P.booking_agent_id IS NOT NULL AND F.departure_time BETWEEN %s AND %s ORDER BY F.departure_time ASC;

    --2.Purchase tickets
        --Check whether the booking agent works for the airline; raise error if it not works for
        SELECT airline_name FROM `booking_agent_work_for` WHERE email = %s;
        --Check the departure time; raise error if the flight has finished
        SELECT airplane_id, departure_time FROM flight WHERE airline_name = %s AND flight_num = %s;
        --Get the number of tickets sold and the number of seats; raise error if no room left
        SELECT COUNT(*) FROM ticket WHERE airline_name = %s AND flight_num = %s;
        SELECT seats FROM airplane WHERE airplane_id = %s;
        --Auto generate the ticket id (= current maximum id + 1)
        SELECT MAX(ticket_id) AS max FROM `ticket`;
        --Insert ticket info into `ticket` and `purchases`
        INSERT INTO `ticket` VALUES(%s,%s,%s);
        INSERT INTO `purchases` VALUES(%s,%s,%s,%s);

    --3.Refund tickets
        --Get all upcoming flights booked by this booking agent
        SELECT ticket_id, F.* FROM `flight` AS F NATURAL JOIN `ticket` NATURAL JOIN `purchases` WHERE booking_agent_id = %s AND booking_agent_id IS NOT NULL AND F.departure_time > %s;
        --Delete the selected flights from `purchases` and `ticket`
        DELETE FROM `purchases` WHERE ticket_id = %s;
        DELETE FROM `ticket` WHERE ticket_id = %s;
    
    --4.Search for flights
        --Search for upcoming flights based on source city/airport name, destination city/airport name, date; raise error if no flights are found
        SELECT * FROM `flight` WHERE (departure_airport = %s OR departure_airport IN (SELECT airport_name FROM `airport` WHERE airport_city = %s)) AND (arrival_airport = %s OR arrival_airport IN (SELECT airport_name FROM `airport` WHERE airport_city = %s)) AND departure_time BETWEEN %s AND %s;

    --5.View Commission
        --View the total amount of commission received and the average commission he/she received per ticket booked in the past 30 days or in the specified range
        SELECT SUM(price*0.1) AS sum, AVG(price*0.1) as avg, COUNT(price) as num FROM `purchases` AS P INNER JOIN `ticket` AS T ON P.ticket_id = T.ticket_id INNER JOIN `flight`AS F ON T.airline_name = F.airline_name AND T.flight_num = F.flight_num WHERE P.booking_agent_id = %s AND P.booking_agent_id IS NOT NULL AND P.purchase_date BETWEEN %s AND %s;
    
    --6.View Top Customers
        --View the top 5 customers based on number of tickets bought from the booking agent in the past 6 months or in the specified range
        SELECT customer_email, COUNT(customer_email) AS num FROM `purchases` WHERE booking_agent_id = %s AND booking_agent_id IS NOT NULL AND purchase_date BETWEEN %s AND %s GROUP BY customer_email ORDER BY COUNT(customer_email) DESC;
        --View the top 5 customers based on amount of commission received in the last year or in the specified range
        SELECT customer_email, COUNT(customer_email) AS num FROM `purchases` WHERE booking_agent_id = %s AND booking_agent_id IS NOT NULL AND purchase_date BETWEEN %s AND %s GROUP BY customer_email ORDER BY COUNT(customer_email) DESC;

--Airline Staff
    --1.View My flights
        --Show all the upcoming flights operated by the airline he/she works for the next 30 days or in the specified range
        SELECT * FROM `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND departure_time BETWEEN %s AND %s ORDER BY departure_time ASC;
    
    --2.Create new flights
        ---Check the 'Admin' permission; raise error if the staff doesn't have the permission
        SELECT permission_type FROM `permission` WHERE username = %s;
        --Default showing all the upcoming flights operated by the airline he/she works for the next 30 days
        SELECT * FROM `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND departure_time BETWEEN %s AND %s ORDER BY departure_time ASC;
        --Get all the airports for the staff to choose
        SELECT airport_name FROM `airport`;
        --Get all the airplane ids of this airline for the staff to choose
        SELECT airplane_id FROM `airplane` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s);
        --Raise Error if the staff enters wrong date format
        --Raise Error if the staff enters negative price
        --Insert the flight info into `flight`; raise error if the flight number has already existed
        INSERT INTO `flight` VALUES((SELECT airline_name FROM `airline_staff` WHERE username = %s),%s,%s,%s,%s,%s,%s,%s,%s);

    --3.Change Status of flights
        --Check the 'Operator' permission; raise error if the staff doesn't have the permission
        SELECT permission_type FROM `permission` WHERE username = %s;
        --Select all the flight numbers operated by the airline for the staff to choose
        SELECT flight_num FROM `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s);
        --Update the status
        UPDATE `flight` SET status = %s WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND flight_num = %s;

    --4.Add airplane in the system
        --Check the 'Admin' permission; raise error if the staff doesn't have the permission
        SELECT permission_type FROM `permission` WHERE username = %s;
        --Default showing all the airplanes owned by the airline
        SELECT * FROM `airplane` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s);
        --Insert the airplane info into `airplane`; raise error if the airplane id has already existed
        INSERT INTO `airplane` VALUES((SELECT airline_name FROM `airline_staff` WHERE username = %s),%s,%s);

    --5.Add new airport in the system
        --Check the 'Admin' permission; raise error if the staff doesn't have the permission
        SELECT permission_type FROM `permission` WHERE username = %s;
        --Insert the airport info into `airport`; raise error if the airport has already existed
        INSERT INTO `airport` VALUES(%s,%s);
    
    --6.View all the booking agents
        --Sort booking agents based on number of tickets sales for the past month and past year
        SELECT email, COUNT(email) AS num FROM `booking_agent_work_for` NATURAL JOIN `booking_agent` NATURAL JOIN `purchases` NATURAL JOIN `ticket` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s GROUP BY email ORDER BY COUNT(email) DESC;
        --Sort booking agents based on the amount of commission received for the last year
        SELECT email, SUM(price*0.1) as amount FROM `booking_agent_work_for` NATURAL JOIN `booking_agent` NATURAL JOIN `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s GROUP BY email ORDER BY amount DESC;
    
    --7.View frequent customers
        --See the most frequent customer within the last year
        WITH freq AS (SELECT customer_email, COUNT(customer_email) AS num FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND departure_time BETWEEN %s AND %s GROUP BY customer_email) SELECT customer_email FROM freq WHERE num = (SELECT MAX(num) FROM freq);
        --Select all the customer taken this airline's flights in the last year for the staff to choose
        SELECT DISTINCT customer_email FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND departure_time BETWEEN %s AND %s;
        --See the list of a list of all flights a particular Customer has taken only on that particular airline
        SELECT * FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND customer_email = %s AND departure_time < %s;
    
    --8.View reports
        --Total amounts of ticket sold based on range of dates/last year/last month etc
        SELECT COUNT(ticket_id) AS num FROM `ticket` NATURAL JOIN `purchases` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s;

    --9.Comparison of Revenue earned
        --Retrieve the direct sales earn in the last month/year or in the specified range
        SELECT SUM(price) AS sum FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s AND booking_agent_id IS NULL;
        --Retrieve the indirect sales earn in the last month/year or in the specified range
        SELECT SUM(price) AS sum FROM `purchases` NATURAL JOIN `ticket` NATURAL JOIN `flight` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND purchase_date BETWEEN %s AND %s AND booking_agent_id IS NOT NULL;
        --Raise Error if no tickets sold in the last month/year or in the specified range
    
    --10.View Top Destinations
        --Sort the destinations for last 3 months and last year
        SELECT arrival_airport, COUNT(arrival_airport) AS num FROM `purchases` NATURAL JOIN `flight` NATURAL JOIN `ticket` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s) AND arrival_time BETWEEN %s AND %s GROUP BY arrival_airport ORDER BY num DESC;

    --11.Grant new permissions
        --Check the 'Admin' permission; raise error if the staff doesn't have the permission
        SELECT permission_type FROM `permission` WHERE username = %s;
        --Get all the staffs' usernames for the Admin to choose
        SELECT username FROM `airline_staff` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s);
        --Insert the permission into `permission`; raise error if the selected staff has already had that permission
        INSERT INTO `permission` VALUES (%s,%s);

    --12.Add booking agents
        --Check the 'Admin' permission; raise error if the staff doesn't have the permission
        SELECT permission_type FROM `permission` WHERE username = %s;
        --Default display all the booking agents working for this airline
        SELECT * FROM `booking_agent_work_for` WHERE airline_name = (SELECT airline_name FROM `airline_staff` WHERE username = %s);
        --Insert the new booking agent email into `booking_agent_work_for`; raise error if the booking agent booking agent has already been added or does not exist
        INSERT INTO `booking_agent_work_for` VALUES(%s,(SELECT airline_name FROM `airline_staff` WHERE username = %s));