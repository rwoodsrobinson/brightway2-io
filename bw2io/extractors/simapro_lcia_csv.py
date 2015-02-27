# -*- coding: utf-8 -*
from __future__ import print_function
from ..compatibility import SIMAPRO_BIOSPHERE, SIMAPRO_BIO_SUBCATEGORIES
from ..units import normalize_units
from ..utils import activity_hash
from bw2data import Database, databases, config
from bw2data.logs import get_io_logger, close_log
from bw2parameters import ParameterSet
from numbers import Number
from stats_arrays import *
import os
import math
import unicodecsv


INTRODUCTION = u"""Starting SimaPro import:
\tFilepath: %s
\tDelimiter: %s
"""

SKIPPABLE_SECTIONS = {
    "Airborne emissions",
    "Economic issues",
    "Emissions to soil",
    "Final waste flows",
    "Quantities",
    "Raw materials",
    "Units",
    "Waterborne emissions",
}


class EndOfDatasets(Exception):
    pass


def filter_delete_char(fp):
    """Where does this come from? \x7f is ascii delete code..."""
    for line in open(fp):
        yield line.replace('\x7f', '')


class SimaProLCIACSVExtractor(object):
    @classmethod
    def extract(cls, filepath, delimiter=";", encoding='cp1252'):
        assert os.path.exists(filepath), "Can't find file %s" % filepath
        log, logfile = get_io_logger(u"SimaPro-LCIA-extractor")

        log.info(INTRODUCTION % (
            filepath,
            repr(delimiter),
        ))
        lines = cls.load_file(filepath, delimiter, encoding)

        # Check if valid SimaPro file
        assert u'SimaPro' in lines[0][0], "File is not valid SimaPro export"

        datasets = []

        index = cls.get_next_method_index(lines, 0)

        while True:
            try:
                ds, index = cls.read_method_data_set(lines, index, filepath)
                datasets.extend(ds)
                index = cls.get_next_method_index(lines, index)
            except EndOfDatasets:
                break

        close_log(log)
        return datasets

    @classmethod
    def get_next_method_index(cls, data, index):
        while True:
            try:
                if data[index] and data[index][0] in SKIPPABLE_SECTIONS:
                    index = cls.skip_to_section_end(data, index)
                elif data[index] and data[index][0] == u"Method":
                    return index + 1
            except IndexError:
                # File ends without extra metadata
                raise EndOfDatasets
            index += 1

    @classmethod
    def skip_to_section_end(cls, data, index):
        while (data[index][0] if data[index] else "").strip() != 'End':
            index += 1
        return index

    @classmethod
    def load_file(cls, filepath, delimiter, encoding):
        """Open the CSV file and load the data.

        Returns:
            The loaded data: a list of lists.

        """
        return [x for x in unicodecsv.reader(
            filter_delete_char(filepath),
            delimiter=delimiter,
            encoding=encoding,
        )]

    @classmethod
    def parse_cf(cls, line):
        """Parse line in `Substances` section.

        0. category
        1. subcategory
        2. flow
        3. CAS number
        4. CF
        5. unit

        """
        if line[1] == "(unspecified)":
            categories = (line[0].lower(),)
        else:
            categories = (line[0].lower(),
                          SIMAPRO_BIOSPHERE.get(line[1], line[1].lower()))
        return {
            u'amount': float(line[4]),
            u'CAS number': line[3],
            u'categories': categories,
            u'name': line[2],
            u'unit': normalize_units(line[5]),
        }

    @classmethod
    def read_metadata(cls, data, index):
        metadata = {}
        while True:
            if not data[index]:
                pass
            elif data[index] and data[index][0] == 'Impact category':
                return metadata, index
            elif data[index] and data[index + 1] and data[index][0]:
                metadata[data[index][0]] = data[index + 1][0]
                index += 1
            index += 1

    @classmethod
    def read_method_data_set(cls, data, index, filepath):
        metadata, index = cls.read_metadata(data, index)
        method_root_name = metadata.pop('Name')
        description = metadata.pop('Comment')
        category_data, nw_data, completed_data = [], [], []

        # `index` is now the `Impact category` line
        while not data[index] or data[index][0] != 'End':
            if not data[index] or not data[index][0]:
                index += 1
            elif data[index][0] == 'Impact category':
                catdata, index = cls.get_category_data(data, index + 1)
                category_data.append(catdata)
            elif data[index][0] == 'Normalization-Weighting set':
                nw_dataset, index = cls.get_normalization_weighting_data(data,
                    index + 1)
                nw_data.append(nw_dataset)
            else:
                raise ValueError

        for ds in category_data:
            completed_data.append({
                'description': description,
                'name': (method_root_name, ds[0]),
                'unit': ds[1],
                'filename': filepath,
                'data': ds[2]
            })

        for ds in nw_data:
            completed_data.append({
                'description': description,
                'name': (method_root_name, ds[0]),
                'unit': metadata['Weighting unit'],
                'filename': filepath,
                'data': cls.get_all_cfs(ds[1], category_data)
            })

        return completed_data, index

    @classmethod
    def get_all_cfs(cls, nw_data, category_data):
        def rescale(cf, scale):
            cf['amount'] *= scale
            return cf

        cfs = []
        for nw_name, scale in nw_data:
            for cat_name, _, cf_data in category_data:
                if cat_name == nw_name:
                    cfs.extend([rescale(cf, scale) for cf in cf_data])
        return cfs

    @classmethod
    def get_category_data(cls, data, index):
        cf_data = []
        # First line is name and unit
        name, unit = data[index][:2]
        index += 2
        assert data[index][0] == 'Substances'
        index += 1
        while data[index]:
            cf_data.append(cls.parse_cf(data[index]))
            index += 1
        return (name, unit, cf_data), index

    @classmethod
    def get_normalization_weighting_data(cls, data, index):
        # TODO: Only works for weighting data, no addition or normalization
        nw_data = []
        name = data[index][0]
        index += 2
        assert data[index][0] == 'Weighting'
        index += 1
        while data[index]:
            cat, weight = data[index][:2]
            index += 1
            if weight == "0":
                continue
            nw_data.append((cat, float(weight)))
        return (name, nw_data), index