"""Combined worker launcher: RQ worker + scheduler loop in one process.

Used by the compose ``worker`` service. Runs an RQ worker on the ``default``
queue and, in a daemon thread, the scheduler tick loop so due Events get
enqueued without a second container.
"""

import threading
import time


def main() -> None:
    from ._bootstrap import bootstrap_app_context
    from . import models  # noqa: F401  (pre-warm DB connection)

    with bootstrap_app_context():
        from .scheduler import Scheduler

        def _scheduler_loop():
            # Flask app contexts are thread-local: the daemon thread cannot
            # reuse the main thread's context. Push its own so current_app
            # and mongoengine resolve inside the loop (settings were already
            # registered by the main thread's connection).
            with bootstrap_app_context():
                sched = Scheduler()
                while True:
                    try:
                        sched.tick()
                    except Exception as exc:  # noqa: BLE001
                        import sys

                        print("scheduler tick error: %s" % exc, file=sys.stderr)
                    time.sleep(10)

        thread = threading.Thread(target=_scheduler_loop, daemon=True)
        thread.start()

        from rq import Worker
        from .worker import get_redis

        from .worker import jobs as _jobs  # noqa: F401

        worker = Worker(["default"], connection=get_redis())
        worker.work()


if __name__ == "__main__":
    main()