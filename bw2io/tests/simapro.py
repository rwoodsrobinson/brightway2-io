# # -*- coding: utf-8 -*-
from ..strategies.simapro import detoxify_re
# from .fixtures.simapro_reference import background as background_data
# from bw2data import Database, databases, config
from bw2data.tests import BW2DataTest
# from bw2data.utils import recursive_str_to_unicode as _
# from stats_arrays import UndefinedUncertainty, NoUncertainty
# import os


# SP_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "simapro")


class SimaProCSVImporterTest(BW2DataTest):
    # def extra_setup(self):
    #     # SimaPro importer always wants biosphere database
    #     database = Database("biosphere", backend="singlefile")
    #     database.register()
    #     database.write({})

    # def filepath(self, name):
    #     return os.path.join(SP_FIXTURES_DIR, name + '.txt')

    # def test_invalid_file(self):
    #     sp = SimaProImporter(self.filepath("invalid"), depends=[])
    #     data = sp.load_file()
    #     with self.assertRaises(AssertionError):
    #         sp.verify_simapro_file(data)

    # def test_overwrite(self):
    #     database = Database("W00t")
    #     database.register()
    #     sp = SimaProImporter(self.filepath("empty"), depends=[], overwrite=True)
    #     sp.importer()
    #     self.assertTrue("W00t" in databases)

    # def test_no_overwrite(self):
    #     database = Database("W00t")
    #     database.register()
    #     sp = SimaProImporter(self.filepath("empty"), depends=[])
    #     with self.assertRaises(AssertionError):
    #         sp.importer()

    # def test_import_one_empty_process(self):
    #     sp = SimaProImporter(self.filepath("empty"), depends=[])
    #     sp.importer()
    #     self.assertTrue("W00t" in databases)
    #     self.assertEqual(len(Database("W00t").load()), 1)

    # def test_get_db_name(self):
    #     sp = SimaProImporter(self.filepath("empty"), depends=[])
    #     sp.importer()
    #     self.assertTrue("W00t" in databases)

    # def test_set_db_name(self):
    #     sp = SimaProImporter(self.filepath("empty"), depends=[], name="A different one")
    #     sp.importer()
    #     self.assertTrue("A different one" in databases)
    #     self.assertTrue("W00t" not in databases)

    # def test_default_geo(self):
    #     sp = SimaProImporter(self.filepath("empty"), depends=[], default_geo="Where?")
    #     sp.importer()
    #     data = Database("W00t").load().values()[0]
    #     self.assertEqual("Where?", data['location'])

    # def test_no_multioutput(self):
    #     sp = SimaProImporter(self.filepath("multioutput"), depends=[])
    #     with self.assertRaises(AssertionError):
    #         sp.importer()

    def test_detoxify_re(self):
        self.assertFalse(detoxify_re.search("Cheese U"))
        self.assertFalse(detoxify_re.search("Cheese/CH"))
        self.assertTrue(detoxify_re.search("Cheese/CH U"))
        self.assertTrue(detoxify_re.search("Cheese/CH/I U"))
        self.assertTrue(detoxify_re.search("Cheese/CH/I S"))
        self.assertTrue(detoxify_re.search("Cheese/RER U"))
        self.assertTrue(detoxify_re.search("Cheese/CENTREL U"))
        self.assertTrue(detoxify_re.search("Cheese/CENTREL S"))

    def test_detoxify_re2(self):
        test_strings = [
            u'Absorption chiller 100kW/CH/I U',
            u'Disposal, solvents mixture, 16.5% water, to hazardous waste incineration/CH U',
            u'Electricity, at power plant/hard coal, IGCC, no CCS/2025/RER U',
            u'Electricity, natural gas, at fuel cell SOFC 200kWe, alloc exergy, 2030/CH U',
            u'Heat exchanger/of cogen unit 160kWe/RER/I U',
            u'Lignite, burned in power plant/post, pipeline 200km, storage 1000m/2025/RER U',
            u'Transport, lorry >28t, fleet average/CH U',
            u'Water, cooling, unspecified natural origin, CH',
            u'Water, cooling, unspecified natural origin/m3',
            u'Water/m3',
        ]

        expected_results = [
            [(u'Absorption chiller 100kW', u'CH', u'/I')],
            [(u'Disposal, solvents mixture, 16.5% water, to hazardous waste incineration', u'CH', u'')],
            [(u'Electricity, at power plant/hard coal, IGCC, no CCS/2025', u'RER', u'')],
            [(u'Electricity, natural gas, at fuel cell SOFC 200kWe, alloc exergy, 2030', u'CH', u'')],
            [(u'Heat exchanger/of cogen unit 160kWe', u'RER', u'/I')],
            [(u'Lignite, burned in power plant/post, pipeline 200km, storage 1000m/2025', u'RER', u'')],
            [(u'Transport, lorry >28t, fleet average', u'CH', u'')],
            [], [], []
        ]
        for string, result in zip(test_strings, expected_results):
            self.assertEqual(detoxify_re.findall(string), result)

    # def test_simapro_unit_conversion(self):
    #     sp = SimaProImporter(self.filepath("empty"), depends=[])
    #     sp.importer()
    #     data = Database("W00t").load().values()[0]
    #     self.assertEqual("unit", data['unit'])

    # def test_dataset_definition(self):
    #     self.maxDiff = None
    #     sp = SimaProImporter(self.filepath("empty"), depends=[])
    #     sp.importer()
    #     data = Database("W00t").load().values()[0]
    #     self.assertEqual(data, _({
    #         "name": "Fish food",
    #         "unit": u"unit",
    #         'database': 'W00t',
    #         "location": "GLO",
    #         "type": "process",
    #         "categories": ["Agricultural", "Animal production", "Animal foods"],
    #         "code": u'6524377b64855cc3daf13bd1bcfe0385',
    #         "exchanges": [{
    #             'amount': 1.0,
    #             'loc': 1.0,
    #             'input': ('W00t', '6524377b64855cc3daf13bd1bcfe0385'),
    #             'output': ('W00t', '6524377b64855cc3daf13bd1bcfe0385'),
    #             'type': 'production',
    #             'uncertainty type': NoUncertainty.id,
    #             'allocation': {'factor': 100.0, 'type': 'not defined'},
    #             'unit': 'unit',
    #             'folder': 'Agricultural\Animal production\Animal foods',
    #             'comment': '',
    #         }],
    #         "simapro metadata": {
    #             "Category type": "material",
    #             "Process identifier": "InsertSomethingCleverHere",
    #             "Type": "Unit process",
    #             "Process name": "bikes rule, cars drool",
    #         }
    #     }))

    # def test_production_exchange(self):
    #     sp = SimaProImporter(self.filepath("empty"), depends=[])
    #     sp.importer()
    #     data = Database("W00t").load().values()[0]
    #     self.assertEqual(data['exchanges'], _([{
    #         'amount': 1.0,
    #         'loc': 1.0,
    #         'input': ('W00t', '6524377b64855cc3daf13bd1bcfe0385'),
    #         'output': ('W00t', '6524377b64855cc3daf13bd1bcfe0385'),
    #         'type': 'production',
    #         'uncertainty type': NoUncertainty.id,
    #         'allocation': {'factor': 100.0, 'type': 'not defined'},
    #         'unit': 'unit',
    #         'folder': 'Agricultural\Animal production\Animal foods',
    #         'comment': '',
    #     }]))

    # def test_simapro_metadata(self):
    #     sp = SimaProImporter(self.filepath("metadata"), depends=[])
    #     sp.importer()
    #     data = Database("W00t").load().values()[0]
    #     self.assertEqual(data['simapro metadata'], {
    #         "Simple": "yep!",
    #         "Multiline": ["This too", "works just fine"],
    #         "But stops": "in time"
    #     })

    # def test_linking(self):
    #     # Test number of datasets
    #     # Test internal links
    #     # Test external links with and without slashes, with and without geo
    #     database = Database("background")
    #     database.register(
    #         format="Test data",
    #     )
    #     database.write(background_data)
    #     sp = SimaProImporter(self.filepath("simple"), depends=["background"])
    #     sp.importer()

    # def test_missing(self):
    #     sp = SimaProImporter(self.filepath("missing"), depends=[])
    #     with self.assertRaises(MissingExchange):
    #         sp.importer()

    # def test_unicode_strings(self):
    #     sp = SimaProImporter(self.filepath("empty"), depends=[], default_geo=u"Where?")
    #     sp.importer()
    #     for obj in Database("W00t").load().values():
    #         for key, value in obj.iteritems():
    #             if isinstance(key, basestring):
    #                 self.assertTrue(isinstance(key, unicode))
    #             if isinstance(value, basestring):
    #                 self.assertTrue(isinstance(value, unicode))

    # def test_comments(self):
    #     self.maxDiff = None
    #     database = Database("background")
    #     database.register()
    #     database.write(background_data)
    #     sp = SimaProImporter(self.filepath("comments"), depends=["background"])
    #     sp.importer()
    #     data = Database("W00t").load().values()[0]
    #     self.assertEqual(data['exchanges'], _([{
    #         'amount': 2.5e-10,
    #         'comment': 'single line comment',
    #         'input': ('background', "1"),
    #         'output': ('W00t', '6524377b64855cc3daf13bd1bcfe0385'),
    #         'label': 'Materials/fuels',
    #         'loc': 2.5e-10,
    #         'location': 'CA',
    #         'name': 'lunch',
    #         'type': 'technosphere',
    #         'uncertainty': 'Lognormal',
    #         'uncertainty type': UndefinedUncertainty.id,
    #         'unit': u'kilogram'
    #     }, {
    #         'amount': 1.0,
    #         'comment': 'first line of the comment\nsecond line of the comment',
    #         'input': ('background', '2'),
    #         'output': ('W00t', '6524377b64855cc3daf13bd1bcfe0385'),
    #         'label': 'Materials/fuels',
    #         'loc': 1.0,
    #         'location': 'CH',
    #         'name': 'dinner',
    #         'type': 'technosphere',
    #         'uncertainty': 'Lognormal',
    #         'uncertainty type': UndefinedUncertainty.id,
    #         'unit': u'kilogram'
    #     },{
    #         'amount': 1.0,
    #         'loc': 1.0,
    #         'input': ('W00t', '6524377b64855cc3daf13bd1bcfe0385'),
    #         'output': ('W00t', '6524377b64855cc3daf13bd1bcfe0385'),
    #         'type': 'production',
    #         'uncertainty type': NoUncertainty.id,
    #         'allocation': {'factor': 100.0, 'type': 'not defined'},
    #         'unit': u'unit',
    #         'folder': 'Agricultural\Animal production\Animal foods',
    #         'comment': 'first line of comment\nsecond line of comment',
    #     }]))

# # Test multiple background DBs
