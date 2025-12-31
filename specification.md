# Home Foods Online Ordering & Order Management — Specification

This is a backend-focused web application for a **home-based food business**
that supplies **home-made food items only on order basis**
(not a shop or restaurant).

Goal: help customers **place food orders online**
and help the owner **manage orders efficiently** using a simple backend system.

Most home food businesses face these problems:

- Orders come through calls, WhatsApp, or messages and get mixed up
- No clear tracking of pending, prepared, or delivered orders
- Difficulty managing daily limited food quantity

## end goal : Even a small number of regular customers can easily place orders, while the owner can manage everything digitally.

### Users :

#### Customer
- Views available food items
- Sees price and availability
- Places an order by entering:
  - name
  - phone number
  - address
  - quantity
- Checks order status

#### Admin (Owner)
- Logs in
- Adds and updates food items
- Sets price and availability
- Views all customer orders
- Updates order status:
  - pending
  - accepted
  - prepared
  - delivered

user places order independently  
admin stays in control of food preparation and delivery  
backend system manages data and tracking

### Software need to use:

- Programming language : Python
- Database : SQLite & SQLAlchemy
- Backend : Python API (Flask / Django)
- Frontend : HTML and Tailwind CSS
