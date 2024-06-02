Notifications API
=================

Toxicnotifications uses an http api to enable/disable notifications
for a given repository. To send notifications it reads messages from
ampq.


List available notifications
----------------------------

A ``GET`` request to ``<notifications_url>/list/<repo_id>`` will list
the notifications available/enabled for a given repo.


Enable notification
-------------------

Send a ``POST`` request to ``<notifications_url>/<notification_name>`` to
enable a notification to a given repository.

The body of the request must be a json with a ``repository_id`` and the config
params for the given notification.


Disable notification
--------------------

Send a ``DELETE`` request to ``<notifications_url>/<notification_name>`` to
disable a notification for a given repository.


Update notification
--------------------

Send a ``PUT`` request to ``<notifications_url>/<notification_name>`` to
update the configs of a notification for a given repository.


Send email
----------
Send a ``POST`` request to ``<notifications_url>/send-email`` to
send an email.

The body request must be a json with the following keys:

``recipients``, ``subject`` and ``message``.
