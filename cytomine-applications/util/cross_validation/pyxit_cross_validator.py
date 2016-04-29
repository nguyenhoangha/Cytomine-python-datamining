# -*- coding: utf-8 -*-
import optparse
import os

import numpy as np
import sys

from sklearn.model_selection import GridSearchCV

from util import str2bool, mk_window_size_tuples, accuracy_scoring
from mapper import BinaryMapper, TernaryMapper
from adapters import AnnotationCollectionAdapter, PyxitClassifierAdapter
from options import MultipleOption
from cytomine import Cytomine
from cytomine.models import Annotation
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.model_selection import LeavePLabelOut, cross_val_score

__author__ = "Mormont Romain <romain.mormont@gmail.com>"
__version__ = "0.1"


def mk_pyxit(params):
    forest = ExtraTreesClassifier(n_estimators=params.forest_n_estimators,
                                  max_features=params.forest_max_features[0],
                                  min_samples_split=params.forest_min_samples_split[0],
                                  n_jobs=params.pyxit_n_jobs,
                                  verbose=False)

    return PyxitClassifierAdapter(base_estimator=forest, n_subwindows=params.pyxit_n_subwindows,
                                  min_size=params.pyxit_min_size[0], max_size=params.pyxit_max_size[0],
                                  target_width=params.pyxit_target_width, target_height=params.pyxit_target_height,
                                  interpolation=params.pyxit_interpolation, transpose=params.pyxit_transpose,
                                  colorspace=params.pyxit_colorspace[0], fixed_size=params.pyxit_fixed_size,
                                  n_jobs=params.pyxit_n_jobs, verbose=params.cytomine_verbose)


def mk_dataset(params):
    cytomine = Cytomine(params.cytomine_host, params.cytomine_public_key, params.cytomine_private_key,
                        base_path=params.cytomine_base_path, working_path=params.cytomine_working_path,
                        verbose=params.cytomine_verbose)

    # fetch annotation and filter them
    annotations = cytomine.get_annotations(id_project=params.cytomine_id_project,
                                           reviewed_only=params.cytomine_reviewed,
                                           showMeta=True, id_user=params.cytomine_selected_users)
    excluded_set = set(params.cytomine_excluded_annotations)
    excluded_terms = set(params.cytomine_excluded_terms)
    filtered = [a for a in annotations.data()
                if len(a.term) > 0
                    and a.id not in excluded_set
                    and set(a.term).isdisjoint(excluded_terms)]
    annotations = AnnotationCollectionAdapter(filtered)
    # dump annotations
    annotations = cytomine.dump_annotations(annotations=annotations, dest_path=params.pyxit_dir_ls,
                                            get_image_url_func=Annotation.get_annotation_alpha_crop_url,
                                            desired_zoom=params.cytomine_zoom_level)

    # make file names
    for annot in annotations:
        if not hasattr(annot, 'filename'):
            annot.filename = os.path.join(params.pyxit_dir_ls, annot.term[0], "{}_{}.png".format(annot.image, annot.id))

    return zip(*[(annot.filename, annot.term[0], annot.image) for annot in annotations])


def score(pyxit, X, y, labels, P, scoring, n_jobs=1, verbose=True):
    X = np.array(X)
    y = np.array(y)
    verbose = 10 if verbose else 0
    return cross_val_score(pyxit, X, y, labels=labels, scoring=scoring, cv=LeavePLabelOut(P),n_jobs=n_jobs,
                           verbose=verbose)


