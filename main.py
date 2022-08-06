import asyncio
import logging
import psycopg2
from config import host, user, password, db_name
from datetime import datetime
from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import Action, RegistrationStatus
from ocpp.v16 import call_result

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys
    sys.exit(1)

def Get_Client():
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name)
        cursor = connection.cursor()
        sql_insert_query = """ SELECT * FROM public."Client" """

        cursor.execute(sql_insert_query)
        connection.commit()
        print(cursor.rowcount, "Record inserted successfully into mobile table")

        Tag = cursor.fetchall()
        return Tag
    except (Exception, psycopg2.Error) as error:
        print("Failed inserting record into mobile table {}".format(error))

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")

def Insert(id):
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name)
        cursor = connection.cursor()
        sql_insert_query = """ INSERT INTO public."Transaction" ("User") VALUES (%s)"""

        cursor.execute(sql_insert_query, id)
        connection.commit()
        print(cursor.rowcount, "Record inserted successfully into mobile table")

    except (Exception, psycopg2.Error) as error:
        print("Failed inserting record into mobile table {}".format(error))

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")

def Update_trans():
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name)
        cursor = connection.cursor()
        sql_insert_query = """ SELECT id FROM public."Transaction" ORDER BY id DESC LIMIT 1"""

        cursor.execute(sql_insert_query)
        connection.commit()
        print(cursor.rowcount, "Update done")

        Transaction = cursor.fetchone()
        idT = Transaction[0]
        return idT

    except (Exception, psycopg2.Error) as error:
        print("Failed inserting record into mobile table {}".format(error))

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")

logging.basicConfig(level=logging.INFO)

User = 0

class ChargePoint(cp):
    @on(Action.BootNotification)
    def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, **kwargs):
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatus.accepted
        )
    @on(Action.StatusNotification)
    def on_status_notification(self, connector_id: int, error_code: str, status: str, timestamp:str, **kwargs):
        return call_result.StatusNotificationPayload()

    @on(Action.Authorize)
    def on_autorize(self, id_tag: str, **kwargs):
        global User
        Client = Get_Client()
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
        idt = Update_trans()
        Insert([User])
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

if __name__ == "__main__":
    asyncio.run(main())