import numbers
import pprint
from copy import deepcopy
from typing import Iterable, List, Optional, Union

import numpy as np
from bw2data import Database, databases

from ..errors import StrategyError
from ..units import normalize_units as normalize_units_function
from ..utils import DEFAULT_FIELDS, activity_hash


def format_nonunique_key_error(obj: dict, fields: List[str], others: List[dict]):
    """
    Generate a formatted error message for a dataset that can't be uniquely linked to the target
    database.

    Parameters
    ----------
    obj : dict
        The problematic dataset that can't be uniquely linked to the target database.
    fields : list
        The list of fields to include in the error message.
    others : list
        A list of other similar datasets.

    Returns
    -------
    str
        A formatted error message.

    See Also
    --------
    pprint.pformat : Format a Python object into a pretty-printed string.

    Notes
    -----
    This function is used to generate a formatted error message for a dataset that can't be
    uniquely linked to the target database. It takes the problematic dataset and a list of other
    similar datasets and returns an error message that includes the problematic dataset and a list
    of possible target datasets that may match the problematic dataset.

    Raises
    ------
    None

    Examples
    --------
    >>> obj = {'name': 'Electricity', 'location': 'CH'}
    >>> fields = ['name', 'location']
    >>> others = [
    ...     {'name': 'Electricity', 'location': 'CH', 'filename': 'file1'},
    ...     {'name': 'Electricity', 'location': 'CH', 'filename': 'file2'}
    ... ]
    >>> format_nonunique_key_error(obj, fields, others)
    "Object in source database can't be uniquely linked to target database.
    Problematic dataset is:
    {'name': 'Electricity', 'location': 'CH'}
    Possible targets include (at least one not shown):
    [{'name': 'Electricity', 'location': 'CH', 'filename': 'file1'},
    {'name': 'Electricity', 'location': 'CH', 'filename': 'file2'}]"
    """
    template = """Object in source database can't be uniquely linked to target database.\nProblematic dataset is:\n{ds}\nPossible targets include (at least one not shown):\n{targets}"""
    fields_to_print = list(fields or DEFAULT_FIELDS) + ["filename"]
    _ = lambda x: {field: x.get(field, "(missing)") for field in fields_to_print}
    return template.format(
        ds=pprint.pformat(_(obj)), targets=pprint.pformat([_(x) for x in others])
    )


def link_iterable_by_fields(
    unlinked: Iterable[dict],
    other: Optional[Iterable[dict]] = None,
    fields: Optional[List[str]] = None,
    kind: Union[str, List[str]] = None,
    internal: bool = False,
    relink: bool = False,
):
    """
    Link objects in ``unlinked`` to objects in ``other`` using fields ``fields``.

    Parameters
    ----------
    unlinked : iterable[dict]
        An iterable of dictionaries containing objects to be linked.
    other : iterable[dict], optional
        An iterable of dictionaries containing objects to link to. If not specified, `other` is set
        to `unlinked`.
    fields : iterable[str], optional
        An iterable of strings indicating which fields should be used to match objects. If not
        specified, all fields will be used.
    kind : str|list[string], optional
        If specified, limit the exchange to objects of the given kind. `kind` can be a string or an
        iterable of strings.
    internal : bool, optional
        If `True`, link objects in `unlinked` to other objects in `unlinked`. Each object must have
        the attributes `database` and `code`.
    relink : bool, optional
        If `True`, link to objects that already have an `input`. Otherwise, skip objects that have
        already been linked.

    Returns
    -------
    iterable
        An iterable of dictionaries containing linked objects.

    Raises
    ------
    StrategyError
        If not all datasets in the database to be linked have ``database`` or ``code`` attributes.
        If there are duplicate keys for the given fields.

    See Also
    --------
    activity_hash : Generate a unique hash key for a dataset.
    format_nonunique_key_error : Generate an error message for datasets that can't be uniquely
    linked to the target database.

    Notes
    -----
    This function takes two iterables of dictionaries: ``unlinked`` and ``other``, where each
    dictionary represents an object to be linked. The objects are linked by matching their fields
    ``fields``. The function returns an iterable of dictionaries containing linked objects.

    If the parameter ``kind`` is specified, only objects of the given kind are linked. If
    ``internal`` is True, objects in ``unlinked`` are linked to other objects in ``unlinked``. If
    ``relink`` is True, objects that already have an input are linked again.

    If a link is not unique, a ``StrategyError`` is raised, which includes a formatted error message
    generated by the ``format_nonunique_key_error`` function.

    Examples
    --------
    >>> data = [
    ...     {"exchanges": [
    ...         {"type": "A", "value": 1},
    ...         {"type": "B", "value": 2}
    ...     ]},
    ...     {"exchanges": [
    ...         {"type": "C", "value": 3},
    ...         {"type": "D", "value": 4}
    ...     ]}
    ... ]
    >>> other = [
    ...     {"database": "db1", "code": "A"},
    ...     {"database": "db2", "code": "C"}
    ... ]
    >>> linked = link_iterable_by_fields(data, other=other, fields=["code"])
    >>> linked[0]["exchanges"][0]["input"]
    ('db1', 'A')
    >>> linked[1]["exchanges"][0]["input"]
    ('db2', 'C')
    """
    if kind:
        kind = {kind} if isinstance(kind, str) else kind
        if relink:
            filter_func = lambda x: x.get("type") in kind
        else:
            filter_func = lambda x: x.get("type") in kind and not x.get("input")
    else:
        if relink:
            filter_func = lambda x: True
        else:
            filter_func = lambda x: not x.get("input")

    if internal:
        other = unlinked

    duplicates, candidates = {}, {}
    try:
        # Other can be a generator, so a bit convoluted
        for ds in other:
            key = activity_hash(ds, fields)
            if key in candidates:
                duplicates.setdefault(key, []).append(ds)
            else:
                candidates[key] = (ds["database"], ds["code"])
    except KeyError:
        raise StrategyError(
            "Not all datasets in database to be linked have "
            "``database`` or ``code`` attributes"
        )

    for container in unlinked:
        for obj in filter(filter_func, container.get("exchanges", [])):
            key = activity_hash(obj, fields)
            if key in duplicates:
                raise StrategyError(
                    format_nonunique_key_error(obj, fields, duplicates[key])
                )
            elif key in candidates:
                obj["input"] = candidates[key]
    return unlinked


