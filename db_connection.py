import psycopg2

DB_HOST = 'localhost'
DB_NAME = 'binance_mooning'
DB_USER = 'nikita'
DB_PASSWORD = '1000g0001'


def connect():
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')

        conn = psycopg2.connect(host=DB_HOST,
                                dbname=DB_NAME,
                                user=DB_USER,
                                password=DB_PASSWORD
                                )
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        return False


def read_table_data(conn=None):
    '''
    :param conn:  DB connection object
    :return:
    '''
    try:
        # create a cursor
        custom_cr = conn.cursor()

        # execute a statement
        # custom_query = "INSERT ... "
        # custom_query = 'SELECT id,upload_audio, upload_text,DATE(date_posted) AS date_posted,out_file_name FROM public.blog_post WHERE length(out_file_name) = 0 ORDER BY date_posted;'
        custom_query = 'SELECT close_pairs, stop_script_manually FROM public.script_management WHERE id = 1;'
        custom_cr.execute(custom_query)
        unprocessed_data_list = custom_cr.fetchall()
        out_list = []
        for unprocessed_data in unprocessed_data_list:
            close_pairs, stop_script_manually = unprocessed_data
        close_pairs = close_pairs.strip().split(';')
        custom_cr.close()
        return close_pairs, stop_script_manually
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return False


def write_data_in_table(conn=None, close_pairs=None, stop_script_manually=None):
    '''
    :param conn:  DB connection object
    :return:
    '''
    # create a cursor
    custom_cr = conn.cursor()
    try:
        # custom_cr.execute("""UPDATE public.blog_post SET out_file_name = %s WHERE id = %s""",
        #                   (output_local_audio_file_name, post_id))
        # -----------

        if close_pairs is not None or stop_script_manually is not None:
            custom_query = 'UPDATE public.script_management SET '
            # ------close_pairs  block---------------------------
            if close_pairs:
                custom_query += 'close_pairs = ' + "'" + ';'.join(close_pairs) + "'" + ', '

            # -----------stop_script_manually  block-----------
            if stop_script_manually == False:
                custom_query += 'stop_script_manually = false '
            elif stop_script_manually:
                custom_query += 'stop_script_manually = true '
            elif stop_script_manually == None:
                custom_query = custom_query[:-2] + ' '  # without comma',' +  empty space
            # ------------------define id block-----------------
            custom_query += 'WHERE id = 1;'
            custom_cr.execute(custom_query)

            conn.commit()
            custom_cr.close()
            return True
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        custom_cr.close()
        return False


if __name__ == '__main__':
    connect = connect()
    print(read_table_data(conn=connect))
    write_data_in_table(conn=connect, close_pairs=['test6'])
