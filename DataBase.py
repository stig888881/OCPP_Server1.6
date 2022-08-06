import psycopg2
from config import host, user, password, db_name

def connect(*args):
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name)
        cursor = connection.cursor()
        len=args[0]
        if isinstance(len, str):
            cursor.execute(*args)
            connection.commit()
            Client=cursor.fetchall()
            return Client
        else:
            sql= args[0]
            cursor.execute(sql[0], sql[1:])
            connection.commit()

    except (Exception, psycopg2.Error) as error:
        print("Failed inserting record into mobile table {}".format(error))

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")

def Get_Client():
    sql_insert_query = """ SELECT * FROM public."Client" """
    return sql_insert_query

def Insert():
    sql_insert_query = """ INSERT INTO public."Transaction" ("User") VALUES (%s)"""
    id = '1'
    return sql_insert_query, id

Client=connect(Get_Client())
for row in Client:
    print(row[0])
    print(row[1])
connect(Insert())