def assign_only_product_as_production(db: Iterable[dict]) -> List[dict]:
    """
    Assign only product as reference product.

    For each dataset in ``db``, this function checks if there is only one production exchange and
    no reference product already assigned. If this is the case, the reference product is set to the
    name of the production exchange, and the following fields are replaced if not already specified:

    * 'name' - name of reference product
    * 'unit' - unit of reference product
    * 'production amount' - amount of reference product

    Parameters
    ----------
    db : iterable
        An iterable of dictionaries containing the datasets to process.

    Returns
    -------
    iterable
        An iterable of dictionaries containing the processed datasets.

    Raises
    ------
    AssertionError
        If a production exchange does not have a `name` attribute.

    Examples
    --------
    >>> data = [{'name': 'Input 1', 'exchanges': [{'type': 'production', 'name': 'Product 1', 'amount': 1}, {'type': 'technosphere', 'name': 'Input 2', 'amount': 2}]}, {'name': 'Input 2', 'exchanges': [{'type': 'production', 'name': 'Product 2', 'amount': 3}, {'type': 'technosphere', 'name': 'Input 3', 'amount': 4}]}]
    >>> processed_data = assign_only_product_as_production(data)
    >>> processed_data[0]['reference product']
    'Product 1'
    >>> processed_data[0]['name']
    'Input 1'
    >>> processed_data[1]['reference product']
    'Product 2'
    >>> processed_data[1]['unit']
    'Unknown'
    """
    for ds in db:
        if ds.get("reference product"):
            continue
        products = [x for x in ds.get("exchanges", []) if x.get("type") == "production"]
        if len(products) == 1:
            product = products[0]
            assert product["name"]
            ds["reference product"] = (
                product.get("reference product", []) or product["name"]
            )
            ds["production amount"] = product["amount"]
            ds["name"] = ds.get("name") or product["name"]
            ds["unit"] = ds.get("unit") or product.get("unit") or "Unknown"
    return db


def link_technosphere_by_activity_hash(db, external_db_name=None, fields=None):
    """
    Link technosphere exchanges using the `activity_hash` function.

    If ``external_db_name`` is provided, link technosphere exchanges against an external database,
    otherwise link internally.

    Parameters
    ----------
    db : obj
        The database to link exchanges in.
    external_db_name : str, optional
        The name of an external database to link against. Default is None.
    fields : list of str, optional
        The fields to use for linking exchanges. If None, all fields will be used.

    Returns
    -------
    linked : list of tuples
        A list of tuples representing the linked exchanges.

    Raises
    ------
    StrategyError
        If the external database name provided is not found in the list of available databases.

    Examples
    --------
    Link technosphere exchanges internally:

    >>> db = Database('example_db')
    >>> linked = link_technosphere_by_activity_hash(db)

    Link technosphere exchanges against an external database using specific fields:

    >>> linked = link_technosphere_by_activity_hash(
    ...     db,
    ...     external_db_name='other_db',
    ...     fields=['name', 'unit']
    ... )
    """
    TECHNOSPHERE_TYPES = {"technosphere", "substitution", "production"}
    if external_db_name is not None:
        if external_db_name not in databases:
            raise StrategyError(
                "Can't find external database {}".format(external_db_name)
            )
        other = (
            obj
            for obj in Database(external_db_name)
            if obj.get("type", "process") == "process"
        )
        internal = False
    else:
        other = None
        internal = True
    return link_iterable_by_fields(
        db, other, internal=internal, kind=TECHNOSPHERE_TYPES, fields=fields
    )


