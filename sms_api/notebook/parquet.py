import os
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, cast, Mapping, Optional
from urllib import parse

import duckdb
import numpy as np
import polars as pl
from polars.datatypes import DataTypeClass
from fsspec.core import filesystem, url_to_fs, OpenFile  # type: ignore[import-untyped]
from fsspec.spec import AbstractFileSystem
from tqdm import tqdm
from vivarium.core.emitter import Emitter

METADATA_PREFIX = "output_metadata__"
"""
In the config dataset, user-defined metadata for each store
(see :py:meth:`~ecoli.experiments.ecoli_master_sim.EcoliSim.output_metadata`)
will be contained in columns with this prefix.
"""

USE_UINT16 = {
    "listeners__rna_synth_prob__n_bound_TF_per_TU",
    "listeners__rna_synth_prob__n_bound_TF_per_cistron",
    "listeners__rnap_data__rna_init_event_per_cistron",
    "listeners__rna_synth_prob__gene_copy_number",
    # Expected RNA init per cistron is a float64 but adds >10%
    # to final output size and is mostly redundant (equal to
    # actual_rna_synth_prob_per_cistron * total_rna_init)
    # so downcast to uint16 to save space.
    "listeners__rna_synth_prob__expected_rna_init_per_cistron",
    "listeners__rna_degradation_listener__count_RNA_degraded_per_cistron",
    "listeners__rna_degradation_listener__count_rna_degraded",
    "listeners__transcript_elongation_listener__count_rna_synthesized",
    "listeners__rnap_data__rna_init_event",
    "listeners__rna_synth_prob__promoter_copy_number",
    "listeners__ribosome_data__n_ribosomes_on_each_mRNA",
    "listeners__ribosome_data__mRNA_TU_index",
    "listeners__complexation_listener__complexation_events",
    "listeners__rnap_data__active_rnap_n_bound_ribosomes",
    "listeners__rnap_data__active_rnap_domain_indexes",
    "listeners__rna_synth_prob__bound_TF_indexes",
    "listeners__rna_synth_prob__bound_TF_domains",
}
"""uint16 is 4x smaller than int64 for values between 0 - 65,535."""

USE_UINT32 = {
    "listeners__ribosome_data__ribosome_init_event_per_monomer",
    "listeners__ribosome_data__n_ribosomes_per_transcript",
    "listeners__rna_counts__partial_mRNA_cistron_counts",
    "listeners__rna_counts__mRNA_cistron_counts",
    "listeners__rna_counts__full_mRNA_cistron_counts",
    "listeners__ribosome_data__n_ribosomes_on_partial_mRNA_per_transcript",
    "listeners__monomer_counts",
    "listeners__rna_counts__partial_mRNA_counts",
    "listeners__rna_counts__mRNA_counts",
    "listeners__rna_counts__full_mRNA_counts",
    "listeners__fba_results__catalyst_counts",
}
"""uint32 is 2x smaller than int64 for values between 0 - 4,294,967,295."""


def json_to_parquet(
    emit_dict: dict[str, np.ndarray | list[pl.Series]],
    outfile: str,
    schema: dict[str, Any],
    filesystem: AbstractFileSystem,
) -> None:
    """Convert dictionary to Parquet.

    Args:
        emit_dict: Mapping from column names to NumPy arrays (fixed-shape)
            or lists of Polars Series (variable-shape).
        outfile: Path to output Parquet file. Can be local path or URI.
        schema: Full mapping of column names to Polars dtypes.
        filesystem: On local filesystem, fsspec filesystem needed to
            write Parquet file atomically.
    """
    tbl = pl.DataFrame(emit_dict, schema={k: schema[k] for k in emit_dict})
    # GCS should have atomic uploads, but on a local filesystem, DuckDB may fail
    # trying to read partially written Parquet files. Get around this by writing
    # to a temporary file and then renaming it to the final output file.
    temp_outfile = outfile
    if parse.urlparse(outfile).scheme in ("", "file", "local"):
        temp_outfile = outfile + ".tmp"
    tbl.write_parquet(temp_outfile, statistics=False)
    if temp_outfile != outfile:
        filesystem.mv(temp_outfile, outfile)