def main(argv):
    p = optparse.OptionParser(description='Pyxit/Cytomine Classification Cross Validator',
                              prog='PyXit Classification Cross Validator (PYthon piXiT)',
                              option_class=MultipleOption)

    p.add_option('--cytomine_host', type="string", default='', dest="cytomine_host",
                 help="The Cytomine host (eg: beta.cytomine.be, localhost:8080)")
    p.add_option('--cytomine_public_key', type="string", default='', dest="cytomine_public_key",
                 help="Cytomine public key")
    p.add_option('--cytomine_private_key', type="string", default='', dest="cytomine_private_key",
                 help="Cytomine private key")
    p.add_option('--cytomine_base_path', type="string", default='/api/', dest="cytomine_base_path",
                 help="Cytomine base path")
    p.add_option('--cytomine_working_path', default="/tmp/", type="string", dest="cytomine_working_path",
                 help="The working directory where temporary files can be stored (eg: /tmp)")
    p.add_option('--cytomine_id_software', type="int", dest="cytomine_id_software",
                 help="The Cytomine software identifier")
    p.add_option('--cytomine_id_project', type="int", dest="cytomine_id_project",
                 help="The Cytomine project identifier")
    p.add_option('-z', '--cytomine_zoom_level', default=0, type='int', dest='cytomine_zoom_level',
                 help="Zoom level for image extraction (0 for no zoom)")
    p.add_option('--cytomine_reviewed', type='string', default="False", dest="cytomine_reviewed",
                 help="Get reviewed annotations only")
    p.add_option('--cytomine_excluded_terms', action="extend", type='int', dest='cytomine_excluded_terms',
                 help="The identifiers of some terms to exclude. Those terms shouldn't be used in one of the three class parameters.")
    p.add_option('--cytomine_excluded_annotations', action="extend", type='int', dest='cytomine_excluded_annotations',
                 help="The identifiers of some annotations to exclude.")
    p.add_option('--cytomine_selected_users', action="extend", type='int', dest='cytomine_selected_users',
                 help="The identifiers of the user of which the annotations should be extracted")
    p.add_option('--cytomine_binary', type='string', default="False", dest="cytomine_binary",
                 help="True for binary classification (or ternary if some term ids are passed with the --cytomine_other_terms parameter.")
    p.add_option('--cytomine_positive_terms', action="extend", type='int', dest="cytomine_positive_terms",
                 help="The identifiers of the terms representing the positive class.")
    p.add_option('--cytomine_negative_terms', action="extend", type='int', dest="cytomine_negative_terms",
                 help="The identifiers of the terms representing the negative class.")
    p.add_option('--cytomine_other_terms', action="extend", type='int', default=[], dest="cytomine_other_terms",
                 help="The identifiers of the terms to as a third class.")
    p.add_option('--cytomine_verbose', type="string", default="False", dest="cytomine_verbose",
                 help="True for enabling verbosity.")

    p.add_option('--pyxit_target_width', default=16, type='int', dest='pyxit_target_width',
                 help="Target width for the pyxit algorithm extracted windows.")
    p.add_option('--pyxit_target_height', default=16, type='int', dest='pyxit_target_height',
                 help="Target height for the pyxit algorithm extracted windows.")
    p.add_option('--pyxit_n_jobs', type='int', default=1, dest='pyxit_n_jobs',
                 help="Number of jobs for performing the cross validation.")
    p.add_option('--pyxit_colorspace', default=[], type='int', dest='pyxit_colorspace', action="extend",
                 help="Color space the windows are converted into (0 for RGB, 1 for TRGB, 2 for HSV, 3 for GRAY)")
    p.add_option('--pyxit_n_subwindows', default=10, type="int", dest="pyxit_n_subwindows",
                 help="Number of subwindows to extract per image.")
    p.add_option('--pyxit_max_size', default=[], type="float", dest="pyxit_max_size", action="extend",
                 help="Maximum size proportion of the windows to extract (relative to the full image size).")
    p.add_option('--pyxit_min_size', default=[], type="float", dest="pyxit_min_size", action="extend",
                 help="Minimum size proportion of the windows to extract (relative to the full image size).")
    p.add_option('--pyxit_transpose', type="string", default="False", dest="pyxit_transpose",
                 help="True for applying rotation to the windows, False otherwise.")
    p.add_option('--pyxit_interpolation', default=2, type="int", dest="pyxit_interpolation",
                 help="Interpolation to use (1 for nearest, 2 for bilinear, 3 for cubic and 4 for anti-alias).")
    p.add_option('--pyxit_fixed_size', type="string", default="False", dest="pyxit_fixed_size",
                 help="True for extracting windows having a fixed size, False for randomly picked size.")
    p.add_option('--pyxit_dir_ls', type="string", default="/tmp/ls", dest="pyxit_dir_ls",
                 help="The directory in which will be stored the images of the learning set.")

    p.add_option('--cv_images_out', type="int", default=1, dest="cv_images_out",
                 help="The number of images to leave out for the cross validation")

    p.add_option('--forest_n_estimators', default=10, type="int", dest="forest_n_estimators",
                 help="The number of tress in pyxit underlying forest.")
    p.add_option('--forest_min_samples_split', default=[], type="int", dest="forest_min_samples_split", action="extend",
                 help="The minimum number of objects in a node required so that it can be splitted.")

    p.add_option('--forest_max_features', default=[], type="int", dest="forest_max_features", action="extend",
                 help="The maximum number of attribute in which to look for a split when expending a node of the tree.")
    p.add_option('--svm', default=0, dest="svm", type="int",
                 help="True for using the Pyxit variant with SVM.")
    p.add_option('--svm_c', default=[], type="float", dest="svm_c", action="extend",
                 help="SVM C parameter.")

    params, arguments = p.parse_args(args=argv)
    params.cytomine_binary = str2bool(params.cytomine_binary)
    params.cytomine_verbose = str2bool(params.cytomine_verbose)
    params.pyxit_fixed_size = str2bool(params.pyxit_fixed_size)
    params.pyxit_transpose = str2bool(params.pyxit_transpose)
    params.cytomine_reviewed = str2bool(params.cytomine_reviewed)

    print "Parameters : {}".format(params)

    # Set default
    if len(params.pyxit_min_size) == 0:
        params.pyxit_min_size = [0.1]
    if len(params.pyxit_max_size) == 0:
        params.pyxit_max_size = [0.9]
    windows_sizes = mk_window_size_tuples(params.pyxit_min_size, params.pyxit_max_size)
    if len(params.forest_max_features) == 0:
        params.forest_max_features = [16]
    if len(params.forest_min_samples_split) == 0:
        params.forest_min_samples_split = [1]
    if len(params.svm_c) == 0:
        params.svm_c = [0.1]
    if len(params.pyxit_colorspace) == 0:
        params.pyxit_colorspace = [2]

    # create pyxit and generate dataset
    print "Create Pyxit..."
    pyxit = mk_pyxit(params)
    print "Create dataset..."
    X, y, labels = mk_dataset(params)

    print "Parameters to tune : "
    print "- Pyxit min size : {}".format(params.pyxit_min_size)
    print "- Pyxit max size : {}".format(params.pyxit_max_size)
    print "- Windows : {}".format(windows_sizes)
    print "- Forest max features : {}".format(params.forest_max_features)
    print "- Forest min sample split : {}".format(params.forest_min_samples_split)
    print "- SVM C : {}".format(params.svm_c)
    print "- Pyxit colorspace : {}".format(params.pyxit_colorspace)

    cv_params = {
        "window_sizes": windows_sizes,
        "max_features": params.forest_max_features,
        "min_samples_split": params.forest_min_samples_split,
        "colorspace": params.pyxit_colorspace,
        # "svm_c": params.svm_c, # disabled to avoid useless cases
    }

    X, y, labels = np.array(X), np.array(y), np.array(labels)
    grid = GridSearchCV(pyxit, cv_params, scoring=accuracy_scoring,
                        cv=LeavePLabelOut(params.cv_images_out).get_n_splits(X, y, labels),
                        verbose=10, n_jobs=1)

    # transform into a binary/ternary problem if necessary
    if params.cytomine_binary:
        if len(params.cytomine_other_terms) > 0:
            mapper = TernaryMapper(params.cytomine_positive_terms, params.cytomine_negative_terms,
                                   params.cytomine_other_terms)
        else:
            mapper = BinaryMapper(params.cytomine_positive_terms, params.cytomine_negative_terms)
        y = [mapper.map(to_map) for to_map in y]

    grid.fit(X, y)

    print "Best parameters : {}".format(grid.best_params_)
    print "Best score      : {}".format(grid.best_score_)

if __name__ == "__main__":
    main(sys.argv)
