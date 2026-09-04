Changelog
=========

* v0.11.3

  - Update toxiccore

* v0.11.2

  - Refactor server to start notification handler on server start

* v0.11.1

  - Update toxiccore

* v0.11.0

  - Refactor the server from an HTTP API to a TCP connection using
    ``toxiccore`` (``BaseToxicProtocol``/``ToxicServer``), matching the
    protocol used by the other toxicbuild services.
  - Compatibility with RabbitMQ 4.x via ``toxiccommon 0.11.0``: non-exclusive
    queues are now always declared as durable, fixing the ``transient_
    nonexcl_queues`` error (541) that made the functional tests fail.
  - Pin ``toxiccommon==0.11.0``, ``toxiccore==0.13.2`` and
    ``mongomotor==0.17.1``.
  - Update ``toxicmaster`` to ``0.12.5``.

* v0.10.2

  - Fix config template

* v0.10.1

  - Fix packaging

* v0.10.0

  - First version on its own repo outside toxicuild
