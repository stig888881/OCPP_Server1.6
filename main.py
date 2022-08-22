import asyncio
import logging
import sys
from datetime import datetime
from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import Action, RegistrationStatus
from ocpp.v16 import call_result
import DataBase
from asyncqt import QEventLoop
from PyQt5 import QtCore, QtWebSockets, QtNetwork
from PyQt5.QtWidgets import QApplication

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys
    sys.exit(1)


logging.basicConfig(level=logging.INFO)

User = 0

class MyServer(QtCore.QObject):
    def __init__(self, parent):
        super(QtCore.QObject, self).__init__(parent)
        self.clients = []
        print("server name: {}".format(parent.serverName()))
        self.server = QtWebSockets.QWebSocketServer(parent.serverName(), parent.secureMode(), parent)
        if self.server.listen(QtNetwork.QHostAddress.LocalHost, 1302):
            print('Listening: {}:{}:{}'.format(
                self.server.serverName(), self.server.serverAddress().toString(),
                str(self.server.serverPort())))
        else:
            print('error')
        self.server.acceptError.connect(self.onAcceptError)
        self.server.newConnection.connect(self.onNewConnection)
        self.clientConnection = None
        print(self.server.isListening())

    def onAcceptError(accept_error):
        print("Accept Error: {}".format(accept_error))

    def onNewConnection(self):
        print("onNewConnection")
        self.clientConnection = self.server.nextPendingConnection()
        self.clientConnection.textMessageReceived.connect(self.processTextMessage)

        self.clientConnection.textFrameReceived.connect(self.processTextFrame)

        self.clientConnection.binaryMessageReceived.connect(self.processBinaryMessage)
        self.clientConnection.disconnected.connect(self.socketDisconnected)

        print("newClient")
        self.clients.append(self.clientConnection)

    def processTextFrame(self, frame, is_last_frame):
        print("in processTextFrame")
        print("\tFrame: {} ; is_last_frame: {}".format(frame, is_last_frame))

    def processTextMessage(self, message):
        print("processTextMessage - message: {}".format(message))
        if self.clientConnection:
            for client in self.clients:
                client.sendTextMessage(message)


    def processBinaryMessage(self, message):
        print("b:",message)
        if self.clientConnection:
            self.clientConnection.sendBinaryMessage(message)

    def socketDisconnected(self):
        print("socketDisconnected")
        if self.clientConnection:
            self.clients.remove(self.clientConnection)
            self.clientConnection.deleteLater()

class ChargePoint(cp):
    @on(Action.BootNotification)
    def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, **kwargs):
        CP=DataBase.connect(DataBase.Get_ChargePoint())
        for row in CP:
            if charge_point_vendor == row[2] and charge_point_model == row[1]:
                B=call_result.BootNotificationPayload(
                    current_time=datetime.utcnow().isoformat(),
                    interval=10,
                    status=RegistrationStatus.accepted
                )
                break
            else:
                B=call_result.BootNotificationPayload(
                    current_time=datetime.utcnow().isoformat(),
                    interval=10,
                    status=RegistrationStatus.rejected
                )
        return B

    @on(Action.StatusNotification)
    def on_status_notification(self, connector_id: int, error_code: str, status: str, timestamp:str, **kwargs):
        return call_result.StatusNotificationPayload()

    @on(Action.Authorize)
    def on_autorize(self, id_tag: str, **kwargs):
        global User
        Client = DataBase.connect(DataBase.Get_Client())
        for row in Client:
            if row[2] == id_tag:
                User = row[0]
                print('another connection')
                return call_result.AuthorizePayload(
                    id_tag_info={
                        'status': 'Accepted'
                        }
                        )
            else:
                print('Denied')
                return call_result.AuthorizePayload(
                    id_tag_info={
                        'status': 'Invalid'
                        }
                        )
            break

    @on(Action.Heartbeat)
    def on_hearbeat(self):
        print('Got a Heartbeat!')
        return call_result.HeartbeatPayload(
            current_time=datetime.utcnow().isoformat()
        )

    @on(Action.MeterValues)
    def on_meter_values(self, connector_id: int, meter_value: list, **kwargs):
        return call_result.MeterValuesPayload()

    @on(Action.StartTransaction)
    def on_start_transaction(self, connector_id: int, id_tag: str, meter_start: int, timestamp: str, **kwargs):
        idt = DataBase.connect(DataBase.Get_Trans())
        DataBase.connect(DataBase.Insert(User))
        return call_result.StartTransactionPayload(
            transaction_id=idt+1,
            id_tag_info={'status': 'Accepted'}
        )


    @on(Action.StopTransaction)
    def on_stop_transaction(self, meter_stop: int, timestamp: str, transaction_id: int, **kwargs):
        return call_result.StopTransactionPayload()



async def on_connect(websocket, path):
    try:
        requested_protocols = websocket.request_headers[
            'Sec-WebSocket-Protocol']
    except KeyError:
        logging.error(
            "Client hasn't requested any Subprotocol. Closing Connection"
        )
        return await websocket.close()
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        logging.warning('Protocols Mismatched | Expected Subprotocols: %s,'
                        ' but client supports  %s | Closing connection',
                        websocket.available_subprotocols,
                        requested_protocols)
        return await websocket.close()

    charge_point_id = path.strip('/')
    cp = ChargePoint(charge_point_id, websocket)
    await cp.start()


async def main():
    server = await websockets.serve(
        on_connect,
        '0.0.0.0',
        9000,
        subprotocols=['ocpp1.6']
    )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()

async def master():
    await main()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    serverObject = QtWebSockets.QWebSocketServer('My Socket', QtWebSockets.QWebSocketServer.NonSecureMode)
    server = MyServer(serverObject)
    serverObject.closed.connect(app.quit)
    with loop:
        loop.create_task(master())
        loop.run_forever()
    #asyncio.run(main())