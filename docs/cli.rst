Command Line Interface
======================

Installing Platzky provides the ``platzky`` command.

.. code-block:: bash

    $ platzky --help

``platzky create``
------------------

Create a new application: a configuration file and a JSON database with sample content.

.. code-block:: bash

    $ platzky create
    $ platzky create --path sites/my-site

**Options:**

* ``--path``: directory the files are created in, created if missing (default: ``.``)

It writes two files and refuses to overwrite either if it already exists:

* ``config.yml`` — a placeholder ``APP_NAME`` to replace with your own, a freshly generated
  ``SECRET_KEY``, English as the only language, ``USE_WWW: false``, the ``json_file`` backend
  pointing at ``data.json``, and every built-in feature flag listed commented out at its
  default
* ``data.json`` — one sample post, an About page and a menu linking to both, so the site
  serves pages straight away

Edit both files to make the site your own: see :doc:`config` for the configuration options
and :doc:`database` for the content structure.

``platzky run``
---------------

Run the development server.

.. code-block:: bash

    $ platzky run --config config.yml
    $ platzky run --config config.yml --host 0.0.0.0 --port 8080

**Options:**

* ``--config``: path to the YAML configuration file (required)
* ``--host``: interface to bind to (default: ``127.0.0.1``)
* ``--port``: port to bind to (default: ``5000``)

``DEBUG: true`` in the configuration file enables the reloader and the interactive debugger.
The configuration file is the only switch for this.

.. warning::
    This is Flask's development server. For production, serve the application with a WSGI
    server such as gunicorn.

Running in Production
---------------------

A Platzky application is an ordinary WSGI application, so serve it with a production server:

.. code-block:: bash

    $ gunicorn "platzky.platzky:create_app(config_path='config.yml')"

Keep ``DEBUG: false`` there; a production server provides neither the reloader nor the
interactive debugger, and debug mode would expose internals.