def set_code_by_activity_hash(db, overwrite=False):
    """
    Set the dataset code for each dataset in the given database using `activity_hash`.

    Parameters
    ----------
    db : obj
        The database to set the dataset codes in.
    overwrite : bool, optional
        Whether to overwrite existing codes. Default is False.

    Returns
    -------
    obj
        The modified database object with updated dataset codes.

    Notes
    -----
    The dataset code is a unique identifier for each dataset in the database. It is generated by hashing the dataset dictionary with `activity_hash`.

    Examples
    --------
    >>> db = Database('example_db')
    >>> set_code_by_activity_hash(db)
    """
    for ds in db:
        if "code" not in ds or overwrite:
            ds["code"] = activity_hash(ds)
    return db


def tupleize_categories(db):
    """
    Convert the "categories" fields in a given database and its exchanges to tuples.

    Parameters
    ----------
    db : obj
        The database to convert categories in.

    Returns
    -------
    obj
        The modified database object with converted category fields.

    Examples
    --------
    >>> from bw2data import Database
    >>> db = Database('example_db')
    >>> tupleize_categories(db)
    """
    for ds in db:
        if ds.get("categories"):
            ds["categories"] = tuple(ds["categories"])
        for exc in ds.get("exchanges", []):
            if exc.get("categories"):
                exc["categories"] = tuple(exc["categories"])
    return db


def drop_unlinked(db):
    """
    Remove all exchanges in a given database that don't have inputs.

    Exchanges that don't have any inputs are often referred to as "unlinked exchanges".
    These exchanges can be a sign of an incomplete or poorly structured database.

    Parameters
    ----------
    db : obj
        The database to remove unlinked exchanges from.

    Returns
    -------
    obj
        The modified database object with removed unlinked exchanges.

    Notes
    -----
    This is the nuclear option - use at your own risk! ⚠️

    Examples
    --------
    >>> db = [
    ...    {"name": "Product A", "unit": "kg", "exchanges": [{"input": True, "amount": 1, "name": "Input 1", "unit": "kg"}]},
    ...    {"name": "Product B", "unit": "kg", "exchanges": [{"input": True, "amount": 1, "name": "Input 2", "unit": "kg"}, {"input": False, "amount": 0.5, "name": "Product A", "unit": "kg"}]},
    ...    {"name": "Product C", "unit": "kg", "exchanges": [{"input": False, "amount": 0.75, "name": "Product A", "unit": "kg"}]}
    ... ]
    >>> drop_unlinked(db)
    [
        {'name': 'Product A', 'unit': 'kg', 'exchanges': [{'input': True, 'amount': 1, 'name': 'Input 1', 'unit': 'kg'}]},
    ... {'name': 'Product B', 'unit': 'kg', 'exchanges': [{'input': True, 'amount': 1, 'name': 'Input 2', 'unit': 'kg'},
    ... {'input': False, 'amount': 0.5, 'name': 'Product A', 'unit': 'kg'}]},
    ... {'name': 'Product C', 'unit': 'kg', 'exchanges': []}
    ]
    """
    for ds in db:
        ds["exchanges"] = [obj for obj in ds["exchanges"] if obj.get("input")]
    return db