def union_by_name(query_sql: str) -> str:
    """
    Modifies SQL query string from :py:func:`~.dataset_sql` to
    include ``union_by_name = true`` in the DuckDB ``read_parquet``
    function. This allows data to be read from simulations that have
    different columns by filling in nulls and casting as necessary.
    This comes with a performance penalty and should be avoided if possible.

    Args:
        query_sql: SQL query string from :py:func:`~.dataset_sql`
    """
    return query_sql.replace("hive_partitioning = true,", "hive_partitioning = true, union_by_name = true,")


def create_duckdb_conn(
    temp_dir: str = "/tmp", gcs: bool = False, cpus: Optional[int] = None
) -> duckdb.DuckDBPyConnection:
    """
    Create a DuckDB connection.

    Args:
        temp_dir: Temporary directory for spilling to disk.
        gcs: Set to True if reading from Google Cloud Storage.
        cpus: Number of cores to use (by default, use all detected cores).
    """
    conn = duckdb.connect()
    if gcs:
        conn.register_filesystem(filesystem("gcs"))
    # Temp directory so DuckDB can spill to disk when data larger than RAM
    conn.execute(f"SET temp_directory = '{temp_dir}'")
    # Turning this off reduces RAM usage
    conn.execute("SET preserve_insertion_order = false")
    # Cache Parquet metadata so only needs to be scanned once
    conn.execute("SET enable_object_cache = true")
    # Set number of threads for DuckDB
    if cpus is not None:
        conn.execute(f"SET threads = {cpus}")
    return conn


def dataset_sql(out_dir: str, experiment_ids: list[str]) -> tuple[str, str, str]:
    """
    Creates DuckDB SQL strings for sim outputs, configs, and metadata on which
    sims were successful.

    Args:
        out_dir: Path to output directory for workflows to retrieve data
            for (relative or absolute local path OR URI beginning with
            ``gcs://`` or ``gs://`` for Google Cloud Storage bucket)
        experiment_ids: List of experiment IDs to include in query. To read data
            from more than one experiment ID, the listeners in the output of the
            first experiment ID in the list must be a strict subset of the listeners
            in the output of the subsequent experiment ID(s).

    Returns:
        3-element tuple containing

        - **history_sql**: SQL query for sim output (see :py:func:`~.read_stacked_columns`),
        - **config_sql**: SQL query for sim configs (see :py:func:`~.field_metadata`
          and :py:func:`~.config_value`)
        - **success_sql**: SQL query for metadata marking successful sims
          (see :py:func:`~.read_stacked_columns`)

    """
    sql_queries = []
    for query_type in ("history", "configuration", "success"):
        query_files = []
        for experiment_id in experiment_ids:
            query_files.append(f"'{os.path.join(out_dir, experiment_id)}/{query_type}/*/*/*/*/*/*.pq'")
        query_files = ", ".join(query_files)
        sql_queries.append(
            f"""
            FROM read_parquet(
                [{query_files}],
                hive_partitioning = true,
                hive_types = {{
                    'experiment_id': VARCHAR,
                    'variant': BIGINT,
                    'lineage_seed': BIGINT,
                    'generation': BIGINT,
                    'agent_id': VARCHAR,
                }}
            )
            """
        )
    return sql_queries[0], sql_queries[1], sql_queries[2]


def num_cells(conn: duckdb.DuckDBPyConnection, subquery: str) -> int:
    """
    Return cell count in DuckDB subquery containing ``experiment_id``,
    ``variant``, ``lineage_seed``, ``generation``, and ``agent_id`` columns.
    """
    return cast(
        tuple,
        conn.sql(f"""SELECT count(
        DISTINCT (experiment_id, variant, lineage_seed, generation, agent_id)
        ) FROM ({subquery})""").fetchone(),
    )[0]


