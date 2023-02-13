import pytest
import shutil

from bw2data import Database, parameters, config, projects
from bw2io.importers.pint_formulas import PintFormulasImporter

test_biosphere_name = "biosphere"
test_technosphere_name = "test"

bw2parameters = pytest.importorskip("bw2parameters", "1.0.0")


@pytest.fixture(scope="module")
def _use_pint():
    if not bw2parameters.PintWrapper.pint_installed:
        pytest.skip("Pint not installed.")
    import fixtures
    config.use_pint_parameters = True
    config.dont_warn = True
    config.is_test = True
    config.cache = {}
    tempdir = projects._use_temp_directory()
    bio = Database(test_biosphere_name)
    bio.write(fixtures.biosphere)

    yield fixtures.data, fixtures.db_params

    def close_all_databases():
        for path, db in config.sqlite3_databases:
            db.db.autoconnect = False
            db.db.close()

    close_all_databases()
    shutil.rmtree(tempdir)


def _dicts_partially_equal(expected, result):
    """Makes sure two dicts are equal while ignoring key-value pairs which are not present in `expected`."""
    return all(expected[k] == result[k] for k in expected.keys())


def _check_activities_and_exchanges(db):
    # test activity A
    act_A = next(filter(lambda a: a["name"] == "A", db))
    expected = {
        "name": "A",
        "location": "DE",
        "unit": "kilogram / year",
    }
    assert _dicts_partially_equal(expected, act_A._data)
    assert "parameters" not in act_A._data

    # test activity B
    act_B = next(filter(lambda a: a["name"] == "B", db))
    expected = {
        "name": "B",
        "location": "DE",
        "unit": "kilogram",
    }
    assert _dicts_partially_equal(expected, act_B._data)
    assert "parameters" not in act_B._data

    # test activity C
    act_C = next(filter(lambda a: a["name"] == "C", db))
    expected = {
        "name": "C",
        "location": "FR",
        "unit": "unit",
    }
    assert _dicts_partially_equal(expected, act_C._data)
    assert "parameters" not in act_C._data

    # test exchange B -> A
    ex_BA = next(filter(lambda e: e["name"] == "B", act_A.exchanges()))
    expected = {
        "name": "B",
        "location": "DE",
        "formula": "production_kg_per_yr * system_life_time_yr / efficiency",
        "type": "technosphere",
        "unit": "kilogram",
        "original_amount": 0,
        "amount": 1e6 * 20 / 0.6,
        "input": (test_technosphere_name, act_B["code"]),
        "output": (test_technosphere_name, act_A["code"]),
    }
    assert expected == ex_BA._data

    # test exchange C -> A
    ex_CA = next(filter(lambda e: e["name"] == "C", act_A.exchanges()))
    expected = {
        "name": "C",
        "location": "FR",
        "formula": "2",
        "type": "technosphere",
        "unit": "unit",
        "amount": 2,
        "original_amount": 0,
        "input": (test_technosphere_name, act_C["code"]),
        "output": (test_technosphere_name, act_A["code"]),
    }
    assert expected == ex_CA._data

    # test exchange CO2 -> B
    ex_CO2B = next(
        filter(lambda e: "Carbon dioxide" in e["name"], act_B.exchanges())
    )
    expected = {
        "name": "Carbon dioxide, fossil",
        "categories": ("air", "urban-air from high stacks"),
        "type": "biosphere",
        "database": "biosphere",
        "unit": "kg",
        "amount": 1,
        "input": (test_biosphere_name, "1"),
        "output": (test_technosphere_name, act_B["code"]),
    }
    assert expected == ex_CO2B._data


def test_simple_import(_use_pint):
    data, db_params = _use_pint
    pfi = PintFormulasImporter(
        db_name=test_technosphere_name,
        data=data,
        db_params=db_params,
    )
    pfi.apply_strategies()
    pfi.write_database()
    db = Database(test_technosphere_name)

    assert len(db) == 3

    # test activities and exchanges
    _check_activities_and_exchanges(db)

    # should remain same after re-calculation
    parameters.recalculate()
    _check_activities_and_exchanges(db)

    pass