def normalize_units(db: List[dict]) -> List[dict]:
    """
    Normalize units in datasets and their exchanges.

    Parameters
    ----------
    db : list[dict]
        The database that needs to be normalized.

    Returns
    -------
    list[dict]
        The normalized database.

    Examples
    --------
    Example 1: Normalize the units of a given database.

    >>> db = {'name': 'test_db', 'unit': 'kg'}
    >>> normalize_units(db)
    {'name': 'test_db', 'unit': 'kilogram'}

    Example 2: Normalize the units of a dataset and its exchanges.

    >>> db = {
    ...     'name': 'test_db',
    ...     'unit': 'kg',
    ...     'exchanges': [
    ...         {'name': 'input', 'unit': 't'},
    ...         {'name': 'output', 'unit': 'lb'},
    ...     ]
    ... }
    >>> normalize_units(db)
    {'name': 'test_db',
     'unit': 'kilogram',
     'exchanges': [
         {'name': 'input', 'unit': 'tonne'},
         {'name': 'output', 'unit': 'pound'}
     ]}
    """
    for ds in db:
        if "unit" in ds:
            ds["unit"] = normalize_units_function(ds["unit"])
        for exc in ds.get("exchanges", []):
            if "unit" in exc:
                exc["unit"] = normalize_units_function(exc["unit"])
            if "reference unit" in exc:
                exc["reference unit"] = normalize_units_function(exc["reference unit"])
        for param in ds.get("parameters", {}).values():
            if "unit" in param:
                param["unit"] = normalize_units_function(param["unit"])
    return db


def add_database_name(db: List[dict], name: str) -> List[dict]:
    """
    Adds a database name to each dataset in a list of datasets.

    Parameters
    ----------
    db : list[dict]
        The list of datasets to add the database name to.
    name : str
        The name of the database to be added to each dataset.

    Returns
    -------
    list[dict]
        The updated list of datasets with the database name added to each dataset.

    Examples
    --------
    >>> db = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    >>> add_database_name(db, "X")
    [{'id': 1, 'name': 'A', 'database': 'X'}, {'id': 2, 'name': 'B', 'database': 'X'}]

    An empty list input returns an empty list.
    >>> add_database_name([], "Y")
    []
    """
    for ds in db:
        ds["database"] = name
    return db


def convert_uncertainty_types_to_integers(db):
    """
    Convert uncertainty types in a list of datasets to integers.

    Parameters
    ----------
    db : list[dict]
        The list of datasets containing uncertainty types to convert.

    Returns
    -------
    list[dict]
        The updated list of datasets with uncertainty types converted to integers where possible.

    Examples
    --------
    >>> db = [{"name": "A", "exchanges": [{"uncertainty type": "triangular"}]}, {"name": "B", "exchanges": [{"uncertainty type": "lognormal"}]}]
    >>> convert_uncertainty_types_to_integers(db)
    [{'name': 'A', 'exchanges': [{'uncertainty type': 'triangular'}]}, {'name': 'B', 'exchanges': [{'uncertainty type': 'lognormal'}]}]

    Float values are rounded down to integers.
    >>> db = [{"name": "C", "exchanges": [{"uncertainty type": "1"}, {"uncertainty type": "2.0"}]}]
    >>> convert_uncertainty_types_to_integers(db)
    [{'name': 'C', 'exchanges': [{'uncertainty type': 1}, {'uncertainty type': 2}]}]
    """
    for ds in db:
        for exc in ds["exchanges"]:
            try:
                exc["uncertainty type"] = int(exc["uncertainty type"])
            except:
                pass
    return db


def drop_falsey_uncertainty_fields_but_keep_zeros(db):
    """
    Drop uncertainty fields that are falsey (e.g. '', None, False) but keep zero and NaN.

    Note that this function doesn't strip `False`, which behaves exactly like 0.

    Parameters
    ----------
    db : list[dict]
        The list of datasets to drop uncertainty fields from.

    Returns
    -------
    list[dict]
        The updated list of datasets with falsey uncertainty fields dropped.

    Examples
    --------
    >>> db = [{"name": "A", "exchanges": [{"amount": 1, "minimum": 0, "maximum": None, "shape": ""}]}]
    >>> drop_falsey_uncertainty_fields_but_keep_zeros(db)
    [{'name': 'A', 'exchanges': [{'amount': 1, 'minimum': 0}]}]

    Float values of NaN are kept in the dictionary.
    >>> db = [{"name": "B", "exchanges": [{"loc": 0.0, "scale": 0.5, "minimum": float('nan')},... {"loc": 0.0, "scale": 0.5}]}]
    >>> drop_falsey_uncertainty_fields_but_keep_zeros(db)
    [{'name': 'B', 'exchanges': [{'loc': 0.0, 'scale': 0.5, 'minimum': nan},{'loc': 0.0, 'scale': 0.5}]}]
    """
    uncertainty_fields = [
        "minimum",
        "maximum",
        "scale",
        "shape",
        "loc",
    ]

    def drop_if_appropriate(exc):
        for field in uncertainty_fields:
            if field not in exc or exc[field] == 0:
                continue
            elif isinstance(exc[field], numbers.Number) and np.isnan(exc[field]):
                continue
            elif not exc[field]:
                del exc[field]

    for ds in db:
        for exc in ds["exchanges"]:
            drop_if_appropriate(exc)
    return db


