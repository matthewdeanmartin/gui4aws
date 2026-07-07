# ADR 0002: serialized API worker

AWS and emulator API calls run through one serialized worker queue.

Tk stays on the main thread. Results return through a queue and are applied by the Tk event loop.

This favors responsiveness and predictable Moto behavior over parallel request fan-out.

The known tradeoff is queue fairness: background cache warming can delay later foreground work.
