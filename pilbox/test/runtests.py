#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, with_statement
import logging
import textwrap
import sys
from tornado.test.util import unittest

TEST_MODULES = [
    'pilbox.test.signature_test',
]


def all():
    return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)


class PilboxTextTestRunner(unittest.TextTestRunner):
    def run(self, test):
        result = super(PilboxTextTestRunner, self).run(test)
        if result.skipped:
            skip_reasons = set(reason for (test, reason) in result.skipped)
            self.stream.write(textwrap.fill(
                "Some tests were skipped because: %s" %
                ", ".join(sorted(skip_reasons))))
            self.stream.write("\n")
        return result

if __name__ == '__main__':
    import warnings
    # Be strict about most warnings.  This also turns on warnings that are
    # ignored by default, including DeprecationWarnings and
    # python 3.2's ResourceWarnings.
    warnings.filterwarnings("error")
    warnings.filterwarnings("ignore", category=ImportWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("error", category=DeprecationWarning,
                            module=r"tornado\..*")
    # The unittest module is aggressive about deprecating redundant methods,
    # leaving some without non-deprecated spellings that work on both
    # 2.7 and 3.2
    warnings.filterwarnings("ignore", category=DeprecationWarning,
                            message="Please use assert.* instead")

    logging.getLogger("tornado.access").setLevel(logging.CRITICAL)

    import tornado.testing
    kwargs = {}
    if sys.version_info >= (3, 2):
        # HACK:  unittest.main will make its own changes to the warning
        # configuration, which may conflict with the settings above
        # or command-line flags like -bb.  Passing warnings=False
        # suppresses this behavior, although this looks like an implementation
        # detail.  http://bugs.python.org/issue15626
        kwargs['warnings'] = False
    kwargs['testRunner'] = PilboxTextTestRunner
    tornado.testing.main(**kwargs)