def convert_activity_parameters_to_list(data):
    """ "
    Convert activity parameters from a dictionary to a list of dictionaries.

    Parameters
    ----------
    data : list[dict]
        The list of activities to convert parameters from.

    Returns
    -------
    list[dict]
        The updated list of activities with parameters converted to a list of dictionaries.

    Examples
    --------
    >>> data = [{"name": "A", "parameters": {"param1": 1, "param2": 2}}, {"name": "B", "parameters": {"param3": 3, "param4": 4}}]
    >>> convert_activity_parameters_to_list(data)
    [{'name': 'A', 'parameters': [{'name': 'param1', 1}, {'name': 'param2', 2}]}, {'name': 'B', 'parameters': [{'name': 'param3', 3}, {'name': 'param4', 4}]}]

    Activities without parameters remain unchanged.
    >>> data = [{"name": "C"}]
    >>> convert_activity_parameters_to_list(data)
    [{'name': 'C'}]
    """

    def _(key, value):
        dct = deepcopy(value)
        dct["name"] = key
        return dct

    for ds in data:
        if "parameters" in ds:
            ds["parameters"] = [_(x, y) for x, y in ds["parameters"].items()]

    return data


def split_exchanges(data, filter_params, changed_attributes, allocation_factors=None):
    """
    Split unlinked exchanges in ``data`` which satisfy ``filter_params`` into new exchanges with changed attributes.

    ``changed_attributes`` is a list of dictionaries with the attributes that should be changed.

    ``allocation_factors`` is an optional list of floats to allocate the original exchange amount to the respective copies defined in ``changed_attributes``. They don't have to sum to one. If ``allocation_factors`` are not defined, then exchanges are split equally.

    Resets uncertainty to ``UndefinedUncertainty`` (0).

    To use this function as a strategy, you will need to curry it first using ``functools.partial``.

    Parameters
    ----------
    data : list[dict]
        The list of activities to split exchanges in.
    filter_params : dict
        A dictionary of filter parameters to apply to the exchanges that will be split.
    changed_attributes : list[dict]
        A list of dictionaries with the attributes that should be changed in the new exchanges.
    allocation_factors : Optional[List[float]], optional
        An optional list of floats to allocate the original exchange amount to the respective copies defined in ``changed_attributes``, by default None. If ``allocation_factors`` are not defined, then exchanges are split equally.

    Returns
    -------
    list[dict]
        The updated list of activities with exchanges split.

    Examples
    --------
    >>> data = [{"name": "A", "exchanges": [{"name": "foo", "location": "bar", "amount": 20}, {"name": "food", "location": "bar", "amount": 12}]}]
    >>> split_exchanges(data, {"name": "foo"}, [{"location": "A"}, {"location": "B", "cat": "dog"}])
    [{'name': 'A', 'exchanges': [{'name': 'food', 'location': 'bar', 'amount': 12}, {'name': 'foo', 'location': 'A', 'amount': 12.0, 'uncertainty_type': 0}, {'name': 'foo', 'location': 'B', 'amount': 8.0, 'uncertainty_type': 0, 'cat': 'dog'}]}]
    >>> data = [{"name": "B", "exchanges": [{"name": "bar", "location": "foo", "amount": 25}, {"name": "bard", "location": "foo", "amount": 13}]}]
    >>> split_exchanges(data, {"name": "bard", "location": "foo"}, [{"name": "new", "location": "bar"}], [0.3])
    [{'name': 'B', 'exchanges': [{'name': 'bar', 'location': 'foo', 'amount': 25}, {'name': 'new', 'location': 'bar', 'amount': 3.9000000000000004, 'uncertainty_type': 0}]}]
    """
    if allocation_factors is None:
        allocation_factors = [1] * len(changed_attributes)

    total = sum(allocation_factors)

    if len(changed_attributes) != len(allocation_factors):
        raise ValueError(
            "`changed_attributes` and `allocation_factors` must have same length"
        )

    for ds in data:
        to_delete, to_add = [], []
        for index, exchange in enumerate(ds.get("exchanges", [])):
            if exchange.get("input"):
                continue
            if all(exchange.get(key) == value for key, value in filter_params.items()):
                to_delete.append(index)
                for factor, obj in zip(allocation_factors, changed_attributes):
                    exc = deepcopy(exchange)
                    exc["amount"] = exc["amount"] * factor / total
                    exc["uncertainty_type"] = 0
                    for key, value in obj.items():
                        exc[key] = value
                    to_add.append(exc)
        if to_delete:
            for index in to_delete[::-1]:
                del ds["exchanges"][index]
            ds["exchanges"].extend(to_add)
    return data
