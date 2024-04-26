import argparse
import os
import shutil

import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# standalone script to clear out corpora. Run standalone directly from the helper/ directory
# ex: python clear_corpus --keep corpus1,corpus1 | python clear_corpus --remove corpus1,corpus2


def check_db_exists(host, port, user, password, db_name):
    "check if a database exists"
    conn = psycopg2.connect(
        f"host={host} port={port} dbname=postgres user={user} password={password}"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute(sql.SQL("SELECT datname FROM pg_database WHERE datistemplate = false;"))
    dbs = cur.fetchall()

    result = db_name in [x[0] for x in dbs]

    cur.close()
    conn.close()

    return result


def parse_list(arg):
    return arg.split(",")


def clear_corpus(keep=[], remove=[]):
    "clear out corpora from metadata/corpora_list.csv, corpora/ directory, and the vector_db table"
    corpora_list = pd.read_csv("../metadata/corpora_list.csv")
    db_info = pd.read_csv("../metadata/db_creds.csv")

    # which corpora to remove
    if len(keep) > 0:
        remove_list = [x for x in corpora_list.name if x not in keep]
    else:
        remove_list = remove

    # remove it from the corpora list csv
    corpora_list.loc[lambda x: ~x.name.isin(remove_list), :].reset_index(
        drop=True
    ).to_csv("../metadata/corpora_list.csv", index=False)

    for removal in remove_list:
        # remove the files from the corpora/ directory
        os.remove(f"../corpora/metadata_{removal}.csv")
        shutil.rmtree(f"../corpora/{removal}/")

        # delete the table from the master vector_db
        if check_db_exists(
            user=db_info.loc[0, "user"],
            password=db_info.loc[0, "password"],
            db_name="vector_db",
        ):
            # establish connection
            conn = psycopg2.connect(
                f"""host={db_info.loc[lambda x: x.field == "host", "value"].values[0]} port={db_info.loc[lambda x: x.field == "port", "value"].values[0]} dbname={db_info.loc[lambda x: x.field == "master_db_name", "value"].values[0]} user={db_info.loc[lambda x: x.field == "user", "value"].values[0]} password={db_info.loc[lambda x: x.field == "password", "value"].values[0]}"""
            )

            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()

            # drop target database if it already exists
            cur.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(f"data_{removal}")
                )
            )
            conn.commit()

            cur.close()
            conn.close()


parser = argparse.ArgumentParser()
parser.add_argument("--remove", type=parse_list)
parser.add_argument("--keep", type=parse_list)

args = parser.parse_args()

if args.keep is None:
    keep = []
else:
    keep = args.keep

if args.remove is None:
    remove = []
else:
    remove = args.remove

clear_corpus(keep=keep, remove=remove)
