# -*- coding: utf-8 -*-
from ..compatibility import (
    SIMAPRO_BIOSPHERE,
    ECOSPOLD_2_3_BIOSPHERE,
)
from ..units import normalize_units
import codecs
import copy
import json
import os
import xlrd
import unicodecsv

dirpath = os.path.dirname(__file__)


def write_json_file(data, name):
    with codecs.open(os.path.join(dirpath, name + ".json"), "w",
                     encoding='utf8') as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def get_sheet(path, name):
    wb = xlrd.open_workbook(path)
    return wb.sheet_by_name(name)


def get_biosphere_2_3_category_migration_data():
    """Get data for 2 -> 3 migration for biosphere flow categories"""
    return {
        'fields': ['categories', 'type'],
        'data': [
            (
                (k, 'biosphere'),  # Exchanges
                {'categories': v}
            ) for k, v in ECOSPOLD_2_3_BIOSPHERE.items()
        ] + [
            (
                (k, 'emission'),   # Datasets
                {'categories': v}
            ) for k, v in ECOSPOLD_2_3_BIOSPHERE.items()
        ]
    }


def get_biosphere_2_3_name_migration_data():
    """Get migration data for 2 -> 3 biosphere flow names.

    This migration **must** be applied only after categories have been updated.

    Note that the input data excel sheet is **modified** from the raw data provided by ecoinvent - some biosphere flows which had no equivalent in ecospold2 were mapped using my best judgment. Name changes from 3.1 were also included. Modified cells are marked in **dark orange**.

    Note that not all rows have names in ecoinvent 3. There are a few energy resources that we don't update. For water flows, the categories are updated by a different strategy, and the names don't change, so we just ignore them for now."""

    ws = get_sheet(os.path.join(dirpath, "lci", "ecoinvent elementary flows 2-3.xlsx"), "ElementaryExchanges")

    def to_exchange(obj):
        obj[0][3] = u'biosphere'
        return obj

    def strip_unspecified(one, two):
        if two == 'unspecified':
            return (one,)
        else:
            return (one, two)

    data = [
        (
            [
                ws.cell(row, 1).value,   # Old name
                # Categories
                strip_unspecified(ws.cell(row, 9).value, ws.cell(row, 10).value),
                normalize_units(ws.cell(row, 6).value),
                u'emission'  # Unit
            ], {'name': ws.cell(row, 8).value}
        )
        for row in range(1, ws.nrows)
        if ws.cell(row, 1).value
        and ws.cell(row, 8).value
        and ws.cell(row, 1).value != ws.cell(row, 8).value
    ]
    data = copy.deepcopy(data) + [to_exchange(obj) for obj in data]

    # Water unit changes
    data.extend([
        (
            ('Water', ('air',), 'kilogram', 'biosphere'),
            {'unit': 'cubic meter', 'multiplier': 0.001}
        ),
        (
            ('Water', ('air', 'non-urban air or from high stacks'), 'kilogram', 'biosphere'),
            {'unit': 'cubic meter', 'multiplier': 0.001}
        ),
        (
            ('Water', ('air', 'lower stratosphere + upper troposphere'), 'kilogram', 'biosphere'),
            {'unit': 'cubic meter', 'multiplier': 0.001}
        ),
        (
            ('Water', ('air', 'urban air close to ground'), 'kilogram', 'biosphere'),
            {'unit': 'cubic meter', 'multiplier': 0.001}
        ),
    ])

    return {
        'fields': ['name', 'categories', 'unit', 'type'],
        'data': data
    }


def convert_simapro_ecoinvent_elementary_flows():
    """Write a correspondence list from SimaPro elementary flow names to ecoinvent 3 flow names to a JSON file.

    Uses custom SimaPro specific data. Ecoinvent 2 -> 3 conversion is in a separate JSON file."""
    ws = get_sheet(os.path.join(dirpath, "lci", "SimaPro - ecoinvent - biosphere.xlsx"), "ee")
    data = [[ws.cell(row, col).value for col in range(3)]
            for row in range(1, ws.nrows)]
    data = {[SIMAPRO_BIOSPHERE[obj[0]], obj[1], obj[2]] for obj in data}
    write_json_file(sorted(data), 'simapro-biosphere')


def get_simapro_ecoinvent_3_migration_data():
    """Write a migrations data file from SimaPro activity names to ecoinvent 3 processes.

    Correspondence file is from Pré, and has the following fields:

        #. SimaPro name
        #. Ecoinvent flow name
        #. Location
        #. Ecoinvent activity name
        #. System model
        #. SimaPro type

    Note that even the official matching data from Pré is incorrect, but works if we cast all strings to lower case.

    SimaPro type is either ``System terminated`` or ``Unit process``. We always match to unit processes regardless of SimaPro type."""
    ws = get_sheet(os.path.join(dirpath, "lci", "SimaPro - ecoinvent - technosphere.xlsx"), "Mapping")
    data = [[ws.cell(row, col).value for col in range(1, 7)]
            for row in range(3, ws.nrows)]
    return {
        'fields': ['name'],
        'data': [(
            (line[0], ),
            {
                'location': line[2],
                'name': line[3],
                'reference product': line[1],
                'system model': line[4],
                'simapro name': line[0],
            }
        ) for line in data]
    }


def convert_ecoinvent_2_301():
    """Write a migrations data file from ecoinvent 2 to 3.1.

    This is not simple, unfortunately. We have to deal with at least the following:
        * Unit changes (e.g. cubic meters to MJ)
        * Some datasets are deleted, and replaced by others

    """
    ws = get_sheet(os.path.join(dirpath, "lci", "ecoinvent 2-3.01.xlsx"), "correspondence sheet_corrected")
    data = [[ws.cell(row, col).value for col in range(17)]
            for row in range(1, ws.nrows)]
    data = {
        'fields': ['name', 'location'],
        'data': [(
            {'name': line[0]},
            {
                'location': line[2],
                'name': line[3],
                'reference product': line[1],
                'system model': line[4]
            }
        ) for line in data]
    }
    write_json_file(data, 'simapro-ecoinvent31')


def convert_lcia_methods_data():
    csv_file = unicodecsv.reader(
        open(os.path.join(os.path.dirname(__file__), "lcia",
             "categoryUUIDs.csv")),
        delimiter=";"
    )
    csv_file.next()  # Skip header row
    csv_data = [{
        'name': (line[0], line[2], line[4]),
        'unit': line[6],
        'description': line[7]
    } for line in csv_file]

    filename = "LCIA implementation v3.1 2014_08_13.xlsx"
    sheet = get_sheet(
        os.path.join(dirpath, "lcia", filename),
        "impact methods"
    )
    cf_data = [{
        'method': (sheet.cell(row, 0).value,
                   sheet.cell(row, 1).value,
                   sheet.cell(row, 2).value),
        'name': sheet.cell(row, 3).value,
        'categories': (sheet.cell(row, 4).value, sheet.cell(row, 5).value),
        'amount': sheet.cell(row, 10).value or sheet.cell(row, 7).value
    } for row in range(1, sheet.nrows)]

    return csv_data, cf_data, filename
