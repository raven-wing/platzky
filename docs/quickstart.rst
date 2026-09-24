Quickstart
==========

Eager to get started? This page gives a good introduction to Platzky.

A Minimal Application
---------------------

1. Install Platzky:

.. code-block:: bash

    $ pip install platzky

2. Create an application:

.. code-block:: bash

    $ platzky create --name "My Platzky App"

This writes ``config.yml`` and ``data.json`` into the current directory; use ``--path`` to
create them elsewhere. The site starts with one sample post and an About page, so it works
straight away. Edit ``config.yml`` to add languages or switch the database backend, and
``data.json`` to replace the sample content with your own.

3. Run the application:

.. code-block:: bash

    $ platzky run --config config.yml

The database path in the generated config is relative, so run the command from the directory
the application was created in.

4. Open http://127.0.0.1:5000 in your browser.

Use ``--host`` and ``--port`` to bind elsewhere, and set ``DEBUG: true`` in the configuration
file to get the reloader and the interactive debugger while developing.

The application is an ordinary Flask app, so it can also be started with Flask's own CLI or
served by a WSGI server such as gunicorn:

.. code-block:: bash

    $ flask --app "platzky.platzky:create_app(config_path='config.yml')" run --debug
    $ gunicorn "platzky.platzky:create_app(config_path='config.yml')"

With ``flask run``, debug mode comes from ``--debug`` or ``FLASK_DEBUG``, not from ``DEBUG``
in the configuration file.

Configuration
-------------

Platzky uses a YAML configuration file. Start with the provided template:

.. code-block:: bash

    $ cp config-template.yml config.yml
    $ # Edit config.yml with your settings

See :doc:`config` for detailed configuration options.

What to Do Next
---------------

* Read about :doc:`config` to understand all available options
* Learn about different :doc:`database` backends
* Check the :doc:`api` reference for detailed information
