# -*- coding: utf-8 -*-
import pickle

__author__ = "Mormont Romain <romain.mormont@gmail.com>"
__version__ = "0.1"

import os
import numpy as np
from PIL.Image import fromarray
from sldc import PolygonClassifier


class PyxitClassifierAdapter(PolygonClassifier):

    def __init__(self, pyxit_classifier, tile_builder, classes, working_path):
        """Constructor for PyxitClassifierAdapter objects

        Parameters
        ----------
        pyxit_classifier: PyxitClassifier
            The pyxit classifier objects
        tile_builder: TileBuilder
            A tile builder
        classes: array
            An array containing the classes labels
        working_path: string
            A path in which the instance can save temporary images to pass to the pyxit classifier
        """
        self._pyxit_classifier = pyxit_classifier
        self._tile_builder = tile_builder
        self._classes = classes
        self._working_path = working_path

    def predict(self, image, polygon):
        # Pyxit classifier takes images from the filesystem
        # So store the crop into a file before passing the path to the classifier
        minx, miny, maxx, maxy = polygon.bounds
        offset = (minx, miny)
        width = int(maxx - minx) + 1
        height = int(maxy - miny) + 1
        tile = image.tile(self._tile_builder, offset, width, height)
        np_image = tile.get_numpy_repr()

        tile_path = self._tile_path(image, offset, width, height)
        fromarray(np_image).save(tile_path)

        # actually predict
        X = np.array([tile_path])
        probas = self._pyxit_classifier.predict_proba(X)
        best_index = np.argmax(probas, axis=1)
        results = self._classes.take(best_index, axis=0)
        return results[0]

    def _tile_path(self, image, offset, width, height):
        """Return the path where to store the tile

        Parameters
        ----------
        image: Image
            The image object from which the tile was extracted
        offset: tuple (int, int)
            The coordinates of the upper left pixel of the tile
        width: int
            The tile width
        height: int
            The tile height

        Returns
        -------
        path: string
            The path in which to store the image
        """
        filename = "{}_{}_{}_{}_{}.png".format(image.image_instance.id, offset[0], offset[1], width, height)
        return os.path.join(self._working_path, filename)

    @staticmethod
    def build_from_pickle(model_path, tile_builder, working_path):
        """Builds a PyxitClassifierAdapter object from a pickled model

        Parameters
        ----------
        model_path: string
            The path to which is stored the pickled model
        tile_builder: TileBuilder
            A tile builder object
        working_path: string
            The path in which temporary files can be written

        Returns
        -------
        adapter: PyxitClassifierAdapter
            The built classifier adapter

        Notes
        -----
        The first object pickled in the file in the path 'model_path' is an array
        containing the classes, and the second is the PyxitClassifier object
        """
        with open(model_path, "rb") as model_file:
            classes = pickle.load(model_file)
            classifier = pickle.load(model_file)
        return PyxitClassifierAdapter(classifier, tile_builder, classes, working_path)