def skip_n_gens(subquery: str, n: int) -> str:
    """
    Modifies a DuckDB SQL query to skip the first ``n`` generations of data.
    """
    return f"SELECT * FROM ({subquery}) WHERE generation >= {n}"


def ndlist_to_ndarray(s) -> np.ndarray:
    """
    Convert a PyArrow series of nested lists with fixed dimensions into
    a Numpy ndarray. This should really only be necessary if you are trying
    to perform linear algebra (e.g. matrix multiplication, dot products) inside
    a user-defined function (see DuckDB documentation on Python Function API and
    ``func`` kwarg for :py:func:`~read_stacked_columns`).

    For elementwise arithmetic of two nested list columns, this can be used
    to define a custom DuckDB function as follows::

        import duckdb
        import polars as pl
        from ecoli.library.parquet_emitter import ndlist_to_ndarray
        def sum_arrays(col_0, col_1):
            return pl.Series(
                ndlist_to_ndarray(col_0) +
                ndlist_to_ndarray(col_1)
            ).to_arrow()
        conn = duckdb.connect()
        conn.create_function(
            "sum_2d_int_arrays", # Function name for use in SQL (must be unique)
            sum_arrays, # Python function that takes and returns PyArrow arrays
            [list[list[int]], list[list[int]]], # Input types (2D lists here)
            list[list[int]], # Return type (2D list here)
            type = "arrow" # Tell DuckDB function operates on Arrow arrays
        )
        conn.sql("SELECT sum_2d_int_arrays(int_col_0, int_col_1) from input_table")
        # Note that function must be registered under different name for each
        # set of unique input/output types
        conn.create_function(
            "sum_2d_int_and_float",
            sum_arrays,
            [list[list[int]], list[list[float]]], # Second input is 2D float array
            list[list[float]], # Adding int to float array gives float in Numpy
            type = "arrow"
        )
        conn.sql("SELECT sum_2d_int_and_float(int_col_0, float_col_0) from input_table")

    """
    inner_s = pl.Series(s)
    dimensions = []
    while inner_s.dtype.is_nested() and len(inner_s) > 0:
        inner_s = inner_s[0]
        dimensions.append(len(inner_s))
    inner_s = inner_s.dtype
    while inner_s.is_nested():
        inner_s = inner_s.inner  # type: ignore[attr-defined]
        dimensions.append(0)
    return pl.Series(s, dtype=pl.Array(inner_s, tuple(dimensions))).to_numpy()


