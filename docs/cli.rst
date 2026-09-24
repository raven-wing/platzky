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
Unlike ``flask run``, the configuration file decides this; the ``FLASK_DEBUG`` environment
variable is ignored.

.. warning::
    This is Flask's development server. For production, serve the application with a WSGI
    server such as gunicorn.

Running Without the CLI
-----------------------

A Platzky application is an ordinary Flask application, so it can also be started with
Flask's own CLI or a WSGI server:

.. code-block:: bash

    $ flask --app "platzky.platzky:create_app(config_path='config.yml')" run --debug
    $ gunicorn "platzky.platzky:create_app(config_path='config.yml')"

With ``flask run``, debug mode comes from ``--debug`` or ``FLASK_DEBUG`` rather than from
``DEBUG`` in the configuration file.
