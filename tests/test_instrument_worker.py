from mso2024_remote.workers.instrument_worker import InstrumentWorker


class FakeConnection:
    connected = True
    resource_name = "USB::SCOPE"
    identity = "TEKTRONIX,MSO2024,0,1"

    def set_timeout(self, timeout_ms):
        self.timeout_ms = timeout_ms

    def connect(self, resource):
        self.resource_name = resource
        return self.identity


class FakeScope:
    last_command = ""
    last_response = ""

    def set_vertical_scale(self, channel, scale):
        self.last_command = f"CH{channel}:SCALE {scale}"


class RejectingScope(FakeScope):
    def set_vertical_scale(self, channel, scale):
        raise RuntimeError("value rejected")


def test_connect_requests_complete_sync_on_next_poll():
    worker = InstrumentWorker()
    worker.connection = FakeConnection()
    worker.poll_count = 7

    worker.connect_resource("USB::SCOPE", 5000)

    assert worker.poll_count == 0


def test_setting_change_requests_complete_sync_on_next_poll():
    worker = InstrumentWorker()
    worker.connection = FakeConnection()
    worker.scope = FakeScope()
    worker.poll_count = 7

    worker.invoke("set_vertical_scale", [1, 0.5])

    assert worker.poll_count == 0


def test_rejected_setting_requests_readback_on_next_poll():
    worker = InstrumentWorker()
    worker.connection = FakeConnection()
    worker.scope = RejectingScope()
    worker.poll_count = 7

    worker.invoke("set_vertical_scale", [1, 0.5])

    assert worker.poll_count == 0