def ndidx_to_duckdb_expr(name: str, idx: list[int | list[int] | list[bool] | str]) -> str:
    """
    Returns a DuckDB expression for a column equivalent to converting each row
    of ``name`` into an ndarray ``name_arr`` (:py:func:`~.ndlist_to_ndarray`)
    and getting ``name_arr[idx]``. ``idx`` can contain 1D lists of integers,
    boolean masks, or ``":"`` (no 2D+ indices like ``x[[[1,2]]]``). See also
    :py:func:`~named_idx` if pulling out a relatively small set of indices.
    Automatically quotes column names to handle special characters. Do NOT
    use double quotes in ``name``.

    .. WARNING:: DuckDB arrays are 1-indexed so this function adds 1 to every
        supplied integer index!

    Args:
        name: Name of column to recursively index
        idx: To get all elements for a dimension, supply the string ``":"``.
            Otherwise, only single integers or 1D integer lists of indices are
            allowed for each dimension. Some examples::

                [0, 1] # First row, second column
                [[0, 1], 1] # First and second row, second column
                [0, 1, ":"] # First element of axis 1, second of 2, all of 3
                # Final example differs between this function and Numpy
                # This func: 1st and 2nd of axis 1, all of 2, 1st and 2nd of 3
                # Numpy: Complicated, see Numpy docs on advanced indexing
                [[0, 1], ":", [0, 1]]

    """
    quoted_name = f'"{name}"'
    idx = idx.copy()
    idx.reverse()
    # Construct expression from inside out (deepest to shallowest axis)
    first_idx = idx.pop(0)
    if isinstance(first_idx, list):
        # Python bools are instances of int so check bool first
        if isinstance(first_idx[0], bool):
            select_expr = f"list_where(x_0, {first_idx})"
        elif isinstance(first_idx[0], int):
            one_indexed_idx = ", ".join(str(i + 1) for i in first_idx)
            select_expr = f"list_select(x_0, [{one_indexed_idx}])"
        else:
            raise TypeError("Indices must be integers or boolean masks.")
    elif first_idx == ":":
        select_expr = "x_0"
    elif isinstance(first_idx, int):
        select_expr = f"list_select(x_0, [{int(first_idx) + 1}])"
    else:
        raise TypeError("All indices must be lists, ints, or ':'.")
    i = -1
    for i, indices in enumerate(idx):
        if isinstance(indices, list):
            if isinstance(indices[0], bool):
                select_expr = f"list_transform(list_where(x_{i + 1}, {indices}), lambda x_{i} : {select_expr})"
            elif isinstance(indices[0], int):
                one_indexed_idx = ", ".join(str(i + 1) for i in indices)
                select_expr = (
                    f"list_transform(list_select(x_{i + 1}, [{one_indexed_idx}]), lambda x_{i} : {select_expr})"
                )
            else:
                raise TypeError("Indices must be integers or boolean masks.")
        elif indices == ":":
            select_expr = f"list_transform(x_{i + 1}, lambda x_{i} : {select_expr})"
        elif isinstance(indices, int):
            select_expr = f"list_transform(list_select(x_{i + 1}, [{int(indices) + 1}]), lambda x_{i} : {select_expr})"
        else:
            raise TypeError("All indices must be lists, ints, or ':'.")
    select_expr = select_expr.replace(f"x_{i + 1}", quoted_name)
    return select_expr + f" AS {quoted_name}"


def named_idx(
    col: str,
    names: list[str],
    idx: list[list[int]],
    zero_to_null: bool = False,
    _quote_col: bool = True,
) -> str:
    """
    Create DuckDB expressions for given indices from a list column. Can be
    used in ``projection`` kwarg of :py:func:`~.read_stacked_columns`. Since
    each index gets pulled out into its own column, this greatly simplifies
    aggregations like averages, etc. Only use this if the number of indices
    is relatively small (<100) and the list column is 1-dimensional. For 2+
    dimensions or >100 indices, see :py:func:`~.ndidx_to_duckdb_expr`.
    Automatically quotes column names to handle special characters.
    Do NOT use double quotes in ``names`` or ``col``.

    .. WARNING:: DuckDB arrays are 1-indexed so this function adds 1 to every
        supplied index!

    Args:
        col: Name of list column.
        names: List of names for the new columns. Length must match the
            number of index combinations in ``idx`` (4 for example below).
        idx: Integer indices to retrieve from each dimension of ``col``.
            For example, ``[[0, 1], [2, 3]]`` will retrieve the third and
            fourth elements of the second dimension for the first and second
            elements of the first dimension.
        zero_to_null: Whether to turn 0s into nulls. This is useful when
            dividing by the values in this column, as most DuckDB aggregation
            functions (e.g. ``avg``, ``max``) propagate NaNs but ignore nulls.
        _quote_col: Private argument to ensure ``col`` is quoted properly.

    Returns:
        DuckDB SQL expression for a set of named columns corresponding to
        the values at given indices of a list column
    """
    assert isinstance(idx[0], list), "idx must be a list of lists."
    # Quote column name on initial call
    if _quote_col:
        col = f'"{col}"'
    col_exprs = []
    if len(idx) == 1:
        for num, i in enumerate(idx[0]):
            quoted_name = f'"{names[num]}"'
            if zero_to_null:
                col_exprs.append(f"CASE WHEN {col}[{i + 1}] = 0 THEN NULL ELSE {col}[{i + 1}] END AS {quoted_name}")
            else:
                col_exprs.append(f"{col}[{i + 1}] AS {quoted_name}")
    else:
        col_counter = 0
        for i in idx[0]:
            sub_col_exprs = named_idx(
                f"{col}[{i + 1}]",
                names[col_counter:],
                idx[1:],
                zero_to_null,
                _quote_col=False,
            )
            col_counter += sub_col_exprs.count(", ") + 1
            col_exprs.append(sub_col_exprs)
    return ", ".join(col_exprs)


