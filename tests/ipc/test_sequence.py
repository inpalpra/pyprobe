import threading

from pyprobe.core.sequence import SequenceGenerator


def test_sequence_generator_monotonic() -> None:
    gen = SequenceGenerator()
    results = []
    lock = threading.Lock()

    def worker(count: int) -> None:
        local = []
        for _ in range(count):
            local.append(gen.next())
        with lock:
            results.extend(local)

    threads = [threading.Thread(target=worker, args=(100,)) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 400
    assert len(set(results)) == 400
    assert min(results) == 0
    assert max(results) == 399
