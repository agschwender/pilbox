#!/usr/bin/env python
#
# Copyright 2013 Adam Gschwender
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import textwrap

from . import image_test
from ..image import Image


def main():
    """Generates expected results using the current application libraries. This
    is a convenience program that is intended to regenerate the tests after an
    algorithm or mode change that would alter the expected output."""

    warning = "WARNING: All expected tests will be regenerated, output must" \
        " be verified to ensure future tests are producing accurate results."
    print "\n".join(textwrap.wrap(warning)) + "\n"
    proceed = raw_input("Are you sure you want to proceed? [y/N] ")
    if proceed not in ["y", "Y"]:
        print "Not proceeding, done"
        sys.exit()

    cases = image_test.get_image_resize_cases()
    for case in cases:
        with open(case["source_path"], "rb") as f:

            print "Generating %s" % case["expected_path"]
            img = Image(f).resize(
                case["width"], case["height"], mode=case["mode"],
                background=case.get("background"), filter=case.get("filter"),
                position=case.get("position"))
            rv = img.save(
                format=case.get("format"), quality=case.get("quality"))

            with open(case["expected_path"], "wb") as expected:
                expected.write(rv.read())

    cases = image_test.get_image_rotate_cases()
    for case in cases:
        with open(case["source_path"], "rb") as f:

            print "Generating %s" % case["expected_path"]
            img = Image(f).rotate(
                case["degree"], expand=case.get("expand"),
                filter=case.get("filter"))
            rv = img.save(
                format=case.get("format"), quality=case.get("quality"))

            with open(case["expected_path"], "wb") as expected:
                expected.write(rv.read())


    cases = image_test.get_image_region_cases()
    for case in cases:
        with open(case["source_path"], "rb") as f:

            print "Generating %s" % case["expected_path"]
            img = Image(f).region(case["rect"].split(","))
            rv = img.save(
                format=case.get("format"), quality=case.get("quality"))

            with open(case["expected_path"], "wb") as expected:
                expected.write(rv.read())


    cases = image_test.get_image_chained_cases()
    for case in cases:
        with open(case["source_path"], "rb") as f:

            print "Generating %s" % case["expected_path"]
            img = Image(f)
            for operation in case["operation"]:
                if operation == "resize":
                    img.resize(case["width"], case["height"])
                elif operation == "rotate":
                    img.rotate(case["degree"])
                elif operation == "region":
                    img.region(case["rect"].split(","))

            rv = img.save()
            with open(case["expected_path"], "wb") as expected:
                expected.write(rv.read())


if __name__ == "__main__":
    main()