def field_metadata(conn: duckdb.DuckDBPyConnection, config_subquery: str, field: str) -> list:
    """
    Gets the saved metadata (see
    :py:meth:`~ecoli.experiments.ecoli_master_sim.EcoliSim.output_metadata`)
    for a given field as a list. Automatically quotes the field name to
    handle special characters. Do NOT use double quotes in ``field``.

    Args:
        conn: DuckDB connection
        config_subquery: DuckDB query containing sim config data
        field: Name of field to get metadata for
    """
    metadata = cast(
        tuple,
        conn.sql(f'SELECT first("{METADATA_PREFIX + field}") FROM ({config_subquery})').fetchone(),
    )[0]
    if isinstance(metadata, list):
        return metadata
    return list(metadata)


def config_value(conn: duckdb.DuckDBPyConnection, config_subquery: str, field: str) -> Any:
    """
    Gets the saved configuration option (anything in config JSON, with
    double underscore concatenation for nested fields due to
    :py:func:`~.flatten_dict`). Automatically quotes the field name to
    handle special characters. Do NOT use double quotes in ``field``.

    Args:
        conn: DuckDB connection
        config_subquery: DuckDB query containing sim config data
        field: Name of configuration option to get value of
    """
    return cast(
        tuple,
        conn.sql(f'SELECT first("{field}") FROM ({config_subquery})').fetchone(),
    )[0]


def plot_metadata(conn: duckdb.DuckDBPyConnection, config_subquery: str, variant_name: str) -> dict[str, Any]:
    """
    Gets dictionary that can be used as ``metadata`` kwarg to
    :py:func:`wholecell.utils.plotting_tools.export_figure`.

    Args:
        conn: DuckDB connection
        config_subquery: DuckDB query containing sim config data
        variant_name: Name of variant
    """
    return {
        "git_hash": config_value(conn, config_subquery, "git_hash"),
        "time": config_value(conn, config_subquery, "time"),
        "description": config_value(conn, config_subquery, "description"),
        "variant_function": variant_name,
        "variant_index": conn.sql(f"SELECT DISTINCT variant FROM ({config_subquery})").arrow().to_pydict()["variant"],
        "seed": conn.sql(f"SELECT DISTINCT lineage_seed FROM ({config_subquery})").arrow().to_pydict()["lineage_seed"],
        "total_gens": cast(
            tuple,
            conn.sql(f"SELECT count(DISTINCT generation) FROM ({config_subquery})").fetchone(),
        )[0],
        "total_variants": cast(
            tuple,
            conn.sql(f"SELECT count(DISTINCT variant) FROM ({config_subquery})").fetchone(),
        )[0],
    }


def open_output_file(outfile: str) -> OpenFile:
    """
    Open a file by its path, whether that be a path on local storage or
    Google Cloud Storage.

    Args:
        outfile: Path to file. Must have ``gs://`` or ``gcs://`` prefix if
            on Google Cloud Storage. Can be relative or absolute path if
            on local storage.

    Returns:
        File object that supports reading, seeking, etc. in bytes
    """
    return url_to_fs(outfile)[0].open(outfile)


def open_arbitrary_sim_data(sim_data_dict: dict[str, dict[int, Any]]) -> OpenFile:
    """
    Given a mapping from experiment ID(s) to mappings from variant ID(s)
    to sim_data path(s), pick an arbitrary sim_data to read.

    Args:
        sim_data_dict: Generated by :py:mod:`runscripts.analysis` and passed to
            each analysis script as an argument.

    Returns:
        File object for arbitrarily chosen sim_data to be loaded
        with ``pickle.load``
    """
    sim_data_path = next(iter(next(iter(sim_data_dict.values())).values()))
    return open_output_file(sim_data_path)


