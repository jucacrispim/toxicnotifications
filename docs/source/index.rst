:tocdepth: 1

Toxicnotifications: Send notifications about builds
===================================================


Install
-------

To install it use pip:

.. code-block:: sh

   $ pip install toxicnotifications --extra-index-url=https://pypi.poraodojuca.dev



Setup & config
--------------

Before executing builds you must create an environment for toxicnotifications.
To do so use:

.. code-block:: sh

   $ toxicnotifications create ~/notifications-env

This is going to create a ``~/notifications-env`` directory with a ``toxicnotifications.conf``
file in it. This file is used to configure toxicnotifications.

Check the configuration instructions for details

.. toctree::
   :maxdepth: 1

   config


Run the server
--------------

When the configuration is done you can run the server with:

.. code-block:: sh

   $ toxicnotifications start ~/notifications-env


For all options for the toxicnotifications command execute

.. code-block:: sh

   $ toxicnotifications --help


Notifications API
=================

With the server running you can store and retrieve secrets. Check the
api documentation for details

.. toctree::
   :maxdepth: 1

   notifications_api.rst


CHANGELOG
---------

.. toctree::
   :maxdepth: 1

   CHANGELOG
