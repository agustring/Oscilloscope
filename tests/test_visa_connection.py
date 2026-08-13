from mso2024_remote.instrument.visa_connection import VisaConnection


class FakeResource:
    def __init__(self):
        self.timeout = 0
        self.write_termination = None
        self.read_termination = None
        self.queries = []
        self.writes = []
        self.closed = False

    def query(self, command):
        self.queries.append(command)
        return "TEKTRONIX,MSO2024,0,1"

    def write(self, command):
        self.writes.append(command)

    def close(self):
        self.closed = True


class FakeManager:
    def __init__(self, resource):
        self.resource = resource

    def open_resource(self, _name):
        return self.resource


def test_connect_identifies_scope_without_changing_its_configuration():
    resource = FakeResource()
    connection = VisaConnection()
    connection.resource_manager = FakeManager(resource)

    identity = connection.connect("USB::SCOPE")

    assert identity == "TEKTRONIX,MSO2024,0,1"
    assert resource.queries == ["*IDN?"]
    assert resource.writes == []