def read_stacked_columns(
    history_sql: str,
    columns: list[str],
    remove_first: bool = False,
    func: Optional[Callable[[pl.DataFrame], pl.DataFrame]] = None,
    conn: Optional[duckdb.DuckDBPyConnection] = None,
    order_results: bool = True,
    success_sql: Optional[str] = None,
) -> pl.DataFrame | str:
    """
    Loads columns for many cells. If you would like to perform more advanced
    computatations (aggregations, window functions, etc.) using the optimized
    DuckDB API, you can omit ``conn``, in which case this function will return
    an SQL string that can be used as a subquery. For computations that cannot
    be easily performed using the DuckDB API, you can define a custom function
    ``func`` that will be called on the data for each cell. By default, the
    return value (whether it be the actual data or an SQL subquery) will
    also include the ``experiment_id``, ``variant``, ``lineage_seed``,
    ``generation``, ``agent_id``, and ``time`` columns.

    .. warning:: If the column expressions in ``columns`` are not from
        :py:func:`~named_idx` or :py:func:`~ndidx_to_duckdb_expr`,
        they may need to be enclosed in double quotes to handle
        special characters (e.g. ``"col-with-hyphens"``).

    For example, to get the average total concentration of three bulk molecules
    with indices 100, 1000, and 10000 per cell::

        import duckdb
        from ecoli.library.parquet_emitter import (
            dataset_sql, read_stacked_columns)
        history_sql, config_sql, _ = dataset_sql('out/', 'exp_id')
        subquery = read_stacked_columns(
            history_sql,
            # Note DuckDB arrays are 1-indexed
            ["bulk[100 + 1] + bulk[1000 + 1] + bulk[10000 + 1] AS bulk_sum",
            "listeners__enzyme_kinetics__counts_to_molar AS counts_to_molar"],
            order_results=False,
        )
        query = '''
            SELECT avg(bulk_sum * counts_to_molar) AS avg_total_conc
            FROM ({subquery})
            GROUP BY experiment_id, variant, lineage_seed, generation, agent_id
            '''
        conn = duckdb.connect()
        data = conn.sql(query).pl()

    Here is a more complicated example that defines a custom function to get
    the per-cell average RNA synthesis probability per cistron::

        import duckdb
        import pickle
        from ecoli.library.parquet_emitter import (
            dataset_sql, ndlist_to_ndarray, read_stacked_columns)
        history_sql, config_sql, _ = dataset_sql('out/', 'exp_id')
        # Load sim data
        with open("reconstruction/sim_data/kb/simData.cPickle", "rb") as f:
            sim_data = pickle.load(f)
        # Get mapping from RNAs (TUs) to cistrons
        cistron_tu_mat = sim_data.process.transcription.cistron_tu_mapping_matrix
        # Custom aggregation function with Numpy dot product and mean
        def avg_rna_synth_prob_per_cistron(rna_synth_prob):
            # Convert rna_synth_prob into 2-D Numpy array (time x TU)
            rna_synth_prob = ndlist_to_ndarray(rna_synth_prob[
                "listeners__rna_synth_prob__actual_rna_synth_prob"])
            rna_synth_prob_per_cistron = cistron_tu_mat.dot(rna_synth_prob.T).T
            # Return value must be a PyArrow table
            return pl.DataFrame({'avg_rna_synth_prob_per_cistron': [
                rna_synth_prob_per_cistron.mean(axis=0)]}).to_arrow()
        conn = duckdb.connect()
        result = read_stacked_columns(
            history_sql,
            ["listeners__rna_synth_prob__actual_rna_synth_prob"],
            func=avg_rna_synth_prob_per_cistron,
            conn=conn,
        )

    Args:
        history_sql: DuckDB SQL string from :py:func:`~.dataset_sql`,
            potentially with filters appended in ``WHERE`` clause
        columns: Names of columns to read data for. Alternatively, DuckDB
            expressions of columns (e.g. ``avg(listeners__mass__cell_mass) AS avg_mass``
            or the output of :py:func:`~.named_idx` or :py:func:`~.ndidx_to_duckdb_expr`).
        remove_first: Remove data for first timestep of each cell
        func: Function to call on data for each cell, should take and
            return a Polars DataFrame with columns equal to ``columns``
        conn: DuckDB connection instance with which to run query. Typically
            provided by :py:func:`runscripts.analysis.main` to the ``plot``
            method of analysis scripts (tweaked some DuckDB settings). Can
            be omitted to return SQL query string to be used as subquery
            instead of running query immediately and returning result.
        order_results: Whether to sort returned table by ``experiment_id``,
            ``variant``, ``lineage_seed``, ``generation``, ``agent_id``, and
            ``time``. If no ``conn`` is provided, this can usually be disabled
            and any sorting can be deferred until the last step in the query with
            a manual ``ORDER BY``. Doing this can greatly reduce RAM usage.
        success_sql: Final DuckDB SQL string from :py:func:`~.dataset_sql`.
            If provided, will be used to filter out unsuccessful sims.
    """
    id_cols = "experiment_id, variant, lineage_seed, generation, agent_id, time"
    columns_str = ", ".join(columns)
    sql_query = f"SELECT {columns_str}, {id_cols} FROM ({history_sql})"
    # Use a semi join to filter out unsuccessful sims
    if success_sql is not None:
        sql_query = f"""
            SELECT * FROM ({sql_query})
            SEMI JOIN ({success_sql})
            USING (experiment_id, variant, lineage_seed, generation, agent_id)
            """
    # Use an anti join to remove rows for first timestep of each sim
    if remove_first:
        sql_query = f"""
            SELECT * FROM ({sql_query})
            ANTI JOIN (
                SELECT experiment_id, variant, lineage_seed, generation,
                    agent_id, MIN(time) AS time
                FROM ({history_sql.replace("COLNAMEHERE", "time")})
                GROUP BY experiment_id, variant, lineage_seed, generation,
                    agent_id
            ) USING (experiment_id, variant, lineage_seed, generation,
                agent_id, time)
            """
    if func is not None:
        if conn is None:
            raise RuntimeError("`conn` must be provided with `func`.")
        # Get all cell identifiers
        cell_ids = conn.sql(f"""SELECT DISTINCT ON(experiment_id, variant,
            lineage_seed, generation, agent_id) experiment_id, variant,
            lineage_seed, generation, agent_id FROM ({history_sql}) ORDER BY {id_cols}
        """).fetchall()
        all_cell_tbls = []
        for experiment_id, variant, lineage_seed, generation, agent_id in tqdm(cell_ids):
            # Explicitly specify Hive partition because DuckDB
            # will otherwise spend a lot of time scanning all files
            cell_sql = sql_query.replace(
                "history/*/*/*/*/*",
                f"history/experiment_id={experiment_id}/variant={variant}/lineage_seed={lineage_seed}/generation={generation}/agent_id={agent_id}",
            )
            # Apply func to data for each cell
            all_cell_tbls.append(func(conn.sql(cell_sql).pl()))
        return pl.concat(all_cell_tbls)
    if order_results:
        query = f"SELECT * FROM ({sql_query}) ORDER BY {id_cols}"
    else:
        query = sql_query
    if conn is None:
        return query
    return conn.sql(query).pl()


