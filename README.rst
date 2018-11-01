========
SnapPass
========


About this fork
---------------

The goal of this fork is to create an entreprise solution without sharing the solution to everybody. In this contexte if you want external people to share a secret with internal ones, there is a feature to share a temporary link to allow this.

Here is an example of a possible architecture:

[[https://github.com/sebnetdev/snappass/blob/master/img/snappass-archi.png|alt=snappass-archi]]

The goal is to protect the solution using WAF and reverse proxy and expose only the secrets and the temporary links.

I also add the possibility to set a base path to make https://example.com/snappass/ possible.   

I updated the version of jquery with the latest version and the same for bootstrap and font awsome.

I add an option to chose the IP address where the service binds, 127.0.0.1 is a better option than 0.0.0.0 in a non-docker context.

I changed the way to encode the encryption key in order to avoid the missing '=' at the end of the link when you share the link with your email application.

There are a couple of options for:
  - Title
  - Company name
  - Company logo URL
  - Help URL
  - Liste of TTL
  - Listen IP address



|pypi| |build|

.. |pypi| image:: https://img.shields.io/pypi/v/snappass.svg
    :target: https://pypi.python.org/pypi/snappass
    :alt: Latest version released on PyPI

.. |build| image:: https://travis-ci.org/pinterest/snappass.svg
    :target: http://travis-ci.org/pinterest/snappass
    :alt: Build status

It's like SnapChat... for Passwords.

This is a webapp that lets you share passwords securely.

Let's say you have a password.  You want to give it to your coworker, Jane.
You could email it to her, but then it's in her email, which might be backed up,
and probably is in some storage device controlled by the NSA.

You could send it to her over chat, but chances are Jane logs all her messages
because she uses Google Talk, and Google Talk logs everything.

You could write it down, but you can't find a pen, and there's way too many
characters because your Security Person, Paul, is paranoid.

So we built SnapPass.  It's not that complicated, it does one thing.  If
Jane gets a link to the password and never looks at it, the password goes away.
If the NSA gets a hold of the link, and they look at the password... well they
have the password.  Also, Jane can't get the password, but now Jane knows that
not only is someone looking in her email, they are clicking on links.

Anyway, this took us very little time to write, but we figure we'd save you the
trouble of writing it yourself, because maybe you are busy and have other things
to do.  Enjoy.

Security
--------

Passwords are encrypted using `Fernet`_ symmetric encryption, from the `cryptography`_ library.
A random unique key is generated for each password, and is never stored;
it is rather sent as part of the password link.
This means that even if someone has access to the Redis store, the passwords are still safe.

.. _Fernet: https://cryptography.io/en/latest/fernet/
.. _cryptography: https://cryptography.io/en/latest/

Requirements
------------

* Redis
* Python 2.7+ or 3.4+ (both included)

Installation
------------

::

    $ pip install snappass
    $ snappass
    * Running on http://0.0.0.0:5000/
    * Restarting with reloader

Configuration
-------------

You can configure the following via environment variables.

`SECRET_KEY` unique key that's used to sign key. This should
be kept secret.  See the `Flask Documentation`__ for more information.

.. __: http://flask.pocoo.org/docs/quickstart/#sessions

`DEBUG` to run Flask web server in debug mode.  See the `Flask Documentation`__ for more information.

.. __: http://flask.pocoo.org/docs/quickstart/#debug-mode

`STATIC_URL` this should be the location of your static assets.  You might not
need to change this.

`NO_SSL` if you are not using SSL.

`REDIS_HOST` this should be set by Redis, but you can override it if you want. Defaults to `"localhost"`

`REDIS_PORT` is the port redis is serving on, defaults to 6379

`SNAPPASS_REDIS_DB` is the database that you want to use on this redis server. Defaults to db 0

`REDIS_URL` (optional) will be used instead of `REDIS_HOST`, `REDIS_PORT`, and `SNAPPASS_REDIS_DB` to configure the Redis client object. For example: redis://username:password@localhost:6379/0

`REDIS_PREFIX` (optional, defaults to `"snappass"`) prefix used on redis keys to prevent collisions with other potential clients

Docker
------

Alternatively, you can use `Docker`_ and `Docker Compose`_ to install and run SnapPass:

.. _Docker: https://www.docker.com/
.. _Docker Compose: https://docs.docker.com/compose/

::

    $ docker-compose up -d

This will pull all dependencies, i.e. Redis and appropriate Python version (3.6), then start up SnapPass and Redis server. SnapPass server is accessible at: http://localhost:5000

We're Hiring!
-------------

Are you really excited about open-source and great software engineering?
Pinterest is [hiring](https://careers.pinterest.com/)!
