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

    $ platzky create

This writes ``config.yml`` and ``data.json`` into the current directory; use ``--path`` to
create them elsewhere. The site starts with one sample post and an About page, so it works
straight away. Set ``APP_NAME`` in ``config.yml`` to your own name, add languages or switch
the database backend there, and replace the sample content in ``data.json`` with your own.

3. Run the application:

.. code-block:: bash

    $ platzky run --config config.yml

The database path in the generated config is relative, so run the command from the directory
the application was created in.

4. Open http://127.0.0.1:5000 in your browser.

See :doc:`cli` for the remaining options, for enabling debug mode, and for serving the
application in production.

Configuration
-------------

Platzky uses a YAML configuration file. ``platzky create`` writes a minimal one; the
``config-template.yml`` shipped with the source shows every option with comments, including
the other database backends:

.. code-block:: bash

    $ cp config-template.yml config.yml
    $ # Edit config.yml with your settings

See :doc:`config` for detailed configuration options.

What to Do Next
---------------

* Read about :doc:`config` to understand all available options
* Learn about different :doc:`database` backends
* See the :doc:`cli` reference for the ``platzky`` command
* Check the :doc:`api` reference for detailed information
