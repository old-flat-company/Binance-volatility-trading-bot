import psycopg2

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
config_file = args.config if args.config else DEFAULT_CONFIG_FILE
parsed_config = load_config(config_file)

DB_HOST = parsed_config['db_connect_options']['DB_HOST']
DB_NAME = parsed_config['db_connect_options']['DB_NAME']
DB_USER = parsed_config['db_connect_options']['DB_USER']
DB_PASSWORD = parsed_config['db_connect_options']['DB_PASSWORD']


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


def table_script_management_read_data(conn=None):
    '''
    :param conn:  DB connection object
    :return:
    '''
    try:
        # create a cursor
        custom_cr = conn.cursor()

        # execute a statement
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


def table_script_management_write_data(conn=None, close_pairs=None, stop_script_manually=None):
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


def table_calculate_efficiency_read_data(conn=None):
    '''
    :param conn:  DB connection object
    :return:
    '''
    try:
        # create a cursor
        custom_cr = conn.cursor()
        # execute a statement
        custom_query = 'SELECT efficiency_coef, positive_set, efficiency_coef_processed_time, positive_set_processed_time FROM public.calculate_efficiency WHERE id = 1;'
        custom_cr.execute(custom_query)
        unprocessed_data_list = custom_cr.fetchall()
        efficiency_coef, positive_set, efficiency_coef_processed_time, positive_set_processed_time = unprocessed_data_list[0]
        custom_cr.close()
        return efficiency_coef, positive_set, efficiency_coef_processed_time, positive_set_processed_time
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return False, False, False, False


def table_calculate_efficiency_write_data(conn=None,
                                          efficiency_coef=None,
                                          positive_set=None,
                                          efficiency_coef_processed_time=None,
                                          positive_set_processed_time=None
                                          ):
    '''
    :param conn:  DB connection object
    :return:
    '''
    # create a cursor
    custom_cr = conn.cursor()
    try:

        if efficiency_coef is not None or positive_set is not None:
            custom_query = 'UPDATE public.calculate_efficiency SET '
            # ------efficiency_coef  block---------------------------
            if efficiency_coef:
                custom_query += 'efficiency_coef = ' + "'" + efficiency_coef + "'" + ', '

            # -----------positive_set block--------------------------
            if positive_set == False:
                custom_query += 'positive_set = false '
            elif positive_set:
                custom_query += 'positive_set = true '
            elif positive_set == None:
                custom_query = custom_query[:-2] + ' '  # without comma',' +  empty space
            # ------------------define id block----------------------
            custom_query += 'WHERE id = 1;'

            #-------custom_query  for  processed_time data ----------
            if efficiency_coef_processed_time is not None and positive_set_processed_time is not None:
                custom_query += " UPDATE public.calculate_efficiency SET efficiency_coef_processed_time = '%s', positive_set_processed_time = '%s' WHERE id = 1;" % (
                    efficiency_coef_processed_time,
                    positive_set_processed_time)

            custom_cr.execute(custom_query)

            conn.commit()
            custom_cr.close()
            return True
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        custom_cr.close()
        return False

#-------------------------------------------

def table_last_sold_pairs_data_read_data(conn=None):
    '''
    :param conn:  DB connection object
    :return:
    '''
    try:
        custom_cr = conn.cursor()
        custom_query = 'SELECT id, pair_name, last_sold_time FROM public.last_sold_pairs_data;'
        custom_cr.execute(custom_query)
        unprocessed_data_list = custom_cr.fetchall()
        custom_cr.close()
        return unprocessed_data_list
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return 'error in table_last_sold_pairs_data_read_data'


def table_last_sold_pairs_data_read_data_by_pair_name(conn=None, pair_names=[]):
    '''
    :param conn:  DB connection object
    :return:
    '''
    try:
        custom_cr = conn.cursor()
        if pair_names:
            query_pair_names = ', '.join(["'" + pair_name + "'" for pair_name in pair_names])
            custom_query = 'SELECT id, pair_name, last_sold_time FROM public.last_sold_pairs_data  WHERE  pair_name IN (%s);' % query_pair_names
            custom_cr.execute(custom_query)
            unprocessed_data_list = custom_cr.fetchall()
            custom_cr.close()
            return unprocessed_data_list
        else:
            return []
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return 'error in table_last_sold_pairs_data_read_data_by_pair_name'



def table_last_sold_pairs_data_write_new_data(conn=None,
                                              pair_name=None,
                                              last_sold_time=None
                                              ):
    '''
    :param conn:  DB connection object
    :return:
    '''
    # create a cursor
    custom_cr = conn.cursor()
    try:
        if pair_name is not None and last_sold_time is not None:
            custom_query = "INSERT INTO public.last_sold_pairs_data (pair_name, last_sold_time) VALUES ('%s', '%s');" % (
                pair_name,
                last_sold_time)
            custom_cr.execute(custom_query)
            conn.commit()
            custom_cr.close()
            return True
        else:
            return False
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        custom_cr.close()
        return False


def table_last_sold_pairs_data_del_old_data(conn=None, ids=[]):
    # create a cursor
    custom_cr = conn.cursor()
    try:
        if ids:
            query_ids_list = str(tuple(ids)) if len(ids) > 1 else str(tuple(ids))[:-2] + ')'
            custom_query = "DELETE FROM public.last_sold_pairs_data WHERE id IN " + query_ids_list + ";"
            custom_cr.execute(custom_query)
            conn.commit()
            custom_cr.close()
            return True
        else:
            return False
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        custom_cr.close()
        return False


if __name__ == '__main__':
    connect = connect()
    # print(table_script_management_read_data(conn=connect))
    # table_script_management_write_data(conn=connect, close_pairs=['test6'])

    # print(table_calculate_efficiency_read_data(conn=connect))
    # table_calculate_efficiency_write_data(conn=connect, efficiency_coef='1.9',
    #                                       positive_set=False,
    #                                       efficiency_coef_processed_time=str(2660640838.0),
    #                                       positive_set_processed_time=str(1660640838.0)
    #                                       )

    # print(table_last_sold_pairs_data_read_data(conn=connect))
    # table_last_sold_pairs_data_write_new_data(conn=connect,
    #                                           pair_name='test8_name',
    #                                           last_sold_time='test8_time')

    print(table_last_sold_pairs_data_read_data_by_pair_name(conn=connect, pair_names=['test8_name']))

    # table_last_sold_pairs_data_del_old_data(conn=connect, ids=[4, 5])
