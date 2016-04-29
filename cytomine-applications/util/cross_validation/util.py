# -*- coding: utf-8 -*-
import os

import shutil

from cytomine.models import Annotation
from sklearn.metrics import precision_score, accuracy_score, recall_score


__author__ = "Mormont Romain <romain.mormont@gmail.com>"
__version__ = "0.1"


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def str2list(l, conv=int):
    return [conv(v) for v in l.split(",")]


def create_dir(path, clean=False):
    if not os.path.exists(path):
        print "Creating annotation directory: %s" % path
        os.makedirs(path)
    elif clean:
        print "Cleaning annotation directory: %s" % path
        shutil.rmtree(path)
        os.makedirs(path)


def copy_content(src, dst):
    files = [f for f in os.listdir(src) if not os.path.isdir(os.path.join(src, f))]
    for f in files:
        shutil.copy(os.path.join(src, f), dst)


class CropTypeEnum(object):
    CROP = 1
    ALPHA_CROP = 2

    @staticmethod
    def enum2crop(enum):
        if enum == CropTypeEnum.CROP:
            return Annotation.get_annotation_crop_url
        elif enum == CropTypeEnum.ALPHA_CROP:
            return Annotation.get_annotation_alpha_crop_url
        else:
            raise ValueError("Invalid enum field : {}".format(enum))


def accuracy_scoring(pyxit, X, y):
    return accuracy_score(y, pyxit.predict(X))


def recall_scoring(pyxit, X, y):
    return recall_score(y, pyxit.predict(X))


def precision_scoring(pyxit, X, y):
    return precision_score(y, pyxit.predict(X))


def get_greater(value, lst):
    return [v for v in lst if value < v]


def mk_window_size_tuples(min_sizes, max_sizes):
    min_sizes = sorted(min_sizes)
    max_sizes = sorted(max_sizes)
    tuples = list()
    for min_size in min_sizes:
        valid_sizes = get_greater(min_size, max_sizes)
        if len(valid_sizes) > 0:
            tuples += [(min_size, max_size) for max_size in valid_sizes]
    return tuples
