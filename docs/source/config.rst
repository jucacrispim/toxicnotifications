Toxicnotifications config
===================

The configuration of toxicnotifications is done using the a configuration file. The configuration
file can be passed using the  ``-c`` flag to the ``toxicnotifications`` command
or settings the environment variable ``TOXICNOTIFICATIONS_SETTINGS``.

This file is a python file, so do what ever you want with it.

Config values
-------------

.. note::

   Although the config is done using a config file, the default
   configuration file created by ``toxicnotifications create`` can use
   environment variables instead.


* ``PORT`` - The port for the server to listen. Defaults to `9432`.
  Environment variable: ``NOTIFICATIONS_PORT``

* ``DBHOST`` - Host for the database connection.
  Environment variable: ``NOTIFICATIONS_DBHOST``.

* ``DBPORT`` - Port for the database connection. Defaults to `27017`.
  Environment variable: ``NOTIFICATIONS_DBPORT``.

* ``DBNAME`` - The database name. Defaults to `toxicnotifications`.
  Environment variable: ``NOTIFICATIONS_DBNAME``

* ``DBUSER`` - User name for authenticated access to the database
  Environment variable: ``NOTIFICATIONS_DBUSER``

* ``DBPASS`` - Password for authenticated access to the database
  Environment variable: ``NOTIFICATIONS_DBPASSWORD``


 ``AMQP_HOST`` - host for the rabbitmq broker.
  Environment variable: ``AMQPHOST``

* ``AMQP_PORT`` - port for the rabbitmq broker.
  Environment variable: ``AMQPPORT``

* ``AMQP_LOGIN`` - login for the rabbitmq broker.
  Environment variable: ``AMQPLOGIN``

* ``AMQP_VIRTUALHOST`` - virtualhost for the rabbitmq broker.
  Environment variable: ``AMQPVIRTUALHOST``

* ``AMQP_PASSWORD`` - password for the rabbitmq broker.
  Environment variable: ``AMQPPASSWORD``
