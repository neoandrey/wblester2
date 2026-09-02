"""Redis-backed background worker (RQ + rq-scheduler).

Tasks enqueued by the WebApi process are executed here. Every handler is
import-safe when Redis or Mongo is unreachable so the worker can start
before the rest of the stack stabilises.

Two entry points are provided for the compose ``worker`` service:

- ``python -m wblester_api.worker``          run the RQ worker process (foreground)
- ``python -m wblester_api.worker --scheduler`` run the rq-scheduler loop that
  polls Events/Schedules and enqueues due sends, then keeps running.
"""

import argparse
import sys


def get_redis():
    import redis
    from redis import Redis
    from redis.retry import Retry
    from redis.exceptions import (
        TimeoutError as RedisTimeoutError,
        ConnectionError as RedisConnectionError
    )
    from redis.backoff import ExponentialBackoff

    from flask import current_app

    host = current_app.config.get("REDIS_HOST", "localhost")
    port = int(current_app.config.get("REDIS_PORT", 6379))
    # RQ requires a byte-mode connection (do NOT set decode_responses=True),
    # otherwise its registries trip over str/bytes decoding.
    
    rd=  None
    if current_app.config.get("REDIS_USERNAME") :
        
        try:
                pool=redis.ConnectionPool(
                host=current_app.config.get("REDIS_HOST", "localhost"),
                port=int(current_app.config.get("REDIS_PORT", 6379)),
                username=current_app.config.get("REDIS_USERNAME"),
                password=current_app.config.get("REDIS_PASSWORD"),
                    socket_connect_timeout=(2),
                    socket_timeout=(2),
                    #single_connection_client=True,
                    retry=Retry(ExponentialBackoff(cap=10, base=1), 25),
                    retry_on_error=[
                        RedisConnectionError,
                        RedisTimeoutError,
                        ConnectionResetError,
                    ],
                    health_check_interval=(30),
                    socket_keepalive=False,
                    retry_on_timeout=True,
                )
                rd = Redis(connection_pool=pool)
        except ConnectionError:
            print("Redis connection error: %s:%s" % (host, port), file=sys.stderr)
    else:
        try:
            rd = redis.Redis(
                host=current_app.config.get("REDIS_HOST", "localhost"),
                port=int(current_app.config.get("REDIS_PORT", 6379)),
                socket_connect_timeout=(2),
                socket_timeout=(2),
                #single_connection_client=True,
                retry=Retry(ExponentialBackoff(cap=10, base=1), 25),
                retry_on_error=[
                    RedisConnectionError,
                    RedisTimeoutError,
                    ConnectionResetError,
                ],
                health_check_interval=(30),
                socket_keepalive=False,
                retry_on_timeout=True,
            )
        except ConnectionError:
            print("Redis connection error: %s:%s" % (host, port), file=sys.stderr)   
             
        
    return rd #redis.Redis(host=host, port=port)


def get_queue(name="default"):
    from rq import Queue

    conn = get_redis()
    return Queue(name, connection=conn)


def enqueue_send_mail(recipients, subject, html) -> str:
    """Queue a one-shot templated send. Returns the RQ job id (no outbox row)."""
    job = get_queue().enqueue("wblester_api.worker.jobs.deliver_mail", recipients, subject, html)
    return job.id


def enqueue_event_job(event_id: int) -> str:
    """Queue execution of an Event's triggered send. Returns the RQ job id."""
    job = get_queue().enqueue("wblester_api.worker.jobs.run_event", event_id)
    return job.id


def run_worker() -> None:
    import mongoengine
    from rq import Worker

    from ._bootstrap import bootstrap_app_context

    with bootstrap_app_context():
        # Pre-warm the DB connection inside the worker's process.
        from . import models  # noqa: F401
        mongoengine.get_connection()

        # Pull every handler module into the worker namespace so enqueued
        # tasks resolve by dotted path.
        from .worker import jobs  # noqa: F401

        queues = ["default"]
        w = Worker(queues, connection=get_redis())
        w.work()


def run_scheduler(interval: int = 10) -> None:
    import time

    from ._bootstrap import bootstrap_app_context

    with bootstrap_app_context():
        from .scheduler import Scheduler

        sched = Scheduler()
        print("rq-scheduler: polling every %ss" % interval)
        while True:
            try:
                sched.tick()
            except Exception as exc:  # noqa: BLE001
                print("scheduler tick error: %s" % exc)
            time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheduler", action="store_true")
    args = parser.parse_args()
    if args.scheduler:
        run_scheduler()
    else:
        run_worker()


if __name__ == "__main__":
    main()