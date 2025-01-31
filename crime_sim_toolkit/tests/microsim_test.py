import os
import json
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import folium
import crime_sim_toolkit.microsim as Microsim
import pkg_resources

# specified for directory passing test
test_dir = os.path.dirname(os.path.abspath(__file__))

# Could be any dot-separated package/module name or a "Requirement"
resource_package = 'crime_sim_toolkit'

class Test(unittest.TestCase):

    def setUp(self):

        self.test_sim = Microsim.Microsimulator()

        self.loaded_sim = Microsim.Microsimulator()

        self.running_sim = Microsim.Microsimulator()

        self.loaded_sim.load_data(seed_year = 2017,
                                  police_data_dir = pkg_resources.resource_filename(resource_package,'tests/testing_data/test_microsim/sample_vic_data_WY2017.csv'),
                                  seed_pop_dir = pkg_resources.resource_filename(resource_package,'tests/testing_data/test_microsim/sample_seed_pop.csv'),
                                  spenser_demographic_cols = ['DC1117EW_C_SEX','DC1117EW_C_AGE','DC2101EW_C_ETHPUK11'],
                                  police_demographic_cols = ['sex','age','ethnicity']
                                  )

        self.running_sim.load_data(seed_year = 2017,
                                  police_data_dir = pkg_resources.resource_filename(resource_package, 'tests/testing_data/test_microsim/sample_vic_data_WY2017.csv'),
                                  seed_pop_dir = pkg_resources.resource_filename(resource_package, 'tests/testing_data/test_microsim/sample_seed_pop.csv'),
                                  spenser_demographic_cols = ['DC1117EW_C_SEX','DC1117EW_C_AGE','DC2101EW_C_ETHPUK11'],
                                  police_demographic_cols = ['sex','age','ethnicity']
                                  )

        self.running_sim.load_future_pop(synthetic_population_dir=pkg_resources.resource_filename(resource_package, 'tests/testing_data/test_microsim/test_future_pop'),
                                         year=2019,
                                         demographic_cols=['DC1117EW_C_SEX','DC1117EW_C_AGE','DC2101EW_C_ETHPUK11'])

        self.running_sim.generate_probability_table()

    def test_load_crime_data(self):
        """
        Test VictimData class
        """

        self.test_sim.load_crime_data(year = 2017.0,
                                      directory = pkg_resources.resource_filename(resource_package, 'tests/testing_data/test_microsim/sample_vic_data_WY2017.csv'),
                                      demographic_cols=['sex','age','ethnicity'])

        self.assertTrue(isinstance(self.test_sim.crime_data, pd.DataFrame))

        # test that on passing bad path system exits
        with self.assertRaises(SystemExit) as cm:

            self.test_sim.load_crime_data(year = 2017.0,
                                          directory = pkg_resources.resource_filename(resource_package, 'tests/testing_data/test_microsim/sample_vic_data_WY2018.csv'),
                                         demographic_cols=['sex','age','ethnicity'])

        self.assertEqual(cm.exception.code, 0)

    def test_combined_profiles(self):
        """
        Test create_combined_profiles function
        """

        self.loaded_sim.crime_data = self.loaded_sim.create_combined_profiles(dataframe = self.loaded_sim.crime_data,
                                               demographic_cols = ['sex','age','ethnicity'])

        self.assertTrue('demographic_profile' in self.loaded_sim.crime_data.columns.tolist())

        self.assertTrue(self.loaded_sim.crime_data.demographic_profile[4] == '2-42-2')

        # test error raise if invalid column names passed
        with self.assertRaises(KeyError) as context:

            self.test_sim.create_combined_profiles(dataframe = self.loaded_sim.crime_data,
                                                   demographic_cols = ['name','age','ethnicity'])


    def test_load_seed_pop(self):
        """
        Test for loading the seed population dataset
        and ensuring demographic columns are combined
        """

        self.test_sim.load_seed_pop(pkg_resources.resource_filename(resource_package, 'tests/testing_data/test_microsim/sample_seed_pop.csv'),
                                    demographic_cols=['DC1117EW_C_SEX','DC1117EW_C_AGE','DC2101EW_C_ETHPUK11'])

        self.assertTrue(isinstance(self.test_sim.seed_population, pd.DataFrame))

    def test_load_future_pop(self):
        """
        Test function for loading future_population
        """
        self.test_sim.load_future_pop(synthetic_population_dir=pkg_resources.resource_filename(resource_package, 'tests/testing_data/test_microsim/test_future_pop'),
                                      year=2019,
                                      demographic_cols=['DC1117EW_C_SEX','DC1117EW_C_AGE','DC2101EW_C_ETHPUK11'])

        self.assertTrue(isinstance(self.test_sim.future_population, pd.DataFrame))

        self.assertEqual(self.test_sim.future_population.shape[0], 2302 * 3)

        self.assertTrue('demographic_profile' in self.test_sim.future_population.columns.tolist())

        with self.assertRaises(ValueError) as context:

            self.test_sim.load_future_pop(synthetic_population_dir=pkg_resources.resource_filename(resource_package, 'tests/testing_data/test_microsim'),
                                          year=2019,
                                          demographic_cols=['DC1117EW_C_SEX','DC1117EW_C_AGE','DC2101EW_C_ETHPUK11'])

    def test_get_prob_table(self):
        """
        Test for getting probability table
        """

        self.loaded_sim.generate_probability_table()

        self.assertEqual(self.loaded_sim.crime_data.shape[0], self.loaded_sim.transition_table.crime_counts.sum())

        self.assertTrue(isinstance(self.loaded_sim.transition_table, pd.DataFrame))

        self.assertAlmostEqual(self.loaded_sim.transition_table.chance_crime_per_day_demo[10], 0.000512, places=4)

    def test_run_simulation(self):
        """
        A test for the run_simulator function
        """

        sim_run01 = self.running_sim.run_simulation(future_population = self.running_sim.future_population)

        self.assertTrue(isinstance(sim_run01, pd.DataFrame))

        self.assertTrue(sim_run01.shape[1], 4)

        # test the proportions of overall crime generated versus
        # seed data

        seed_crime_prop = self.running_sim.crime_data.shape[0] / self.running_sim.seed_population.shape[0]

        sim_crime_prop = sim_run01.shape[0] / self.running_sim.future_population.shape[0]

        # test if absolute crime proportions are within 5% tolerance
        np.testing.assert_allclose(sim_crime_prop, seed_crime_prop, rtol=0.01, atol=0.05)

        # testing crime specific proportions are similar

        seed_crimes = (self.running_sim.crime_data.Crime_description.value_counts() \
                        / self.running_sim.crime_data.shape[0])[:3].sort_index()

        sim_crimes = ((sim_run01.crime.value_counts() \
                       / sim_run01.shape[0])[:3]).sort_index()

        np.testing.assert_allclose(seed_crimes.to_numpy(), sim_crimes.to_numpy(), atol=1.5, rtol=1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