def np_dtype(val: Any, field_name: str) -> Any:
    """
    Get NumPy type for input value. There are a few scenarios
    where this function raises an exception intentionally:

    - An internal value is None or an empty list/tuple: data is
      ragged/nullable and needs Polars serialization.
    - Python bytes type: NumPy only has fixed-length bytes type
      so use Polars serialization to avoid truncation.
    - Python datetime types: Simpler and less error-prone to use
      Polars serialization instead of converting to NumPy.

    .. warning::
        ``np.bytes_`` values and arrays will get truncated to the
        size of the first encountered value. Convert to Python
        bytes type to avoid this.

    The ``try...except`` blocks in :py:meth:`~.ParquetEmitter.emit`
    are designed to catch these exceptions and fall back to
    Polars serialization.

    All other exceptions raised by this function indicate that the
    value is of an unsupported type for which even the fall back
    Polars serialization likely will not work.
    """
    if field_name in USE_UINT16:
        return np.uint16
    elif field_name in USE_UINT32:
        return np.uint32
    elif isinstance(val, float):
        return np.float64
    elif isinstance(val, bool):
        return np.bool_
    elif isinstance(val, int):
        return np.int64
    # Use NumPy variable-length string type
    elif isinstance(val, (str, np.str_)):
        return np.dtypes.StringDType
    elif isinstance(val, np.generic):
        return val.dtype
    elif isinstance(val, np.ndarray):
        return val.dtype
    elif isinstance(val, (list, tuple)):
        if len(val) > 0:
            for inner_val in val:
                if inner_val is not None:
                    return np_dtype(inner_val, field_name)
    raise ValueError(f"{field_name} has unsupported type {type(val)}.")


