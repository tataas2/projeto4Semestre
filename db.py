import psycopg2

# database connection

def get_connection():
    return psycopg2.connect(
        host="projeto-4-sem.cno6kgcgoyxu.us-east-2.rds.amazonaws.com",
        database="postgres",                   
        user="postgres",                        
        password="admin12345",                 
        port="5432"
    )