# Campus Food-Ordering App

Students at IIIT Vadodara waste most of their lunch break queueing at the three campus
canteens. We want a mobile-first web app and an Android app where a student signs in with
their college email, browses each canteen's live menu, places an order, pays by UPI, and gets
a notification when the order is ready for pickup.

Canteen vendors need a simple dashboard to mark items in or out of stock, see incoming
orders in a queue, accept or reject them, and mark them ready. They also want a daily sales
summary they can download.

Must have for launch:
- Sign-in with college email (OTP), student profile, order history
- Menu and catalogue per canteen with categories, prices, veg/non-veg tags, availability
- Cart, checkout, UPI payment through a payment gateway, refunds for rejected orders
- Order status updates (placed, accepted, ready, picked up) with push notifications
- Vendor dashboard: order queue, stock toggles, daily sales report (CSV)
- Admin can add canteens and vendor accounts

Constraints: the college IT team hosts it on their own servers with Docker. Payment data
must never be stored by us beyond the gateway's transaction id. About 2,000 students and
3 vendors at launch. The team is 8 people; the semester project ends in about 6 weeks.
