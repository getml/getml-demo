from pathlib import Path

import getml


def load_or_query(conn, name):
    """
    Loads the data from disk (the project folder) if present, if not, queries it from
    the database associated with `conn`.
    """

    if not getml.data.exists(name):
        print(f"Querying {name!r} from {conn.dbname!r}...")
        df = getml.DataFrame.from_db(name=name, table_name=name, conn=conn)
        df.save()
    else:
        print(f"Loading {name!r} from disk (project folder).")
        df = getml.data.load_data_frame(name)

    return df


def load_or_retrieve(csv_file, name=None):
    """
    Loads the data from disk (the project folder) if present, if not, retrieves it from
    `csv_file`.

    If no name is supplied, the df's name is inferred from the filename.
    """

    if name is None:
        name = Path(csv_file).stem

    if not getml.data.exists(name):
        df = getml.DataFrame.from_csv(fnames=csv_file, name=name)
        df.save()
    else:
        print(f"Loading {name!r} from disk (project folder).")
        df = getml.data.load_data_frame(name)

    return df
