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

    def snapshot(self):
        return {
            "channels": {
                1: {"enabled": True},
                2: {"enabled": False},
                3: {"enabled": True},
                4: {"enabled": False},
            },
            "horizontal": {"scale": 2e-4},
        }

    def set_vertical_scale(self, channel, scale):
        self.last_command = f"CH{channel}:SCALE {scale}"


class RejectingScope(FakeScope):
    def set_vertical_scale(self, channel, scale):
        raise RuntimeError("value rejected")


def test_connect_requests_complete_sync_on_next_poll():
    worker = InstrumentWorker()
    worker.connection = FakeConnection()
    worker.scope = FakeScope()
    worker.poll_count = 7
    events = []
    worker.snapshot_ready.connect(lambda state: events.append(("snapshot", state)))
    worker.connection_changed.connect(lambda connected, _identity, _resource: events.append(("connection", connected)))

    worker.connect_resource("USB::SCOPE", 5000)

    assert worker.poll_count == 0
    assert worker.enabled_channels == {1, 3}
    assert events[0][0] == "snapshot"
    assert events[0][1]["horizontal"]["scale"] == 2e-4
    assert events[1] == ("connection", True)


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