def union_pl_dtypes(
    dt1: pl.DataType | DataTypeClass,
    dt2: pl.DataType | DataTypeClass,
    k: str,
    force_inner: Optional[pl.DataType | DataTypeClass] = None,
) -> pl.DataType | DataTypeClass:
    """
    Returns the more specific data type when combining two Polars datatypes.
    Mainly intended to fill out nested List types that contain Nulls.

    Args:
        dt1: First Polars datatype
        dt2: Second Polars datatype
        k: Name of column being combined (for error messages)
        force_inner: Force this inner type when possible

    Returns:
        The resulting datatype
    """
    if isinstance(dt1, (pl.List, pl.Array)) and isinstance(dt2, (pl.List, pl.Array)):
        # Recursively find the common type for inner elements
        inner_type = union_pl_dtypes(dt1.inner, dt2.inner, k, force_inner)
        return pl.List(inner_type)

    if dt1 == pl.Null:
        # To force a specific inner type, may need to recurse
        if force_inner is not None:
            if isinstance(dt2, (pl.List, pl.Array)):
                return pl.List(union_pl_dtypes(dt2.inner, dt2.inner, k, force_inner))
            return force_inner
        return dt2
    if dt2 == pl.Null:
        if force_inner is not None:
            if isinstance(dt1, (pl.List, pl.Array)):
                return pl.List(union_pl_dtypes(dt1.inner, dt1.inner, k, force_inner))
            return force_inner
        return dt1

    if force_inner is not None:
        return force_inner

    if dt1 == dt2:
        return dt1

    raise TypeError(
        f"Incompatible inner types for field {k}: {dt1} and {dt2}."
        " Please modify the store value to contain a consistent type."
    )


_FLAG_FIRST = object()


def flatten_dict(d: dict):
    """
    Flatten nested dictionary down to key-value pairs where each key
    concatenates all the keys needed to reach the corresponding value
    in the input. Allows each leaf field in a nested emit to be turned
    into a column in a Parquet file for efficient storage and retrieval.
    """
    results: list[tuple[str, Any]] = []

    def visit_key(subdict, results, partialKey):
        for k, v in subdict.items():
            newKey = k if partialKey == _FLAG_FIRST else f"{partialKey}__{k}"
            if isinstance(v, Mapping):
                visit_key(v, results, newKey)
            else:
                results.append((newKey, v))

    visit_key(d, results, _FLAG_FIRST)
    return dict(results)


def pl_dtype_from_ndarray(arr: np.ndarray) -> pl.DataType:
    """
    Get Polars data type for a Numpy array, including nested lists.
    """
    # Must be size 1 in order for np.dtypes.StringDType to
    # convert to Polars String type
    pl_dtype = pl.Series(np.empty(1, dtype=arr.dtype)).dtype
    for _ in range(arr.ndim):
        pl_dtype = pl.List(pl_dtype)
    return pl_dtype
